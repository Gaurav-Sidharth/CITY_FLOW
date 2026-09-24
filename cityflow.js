'use strict';
console.log('%cCityFlow client build: v15 (Final Stack)', 'color:#00E5FF;font-weight:bold');
const TICK_MS = 2000;

const state = {
    fromStop: null, toStop: null, activeRoutes: [], busMarkers: {}, routeLines: {},
    fromMarker: null, toMarker: null, stopMarkersMap: {}, isSearching: false, connected: false,
    selectedBusId: null, selectedRouteId: null
};

let map;
function initMap() {
    map = L.map('map', { center: [30.3200, 78.0400], zoom: 13, zoomControl: true, attributionControl: false });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19 }).addTo(map);
}

function startClock() {
    const el = document.getElementById('clock');
    setInterval(() => { el.textContent = new Date().toLocaleTimeString('en-IN', { hour12: false }); }, 1000);
}

let socket;
function initSocket() {
    socket = io({ transports: ['websocket', 'polling'] });
    setConnectionState('connecting');
    socket.on('connect', () => { state.connected = true; setConnectionState('online'); });
    socket.on('disconnect', () => { state.connected = false; setConnectionState('offline'); });
    socket.on('reconnect_attempt', () => setConnectionState('connecting'));
    socket.on('bus_positions', handleBusPositions);
}

function setConnectionState(mode) {
    const ring = document.querySelector('.pulse-ring'), txt = document.getElementById('status-text');
    ring.classList.remove('offline', 'connecting');
    if (mode === 'online') { if (!state.isSearching) txt.textContent = 'LIVE'; }
    else if (mode === 'connecting') { ring.classList.add('connecting'); txt.textContent = 'CONNECTING'; }
    else { ring.classList.add('offline'); txt.textContent = 'OFFLINE'; }
}

function computeEta(route, progress, direction, speedStr, targetStopId) {
    if (!targetStopId || !route.stop_cum) return null;
    if (direction === -1) return 'Opposite Dir.';
    const idx = route.stops.map(s => s.id).indexOf(targetStopId);
    if (idx === -1) return null;
    
    const targetDist = route.stop_cum[idx];
    const currentDist = progress * route.total_dist;
    const remaining = targetDist - currentDist;
    
    if (Math.abs(remaining) < 10) return 'At Stop';
    if (remaining < 0) return 'Passed';
    
    const speedKmh = parseInt(speedStr, 10) || 30;
    const mins = Math.round((remaining / 1000) / (speedKmh / 60));
    return `${Math.max(1, mins)} min`;
}

function getArrivalSortScore(bus) {
    if (bus.eta_from) {
        if (bus.eta_from === 'At Stop') return 0;
        const m = bus.eta_from.match(/(\d+)\s*min/);
        if (m) return parseInt(m[1], 10);
        if (bus.eta_from === 'Passed') return 5000;
        if (bus.eta_from === 'Opposite Dir.') return 9000;
    }
    if (bus.eta_to) {
        if (bus.eta_to === 'At Stop') return 0;
        const m = bus.eta_to.match(/(\d+)\s*min/);
        if (m) return parseInt(m[1], 10);
    }
    if (bus.distance) {
        if (bus.distance === 'At Stop') return 0;
        const dm = bus.distance.match(/(\d+)\s*m/);
        if (dm) return parseInt(dm[1], 10) / 100;
    }
    return 9999;
}

function handleBusPositions(payload) {
    const liveBuses = payload.buses || {};
    if (!state.activeRoutes.length) return;
    let touched = false;
    state.activeRoutes.forEach(route => {
        route.buses.forEach(bus => {
            const live = liveBuses[bus.id];
            if (!live) return;
            touched = true;
            bus.lat = live.lat; bus.lng = live.lng; bus.status = live.status;
            bus.occupancy = live.occupancy; bus.progress = live.progress;
            bus.direction = live.direction;
            bus.last_stop = live.last_stop; bus.next_stop = live.next_stop;
            bus.speed = live.speed; bus.distance = live.distance;
            
            const searchFrom = route.search_from_id || (state.fromStop ? state.fromStop.id : null);
            const searchTo = route.search_to_id || (state.toStop ? state.toStop.id : null);
            
            bus.eta_from = searchFrom ? computeEta(route, live.progress, live.direction, live.speed, searchFrom) : null;
            bus.eta_to = searchTo ? computeEta(route, live.progress, live.direction, live.speed, searchTo) : null;
        });
    });
    if (touched) {
        state.activeRoutes.forEach(route => route.buses.forEach(bus => addOrUpdateBusMarker(bus, route, true)));
        updateBusList(state.activeRoutes);
        flashRefreshBadge();
    }
}

let badgeTimeout;
function flashRefreshBadge() {
    const badge = document.getElementById('refresh-badge');
    badge.classList.remove('hidden');
    clearTimeout(badgeTimeout);
    badgeTimeout = setTimeout(() => badge.classList.add('hidden'), 1200);
}

let debounceTimer = {};
let currentSearchController = null;

function setupAutocomplete(inputId, dropdownId, selectedId, onSelect) {
    const input = document.getElementById(inputId), dropdown = document.getElementById(dropdownId), selected = document.getElementById(selectedId);
    
    input.addEventListener('input', () => {
        if (inputId === 'from-input') { state.fromStop = null; document.getElementById('from-selected').classList.add('hidden'); }
        if (inputId === 'to-input') { state.toStop = null; document.getElementById('to-selected').classList.add('hidden'); }

        const q = input.value.trim();
        clearTimeout(debounceTimer[inputId]);
        if (q.length < 2) { dropdown.classList.add('hidden'); return; }
        debounceTimer[inputId] = setTimeout(async () => {
            const stops = await fetchStops(q);
            renderDropdown(dropdown, stops, (stop) => {
                input.value = stop.name; dropdown.classList.add('hidden');
                selected.textContent = `📍 ${stop.name}`; selected.classList.remove('hidden');
                onSelect(stop);
            });
        }, 250);
    });
    
    input.addEventListener('keydown', (e) => { if (e.key === 'Escape') dropdown.classList.add('hidden'); });
    document.addEventListener('click', (e) => { if (!input.contains(e.target) && !dropdown.contains(e.target)) dropdown.classList.add('hidden'); });
}

async function fetchStops(q) { 
    if (currentSearchController) currentSearchController.abort();
    currentSearchController = new AbortController();
    
    try { 
        const res = await fetch(`/api/stops/search?q=${encodeURIComponent(q)}`, { 
            signal: currentSearchController.signal 
        }); 
        return await res.json(); 
    } catch (e) { 
        return []; 
    } 
}

function renderDropdown(dropdown, stops, onSelect) {
    if (!stops.length) { dropdown.innerHTML = `<div class="dropdown-item" style="color:var(--muted)">No matches found</div>`; } 
    else {
        dropdown.innerHTML = stops.map(s => `
            <div class="dropdown-item" data-id="${s.id}">
                <span class="dropdown-item-icon">${s.source === 'stop' ? '🚏' : '📍'}</span>
                <div><div>${s.name}</div>${s.source !== 'stop' && s.full_name ? `<div class="dropdown-item-sub">${s.full_name}</div>` : ''}</div>
            </div>`).join('');
        dropdown.querySelectorAll('.dropdown-item[data-id]').forEach((el, i) => { el.addEventListener('click', () => onSelect(stops[i])); });
    }
    dropdown.classList.remove('hidden');
}

document.getElementById('swap-btn').addEventListener('click', () => {
    const fi = document.getElementById('from-input'), ti = document.getElementById('to-input');
    const fs = document.getElementById('from-selected'), ts = document.getElementById('to-selected');
    [fi.value, ti.value] = [ti.value, fi.value];
    [fs.textContent, ts.textContent] = [ts.textContent, fs.textContent];
    [state.fromStop, state.toStop] = [state.toStop, state.fromStop];
    fs.classList.toggle('hidden', !state.fromStop); ts.classList.toggle('hidden', !state.toStop);
});

document.getElementById('search-btn').addEventListener('click', async () => {
    const fromQuery = state.fromStop ? state.fromStop.id : document.getElementById('from-input').value.trim();
    const toQuery = state.toStop ? state.toStop.id : document.getElementById('to-input').value.trim();
    if (!fromQuery || !toQuery) { showResults(`<div class="no-route-msg">Please enter both FROM and TO stops.</div>`); return; }
    if (fromQuery.toLowerCase() === toQuery.toLowerCase()) { showResults(`<div class="no-route-msg">Start and destination cannot be the same!</div>`); return; }
    
    setSearching(true); 
    clearMap(); 
    state.selectedBusId = null;
    state.selectedRouteId = null;
    
    try {
        const res = await fetch(`/api/find-buses?from=${encodeURIComponent(fromQuery)}&to=${encodeURIComponent(toQuery)}`);
        const data = await res.json();
        if (data.error) { showResults(`<div class="no-route-msg">⚠ ${data.error}</div>`); state.activeRoutes = []; return; }
        if (!data.routes || !data.routes.length) { showResults(`<div class="no-route-msg">🚫 No routes found connecting these stops.<br>Try nearby stops.</div>`); state.activeRoutes = []; return; }
        
        state.fromStop = data.routes[0].from_stop; 
        state.toStop = data.routes[data.routes.length - 1].to_stop;
        
        document.getElementById('from-selected').textContent = `📍 ${state.fromStop.name}`; document.getElementById('from-selected').classList.remove('hidden');
        document.getElementById('to-selected').textContent = `📍 ${state.toStop.name}`; document.getElementById('to-selected').classList.remove('hidden');
        
        state.activeRoutes = data.routes;
        renderResults(data.routes, data.notes || []);
        renderMapRoutes(data.routes);
    } finally { setSearching(false); }
});

function setSearching(val) {
    state.isSearching = val;
    document.getElementById('search-btn').disabled = val;
    document.getElementById('search-btn-text').textContent = val ? 'SEARCHING...' : 'SEARCH TRANSPORT';
    document.getElementById('search-spinner').classList.toggle('hidden', !val);
    document.getElementById('status-text').textContent = val ? 'SEARCHING' : (state.connected ? 'LIVE' : 'OFFLINE');
}

function renderResults(routes, notes) {
    let html = notes && notes.length ? `<div class="snap-note">${notes.map(n => `⚡ ${n}`).join('<br/>')}</div>` : '';
    html += `<div class="result-header"><span>${routes.length} ROUTE${routes.length > 1 ? 'S' : ''} FOUND</span><span>${routes.reduce((s, r) => s + r.buses.length, 0)} BUSES LIVE</span></div>`;
    
    html += routes.map(r => {
        r.buses.sort((a, b) => getArrivalSortScore(a) - getArrivalSortScore(b));
        return `
        <div class="route-result-card" data-route="${r.id}">
            <div class="route-card-header">
                <div class="route-color-line" style="background:${r.color};box-shadow:0 0 8px ${r.color}66"></div>
                <div><div class="route-card-name">${r.name}</div><div class="route-card-id">${r.id} · ${r.buses.length} buses</div></div>
            </div>
            <div class="route-all-stops">${r.stops.map(s => s.name).join(' · ')}</div>
            <div class="bus-list-container" id="bus-list-${r.id}">
                ${r.buses.map(b => buildBusRowHtml(b, r)).join('')}
            </div>
        </div>`
    }).join('');
        
    showResults(html); 
    attachBusRowHandlers(routes);
}

function updateBusList(routes) {
    routes.forEach(route => {
        route.buses.sort((a, b) => getArrivalSortScore(a) - getArrivalSortScore(b));
        const container = document.getElementById(`bus-list-${route.id}`);
        if (container) {
            container.innerHTML = route.buses.map(b => buildBusRowHtml(b, route)).join('');
            container.querySelectorAll('.bus-row').forEach(row => {
                row.addEventListener('click', () => {
                    selectSingleBus(row.dataset.bus, route.id);
                });
            });
        }
    });
}

function buildBusRowHtml(b, route) {
    let etaText = '—';
    if (b.eta_from === 'At Stop') etaText = '⚡ Arrived at your stop';
    else if (b.eta_from === 'Opposite Dir.') etaText = 'Moving opposite direction';
    else if (b.eta_from && b.eta_from !== 'Passed') etaText = `Arrives in ${b.eta_from}`;
    else if (b.eta_to) etaText = (route && route.is_transfer_leg && b.eta_to !== 'Passed') ? `Transfer in ${b.eta_to}` : `Destination in ${b.eta_to}`;
    
    const isSelected = state.selectedBusId === b.id;
    const selectedStyle = isSelected ? 'border: 2px solid #00E5FF; background: rgba(0, 229, 255, 0.15); box-shadow: 0 0 12px rgba(0, 229, 255, 0.35);' : '';

    return `
    <div class="bus-row" data-bus="${b.id}" style="cursor:pointer; transition: all 0.2s ease; ${selectedStyle}">
        <div class="bus-row-icon">🚌</div>
        <div class="bus-row-info">
            <div class="bus-row-id">${b.id} <span style="font-size:10px; color:#94a3b8; font-weight:normal;">(${b.speed || ''})</span></div>
            <div class="bus-row-stops">${b.last_stop && b.next_stop ? `${b.last_stop} →${b.next_stop}` : ''}</div>
            <div class="bus-row-eta" style="color:#00E5FF; font-weight:600;">${etaText}</div>
        </div>
        <div class="bus-row-right">
            <span class="status-pill ${b.status === 'Delayed' ? 'pill-delayed' : b.status === 'Early' ? 'pill-early' : 'pill-ontime'}">${b.status}</span>
            <div class="occ-bar"><div class="occ-fill" style="width:${b.occupancy}%;background:${b.occupancy > 80 ? 'var(--red)' : b.occupancy > 55 ? 'var(--yellow)' : 'var(--green)'}"></div></div>
        </div>
    </div>`;
}

function attachBusRowHandlers(routes) {
    document.querySelectorAll('.bus-row[data-bus]').forEach(row => {
        row.addEventListener('click', () => {
            const busId = row.dataset.bus;
            const targetRoute = routes.find(r => r.buses.some(b => b.id === busId));
            if (targetRoute) selectSingleBus(busId, targetRoute.id);
        });
    });
}

function selectSingleBus(busId, routeId) {
    state.selectedBusId = busId;
    state.selectedRouteId = routeId;

    Object.keys(state.routeLines).forEach(id => {
        const line = state.routeLines[id];
        if (id === routeId) {
            if (!map.hasLayer(line)) line.addTo(map);
            line.setStyle({ weight: 5, opacity: 1 });
        } else {
            if (map.hasLayer(line)) line.remove();
        }
    });

    Object.values(state.stopMarkersMap).forEach(item => {
        if (item.routes.has(routeId)) {
            if (!map.hasLayer(item.marker)) item.marker.addTo(map);
        } else {
            if (map.hasLayer(item.marker)) item.marker.remove();
        }
    });
    
    state.activeRoutes.forEach(r => {
        r.buses.forEach(b => {
            const m = state.busMarkers[b.id];
            if (!m) return;
            if (b.id === busId) {
                if (!map.hasLayer(m)) m.addTo(map);
            } else {
                if (map.hasLayer(m)) m.remove();
            }
        });
    });

    updateBusList(state.activeRoutes); 

    const targetMarker = state.busMarkers[busId];
    if (targetMarker) {
        map.flyTo(targetMarker.getLatLng(), 15, { duration: 0.8 });
        setTimeout(() => targetMarker.openPopup(), 900);
    }

    let resetBtn = document.getElementById('reset-view-btn');
    if (!resetBtn) {
        resetBtn = document.createElement('button');
        resetBtn.id = 'reset-view-btn'; 
        resetBtn.className = 'search-btn';
        resetBtn.style.marginTop = '15px'; 
        resetBtn.style.marginBottom = '15px'; 
        resetBtn.style.background = '#FF3D5A'; 
        resetBtn.style.color = '#fff'; 
        resetBtn.textContent = 'SHOW ALL BUSES & ROUTES';
        resetBtn.onclick = resetAllViews;
        document.getElementById('results-area').prepend(resetBtn);
    }
}

function resetAllViews() {
    state.selectedBusId = null;
    state.selectedRouteId = null;

    Object.values(state.routeLines).forEach(line => {
        if (!map.hasLayer(line)) line.addTo(map);
        line.setStyle({ weight: 4, opacity: 0.75 });
    });

    Object.values(state.stopMarkersMap).forEach(item => {
        if (!map.hasLayer(item.marker)) item.marker.addTo(map);
    });

    state.activeRoutes.forEach(r => {
        r.buses.forEach(b => {
            const m = state.busMarkers[b.id];
            if (m && !map.hasLayer(m)) m.addTo(map);
        });
    });

    updateBusList(state.activeRoutes); 

    const resetBtn = document.getElementById('reset-view-btn');
    if (resetBtn) resetBtn.remove();

    const bounds = [];
    if (state.fromMarker) bounds.push(state.fromMarker.getLatLng());
    if (state.toMarker) bounds.push(state.toMarker.getLatLng());
    Object.values(state.busMarkers).forEach(m => bounds.push(m.getLatLng()));
    if (bounds.length) map.fitBounds(L.latLngBounds(bounds).pad(0.2));
}

function showResults(html) { document.getElementById('results-area').innerHTML = html; }

function renderMapRoutes(routes) {
    routes.forEach(route => {
        const latlngs = route.road_points && route.road_points.length > 1 ? route.road_points : route.stops.map(s => [s.lat, s.lng]);
        state.routeLines[route.id] = L.polyline(latlngs, { color: route.color, weight: 4, opacity: 0.75, dashArray: route.road_matched ? null : '8, 5' }).addTo(map);
        
        if (route.from_stop && !state.fromMarker) {
            state.fromMarker = L.marker([route.from_stop.lat, route.from_stop.lng], { icon: stopIcon(route.from_stop.name, '#00E5FF', 'A'), zIndexOffset: 1000 }).addTo(map);
        }
        if (route.to_stop && !state.toMarker) {
            state.toMarker = L.marker([route.to_stop.lat, route.to_stop.lng], { icon: stopIcon(route.to_stop.name, '#FF6B35', 'B'), zIndexOffset: 1000 }).addTo(map);
        }
        
        route.stops.forEach(stop => {
            if (route.from_stop && stop.lat === route.from_stop.lat && stop.lng === route.from_stop.lng) return;
            if (route.to_stop && stop.lat === route.to_stop.lat && stop.lng === route.to_stop.lng) return;
            
            if (!state.stopMarkersMap[stop.id]) {
                const marker = L.circleMarker([stop.lat, stop.lng], { radius: 5, fillColor: route.color, color: '#07090e', weight: 1.5, fillOpacity: 0.85 })
                    .bindTooltip(stop.name, { permanent: true, direction: 'top', offset: [0, -4], className: 'stop-pin-label' });
                
                marker.addTo(map);
                state.stopMarkersMap[stop.id] = { marker: marker, routes: new Set([route.id]) };
            } else {
                state.stopMarkersMap[stop.id].routes.add(route.id);
            }
        });
        route.buses.forEach(bus => addOrUpdateBusMarker(bus, route, false));
    });
    
    const bounds = [];
    if (state.fromMarker) bounds.push(state.fromMarker.getLatLng());
    if (state.toMarker) bounds.push(state.toMarker.getLatLng());
    Object.values(state.busMarkers).forEach(m => bounds.push(m.getLatLng()));
    if (bounds.length) map.fitBounds(L.latLngBounds(bounds).pad(0.25));
}

function stopIcon(name, color, label) {
    return L.divIcon({
        className: '', iconSize: [28, 28], iconAnchor: [14, 14], popupAnchor: [0, -18],
        html: `<div style="width:28px;height:28px;border-radius:50%;background:${color}22;border:2px solid ${color};display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:${color};box-shadow:0 0 12px ${color}55;">${label}</div>
        <div style="position:absolute;top:30px;left:50%;transform:translateX(-50%);white-space:nowrap;font-size:9px;color:${color};background:rgba(7,9,14,.85);padding:2px 5px;border-radius:3px;border:1px solid ${color}44;">${name}</div>`
    });
}

function animateMarkerTo(marker, targetLatLng, duration) {
    if (marker._cfAnim) cancelAnimationFrame(marker._cfAnim);
    const start = marker.getLatLng(), startTime = performance.now();
    function step(now) {
        const t = Math.min((now - startTime) / duration, 1);
        marker.setLatLng([start.lat + (targetLatLng.lat - start.lat) * t, start.lng + (targetLatLng.lng - start.lng) * t]);
        marker._cfAnim = t < 1 ? requestAnimationFrame(step) : null;
    }
    marker._cfAnim = requestAnimationFrame(step);
}

function addOrUpdateBusMarker(bus, route, animate) {
    const ring = bus.status === 'Delayed' ? '#FF3D5A' : bus.status === 'Early' ? '#FFD600' : '#00FF94';
    const icon = L.divIcon({ className: '', iconSize: [34, 34], iconAnchor: [17, 17], popupAnchor: [0, -20],
        html: `<div style="width:34px;height:34px;border-radius:50%;background:${route.color}18;border:2px solid ${ring};display:flex;align-items:center;justify-content:center;font-size:16px;box-shadow:0 0 12px ${ring}66;animation:busPulse 2s infinite;">🚌</div>`
    });
    
    const popup = `<div class="popup-inner"><div class="popup-bus-id">${bus.id}</div><div class="popup-row"><span>Route</span><span style="color:${route.color}">${route.name}</span></div><div class="popup-row"><span>Status</span><span style="color:${ring}">${bus.status}</span></div><div class="popup-row"><span>Speed</span><span>${bus.speed || '—'}</span></div><div class="popup-row"><span>Dist. to Next</span><span>${bus.distance || '—'}</span></div><div class="popup-row"><span>Last stop</span><span>${bus.last_stop || '—'}</span></div><div class="popup-row"><span>Next stop</span><span>${bus.next_stop || '—'}</span></div><div class="popup-row"><span>ETA your stop</span><span>${bus.eta_from || '—'}</span></div><div class="popup-row"><span>ETA destination</span><span>${bus.eta_to || '—'}</span></div><div class="popup-row"><span>Occupancy</span><span style="color:${bus.occupancy > 80 ? '#FF3D5A' : bus.occupancy > 55 ? '#FFD600' : '#00FF94'}">${bus.occupancy}%</span></div></div>`;
    const tooltipHtml = `<div style="font-family:'DM Mono', monospace; font-size:11px; font-weight:600; text-align:center; line-height:1.2; padding: 2px;">${bus.speed || '--'}<br><span style="opacity: 0.8; font-size:9px;">${bus.distance || '--'}</span></div>`;
    
    const target = L.latLng(bus.lat, bus.lng);
    
    if (state.busMarkers[bus.id]) {
        const marker = state.busMarkers[bus.id];
        if (animate) animateMarkerTo(marker, target, TICK_MS * 0.9); else marker.setLatLng(target);
        marker.setIcon(icon); 
        marker.setPopupContent(popup); 
        marker.setTooltipContent(tooltipHtml);

        if (state.selectedBusId) {
            if (bus.id === state.selectedBusId) {
                if (!map.hasLayer(marker)) marker.addTo(map);
            } else {
                if (map.hasLayer(marker)) marker.remove();
            }
        } else {
            if (!map.hasLayer(marker)) marker.addTo(map);
        }
    } else {
        const marker = L.marker(target, { icon })
            .bindPopup(popup, { maxWidth: 220 })
            .bindTooltip(tooltipHtml, { permanent: true, direction: 'top', offset: [0, -20], className: 'bus-stats' });
        
        marker.on('click', () => { selectSingleBus(bus.id, route.id); });

        if (!state.selectedBusId || state.selectedBusId === bus.id) marker.addTo(map);
        state.busMarkers[bus.id] = marker;
    }
}

function clearMap() {
    Object.values(state.busMarkers).forEach(m => { if (m._cfAnim) cancelAnimationFrame(m._cfAnim); m.remove(); });
    state.busMarkers = {};
    Object.values(state.routeLines).forEach(l => l.remove());
    state.routeLines = {};
    if (state.stopMarkersMap) { Object.values(state.stopMarkersMap).forEach(item => item.marker.remove()); }
    state.stopMarkersMap = {};
    if (state.fromMarker) { state.fromMarker.remove(); state.fromMarker = null; }
    if (state.toMarker) { state.toMarker.remove(); state.toMarker = null; }
    document.getElementById('refresh-badge').classList.add('hidden');
}

(function boot() {
    try {
        initMap(); 
        startClock(); 
        initSocket();
        
        document.getElementById('results-area').innerHTML = `<div class="result-empty" style="text-align:center; padding-top:40px;"><div class="pulse-ring connecting" style="display:inline-block; margin-bottom:20px;"></div><br>Booting live radar...</div>`;
        
        fetch('/api/all-routes')
            .then(res => res.json())
            .then(data => {
                if (data.routes) {
                    state.activeRoutes = data.routes;
                    renderResults(data.routes, []);
                    renderMapRoutes(data.routes);
                }
            })
            .catch(() => showResults(`<div class="no-route-msg">Failed to load initial routes.</div>`));

        setupAutocomplete('from-input', 'from-dropdown', 'from-selected', (stop) => { state.fromStop = stop; });
        setupAutocomplete('to-input', 'to-dropdown', 'to-selected', (stop) => { state.toStop = stop; });
    } catch (err) { console.error('CityFlow boot() failed:', err); }
})();