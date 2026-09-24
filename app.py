from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import random, threading, time, math, requests

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

STOPS = {
    "railway_station":   {"name": "Railway Station",        "lat": 30.3165, "lng": 78.0322},
    "clock_tower":       {"name": "Clock Tower",            "lat": 30.3244, "lng": 78.0339},
    "isbt":              {"name": "ISBT Dehradun",          "lat": 30.2888, "lng": 78.0000},
    "paltan_bazaar":     {"name": "Paltan Bazaar",          "lat": 30.3210, "lng": 78.0367},
    "rispana_bridge":    {"name": "Rispana Bridge",         "lat": 30.3050, "lng": 78.0580},
    "doon_hospital":     {"name": "Doon Hospital",          "lat": 30.3189, "lng": 78.0421},
    "survey_chowk":      {"name": "Survey Chowk",           "lat": 30.3295, "lng": 78.0441},
    "ec_road":           {"name": "EC Road",                "lat": 30.3320, "lng": 78.0280},
    "rajpur_road":       {"name": "Rajpur Road",            "lat": 30.3410, "lng": 78.0510},
    "haridwar_road":     {"name": "Haridwar Road",          "lat": 30.2850, "lng": 78.0200},
    "mussoorie_road":    {"name": "Mussoorie Road",         "lat": 30.3550, "lng": 78.0650},
    "prem_nagar":        {"name": "Prem Nagar",             "lat": 30.3100, "lng": 77.9950},
    "sahastradhara":     {"name": "Sahastradhara",          "lat": 30.3780, "lng": 78.1100},
    "it_park":           {"name": "IT Park",                "lat": 30.3700, "lng": 77.9820},
    "ballupur_chowk":    {"name": "Ballupur Chowk",         "lat": 30.3480, "lng": 78.0370},
    "gandhi_road":       {"name": "Gandhi Road",            "lat": 30.3270, "lng": 78.0310},
    "chakrata_road":     {"name": "Chakrata Road",          "lat": 30.3350, "lng": 77.9980},
    "mothrowala":        {"name": "Mothrowala",             "lat": 30.2750, "lng": 77.9800},
    "dalanwala":         {"name": "Dalanwala",              "lat": 30.3150, "lng": 78.0520},
    "nehru_colony":      {"name": "Nehru Colony",           "lat": 30.3080, "lng": 78.0430},
    "vasant_vihar":      {"name": "Vasant Vihar",           "lat": 30.3350, "lng": 78.0150},
    "rajendra_nagar":    {"name": "Rajendra Nagar",         "lat": 30.3050, "lng": 78.0350},
    "kishanpur":         {"name": "Kishanpur",              "lat": 30.3120, "lng": 78.0050},
    "clement_town":      {"name": "Clement Town",           "lat": 30.2800, "lng": 78.0000},
    "selaqui":           {"name": "Selaqui",                "lat": 30.3600, "lng": 77.8600},
    "race_course":       {"name": "Race Course",            "lat": 30.3050, "lng": 78.0480},
    "adhoiwala":         {"name": "Adhoiwala",              "lat": 30.3000, "lng": 78.0450},
    "kargi_chowk":       {"name": "Kargi Chowk",            "lat": 30.3300, "lng": 77.9900},
    "niranjanpur":       {"name": "Niranjanpur",            "lat": 30.3550, "lng": 78.0450},
    "jakhan":            {"name": "Jakhan",                 "lat": 30.3450, "lng": 78.0700},
    "karanpur":          {"name": "Karanpur",               "lat": 30.3280, "lng": 78.0420},
    "dharampur":         {"name": "Dharampur",              "lat": 30.3400, "lng": 78.0850},
    "vikasnagar_road":   {"name": "Vikasnagar Road",        "lat": 30.3700, "lng": 77.9000},
    "lachhiwala":        {"name": "Lachhiwala",              "lat": 30.2600, "lng": 78.1100},
    "rani_bagh":         {"name": "Rani Bagh",              "lat": 30.3230, "lng": 78.0300},
    "saharanpur_chowk":  {"name": "Saharanpur Chowk",       "lat": 30.2900, "lng": 78.0050},
}

ROUTES = [
    {"id": "R01", "name": "Karanpur → ISBT", "color": "#00C9FF", "stops": ["karanpur", "clock_tower", "gandhi_road", "paltan_bazaar", "railway_station", "doon_hospital", "dalanwala", "adhoiwala", "race_course", "nehru_colony", "rispana_bridge", "isbt"]},
    {"id": "R02", "name": "Rani Bagh → Jakhan", "color": "#FF6B35", "stops": ["rani_bagh", "clock_tower", "survey_chowk", "ec_road", "ballupur_chowk", "rajpur_road", "jakhan"]},
    {"id": "R03", "name": "Prem Nagar → Sahastradhara", "color": "#A8FF78", "stops": ["prem_nagar", "chakrata_road", "vasant_vihar", "clock_tower", "survey_chowk", "rajpur_road", "niranjanpur", "dharampur", "sahastradhara"]},
    {"id": "R04", "name": "Mothrowala → Mussoorie Road", "color": "#FFD700", "stops": ["mothrowala", "clement_town", "saharanpur_chowk", "haridwar_road", "isbt", "rispana_bridge", "dalanwala", "doon_hospital", "railway_station", "rajendra_nagar", "clock_tower", "ballupur_chowk", "mussoorie_road"]},
    {"id": "R05", "name": "IT Park → Nehru Colony", "color": "#FF6EFF", "stops": ["it_park", "chakrata_road", "kargi_chowk", "kishanpur", "ec_road", "gandhi_road", "paltan_bazaar", "railway_station", "doon_hospital", "nehru_colony"]},
    {"id": "R06", "name": "Selaqui → Lachhiwala", "color": "#B983FF", "stops": ["selaqui", "vikasnagar_road", "chakrata_road", "kargi_chowk", "clock_tower", "survey_chowk", "doon_hospital", "rispana_bridge", "lachhiwala"]}
]
ROUTES_BY_ID = {r["id"]: r for r in ROUTES}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
HTTP_HEADERS = {"User-Agent": "CityFlow-Dehradun-Demo/1.0"}
DEHRADUN_VIEWBOX = "77.85,30.43,78.20,30.24"

def geocode_places(query, limit=5):
    try:
        resp = requests.get(NOMINATIM_URL, params={"q": query, "format": "json", "viewbox": DEHRADUN_VIEWBOX, "bounded": 1, "limit": limit}, headers=HTTP_HEADERS, timeout=3)
        resp.raise_for_status()
        out = []
        for item in resp.json():
            display = item.get("display_name", "")
            out.append({"id": f"geo:{item['lat']},{item['lon']}", "name": display.split(",")[0].strip() or query, "full_name": display, "lat": float(item["lat"]), "lng": float(item["lon"]), "source": "map"})
        return out
    except Exception: return []

def get_distance_m(lat1, lon1, lat2, lon2):
    R = 6371e3
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def nearest_stop(lat, lng):
    best_id, best_dist = None, float("inf")
    for sid, sdata in STOPS.items():
        d = get_distance_m(lat, lng, sdata["lat"], sdata["lng"])
        if d < best_dist: best_id, best_dist = sid, d
    return best_id, best_dist / 1000

def resolve_stop_id(value):
    if not value: return None, None
    if value in STOPS: return value, None
    if value.startswith("geo:"):
        try:
            lat_s, lng_s = value[4:].split(",")
            sid, dist_km = nearest_stop(float(lat_s), float(lng_s))
            return sid, round(dist_km, 2)
        except Exception: return None, None
    q = value.lower().strip()
    for sid, sdata in STOPS.items():
        if sdata["name"].lower() == q: return sid, None
    for sid, sdata in STOPS.items():
        if q in sdata["name"].lower(): return sid, None
    return None, None

def search_stop(query):
    q = query.lower().strip()
    matches = []
    for sid, sdata in STOPS.items():
        if q in sdata["name"].lower():
            matches.append({"id": sid, "name": sdata["name"], "lat": sdata["lat"], "lng": sdata["lng"], "source": "stop"})
    return matches

ROAD_ROUTE_CACHE = {}
road_route_lock = threading.Lock()

def generate_straight_route(route):
    points = []
    stop_cum = []
    point_cum = []
    dist = 0.0
    for i, sid in enumerate(route["stops"]):
        lat, lng = STOPS[sid]["lat"], STOPS[sid]["lng"]
        points.append([lat, lng])
        if i > 0:
            prev_lat, prev_lng = points[-2]
            dist += get_distance_m(prev_lat, prev_lng, lat, lng)
        stop_cum.append(dist)
        point_cum.append(dist)
    return {"points": points, "point_cum": point_cum, "stop_cum": stop_cum, "total_dist": dist}

def fetch_road_route(route):
    coords = ";".join(f"{STOPS[s]['lng']},{STOPS[s]['lat']}" for s in route["stops"])
    url = f"{OSRM_URL}/{coords}"
    headers = {"User-Agent": "CityFlow-Dehradun-App/1.0"}
    try:
        resp = requests.get(url, params={"overview": "full", "geometries": "geojson", "continue_straight": "true"}, headers=headers, timeout=6)
        data = resp.json()
        if data.get("code") != "Ok":
            resp = requests.get(url, params={"overview": "full", "geometries": "geojson"}, headers=headers, timeout=6)
            data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"): 
            return generate_straight_route(route)
        route_data = data["routes"][0]
        points = [[lat, lng] for lng, lat in route_data["geometry"]["coordinates"]]
        if len(points) < 2: return generate_straight_route(route)
        legs = route_data["legs"]
        stop_cum = [0.0]
        for leg in legs: stop_cum.append(stop_cum[-1] + leg["distance"])
        point_cum = [0.0]
        for i in range(1, len(points)):
            d = get_distance_m(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1])
            point_cum.append(point_cum[-1] + d)
        return {"points": points, "point_cum": point_cum, "stop_cum": stop_cum, "total_dist": point_cum[-1]}
    except Exception:
        return generate_straight_route(route)

def get_road_route(route):
    rid = route["id"]
    with road_route_lock:
        if rid in ROAD_ROUTE_CACHE: return ROAD_ROUTE_CACHE[rid]
    road = fetch_road_route(route)
    with road_route_lock: ROAD_ROUTE_CACHE[rid] = road
    return road

def interpolate_path(points, point_cum, target_dist):
    if target_dist <= 0: return points[0][0], points[0][1]
    if target_dist >= point_cum[-1]: return points[-1][0], points[-1][1]
    for i in range(len(point_cum) - 1):
        if point_cum[i] <= target_dist <= point_cum[i+1]:
            seg_len = point_cum[i+1] - point_cum[i]
            if seg_len == 0: return points[i][0], points[i][1]
            frac = (target_dist - point_cum[i]) / seg_len
            lat = points[i][0] + frac * (points[i+1][0] - points[i][0])
            lng = points[i][1] + frac * (points[i+1][1] - points[i][1])
            return round(lat, 5), round(lng, 5)
    return points[-1][0], points[-1][1]

def estimate_eta_backend(route, live, target_stop_id):
    stops = route["stops"]
    if target_stop_id not in stops: return None
    road = get_road_route(route)
    target_idx = stops.index(target_stop_id)
    target_dist = road["stop_cum"][target_idx]
    
    if live["direction"] == -1: return "Opposite Dir."
    if target_dist < live["dist"]: return "Passed"
    rem_m = target_dist - live["dist"]
    if live.get("pause_time", 0) > 0 and rem_m == 0: return "At Stop"
    mins = round((rem_m / 1000) / (live["speed_display"] / 60))
    return f"{max(mins, 1)} min"

def find_journey_bfs(from_id, to_id):
    direct = [r for r in ROUTES if from_id in r["stops"] and to_id in r["stops"]]
    if direct: return {"type": "direct", "routes": direct}
    
    start_routes = [r["id"] for r in ROUTES if from_id in r["stops"]]
    end_routes = [r["id"] for r in ROUTES if to_id in r["stops"]]
    
    if not start_routes or not end_routes: return {"type": "none"}
        
    queue = []
    for sr in start_routes: queue.append((sr, [sr], []))
        
    visited = set(start_routes)
    
    while queue:
        curr_r_id, path, transfers = queue.pop(0)
        
        if curr_r_id in end_routes:
            routes_in_path = [ROUTES_BY_ID[rid] for rid in path]
            return {"type": "transfer", "route_path": routes_in_path, "transfers": transfers}
            
        curr_route = ROUTES_BY_ID[curr_r_id]
        curr_stops = set(curr_route["stops"])
        
        for next_route in ROUTES:
            nr_id = next_route["id"]
            if nr_id not in visited:
                common = curr_stops.intersection(set(next_route["stops"]))
                if common:
                    t_stop = list(common)[0]
                    visited.add(nr_id)
                    queue.append((nr_id, path + [nr_id], transfers + [t_stop]))
                    
    return {"type": "none"}

def routes_serving_both(from_stop_id, to_stop_id):
    results = []
    for route in ROUTES:
        stops = route["stops"]
        if from_stop_id in stops and to_stop_id in stops:
            results.append(route)
    return results

TICK_SECONDS = 2.0
bus_lock = threading.Lock()
BUS_STATE = {}

def init_bus_state():
    with bus_lock:
        for route in ROUTES:
            stops = route["stops"]
            route["active_bus_ids"] = []
            road = get_road_route(route)
            for i in range(len(stops) - 1):
                bus_id = f"{route['id']}_bus_{i}"
                route["active_bus_ids"].append(bus_id)
                start_dist = (road["stop_cum"][i] + road["stop_cum"][i+1]) / 2.0
                lat, lng = interpolate_path(road["points"], road["point_cum"], start_dist)
                speed_kmh = random.randint(30, 45)
                BUS_STATE[bus_id] = {
                    "route_id": route["id"], "dist": start_dist, "direction": 1,
                    "last_stop_idx": i, "next_stop_idx": i + 1, "pause_time": 0.0,
                    "status": "On Time", "occupancy": random.randint(10, 80),
                    "type": random.choice(["Bus", "Shared Van", "Shared Cab"]),
                    "lat": lat, "lng": lng, "speed_display": speed_kmh,
                    "speed_m_tick": (speed_kmh * 1000 / 3600) * TICK_SECONDS
                }

def advance_bus_state():
    changed = {}
    with bus_lock:
        for bus_id, live in BUS_STATE.items():
            route = ROUTES_BY_ID[live["route_id"]]
            road = get_road_route(route)
            
            if live.get("pause_time", 0) > 0:
                live["pause_time"] -= TICK_SECONDS
                speed_display = "0 km/h"
                lat = STOPS[route["stops"][live["last_stop_idx"]]]["lat"]
                lng = STOPS[route["stops"][live["last_stop_idx"]]]["lng"]
                live["lat"], live["lng"] = lat, lng
                dist_text = "At Stop"
            else:
                direction = live["direction"]
                live["dist"] += live["speed_m_tick"] * direction
                passed = False
                
                if direction == 1:
                    target_dist = road["stop_cum"][live["next_stop_idx"]]
                    if live["dist"] >= target_dist:
                        live["dist"] = target_dist
                        live["last_stop_idx"] = live["next_stop_idx"]
                        if live["next_stop_idx"] < len(route["stops"]) - 1:
                            live["next_stop_idx"] += 1
                            passed = True
                        else:
                            live["direction"] = -1
                            live["next_stop_idx"] = live["last_stop_idx"] - 1
                            passed = True
                else: 
                    target_dist = road["stop_cum"][live["next_stop_idx"]]
                    if live["dist"] <= target_dist:
                        live["dist"] = target_dist
                        live["last_stop_idx"] = live["next_stop_idx"]
                        if live["next_stop_idx"] > 0:
                            live["next_stop_idx"] -= 1
                            passed = True
                        else:
                            live["direction"] = 1
                            live["next_stop_idx"] = 1
                            passed = True

                if passed: live["pause_time"] = 10.0
                
                lat, lng = interpolate_path(road["points"], road["point_cum"], live["dist"])
                live["lat"], live["lng"] = lat, lng
                speed_display = f"{live['speed_display']} km/h"
                dist_m = abs(road["stop_cum"][live["next_stop_idx"]] - live["dist"])
                dist_text = f"{int(dist_m)} m"

            if random.random() < 0.04:
                live["status"] = random.choices(["On Time", "Delayed", "Early"], weights=[70, 20, 10])[0]
            live["occupancy"] = max(5, min(98, live["occupancy"] + random.randint(-4, 4)))

            changed[bus_id] = {
                "route_id": live["route_id"], "lat": live["lat"], "lng": live["lng"],
                "status": live["status"], "occupancy": live["occupancy"], "direction": live["direction"],
                "progress": round(live["dist"] / max(road["total_dist"], 1), 4),
                "last_stop": STOPS[route["stops"][live["last_stop_idx"]]]["name"],
                "next_stop": STOPS[route["stops"][live["next_stop_idx"]]]["name"],
                "speed": speed_display, "distance": dist_text
            }
    return changed

def simulation_loop():
    while True:
        socketio.sleep(TICK_SECONDS)
        payload = advance_bus_state()
        socketio.emit("bus_positions", {"buses": payload, "ts": time.time()})

@app.route('/')
def home(): return render_template('index.html')

@app.route('/api/all-routes')
def all_routes_api():
    result_routes = []
    with bus_lock:
        for route in ROUTES:
            stops_data = [{"id": s, **STOPS[s]} for s in route["stops"]]
            road = get_road_route(route)
            road_points = road["points"] if road else [[STOPS[s]["lat"], STOPS[s]["lng"]] for s in route["stops"]]
            buses_data = []
            for bus_id in route.get("active_bus_ids", []):
                live = BUS_STATE[bus_id]
                next_lat = STOPS[route["stops"][live["next_stop_idx"]]]["lat"]
                next_lng = STOPS[route["stops"][live["next_stop_idx"]]]["lng"]
                dist_m = get_distance_m(live["lat"], live["lng"], next_lat, next_lng)
                speed_str = "0 km/h" if live.get("pause_time", 0) > 0 else f"{live['speed_display']} km/h"
                dist_str = "At Stop" if live.get("pause_time", 0) > 0 else f"{int(dist_m)} m"
                buses_data.append({
                    "id": bus_id, "lat": live["lat"], "lng": live["lng"], "status": live["status"], 
                    "occupancy": live["occupancy"], "type": live.get("type", "Bus"), "eta_from": None, "eta_to": None,
                    "progress": round(live["dist"] / max(road["total_dist"], 1), 3), "direction": live["direction"],
                    "last_stop": STOPS[route["stops"][live["last_stop_idx"]]]["name"],
                    "next_stop": STOPS[route["stops"][live["next_stop_idx"]]]["name"], "speed": speed_str, "distance": dist_str
                })
            result_routes.append({
                "id": route["id"], "name": route["name"], "color": route["color"], "stops": stops_data, 
                "road_points": road_points, "road_matched": road is not None, "buses": buses_data,
                "stop_cum": road["stop_cum"] if road else [0 for _ in route["stops"]],
                "total_dist": road["total_dist"] if road else 1
            })
    return jsonify({"routes": result_routes})

@app.route('/api/stops/search')
def stops_search():
    query = request.args.get('q', '').strip()
    if len(query) < 2: return jsonify([])
    
    local = search_stop(query)
    if local:
        return jsonify(local[:6])
        
    remote = geocode_places(f"{query}, Dehradun, Uttarakhand, India")
    return jsonify(remote[:4])

@app.route('/api/find-buses')
def find_buses():
    from_raw, to_raw = request.args.get('from', '').strip(), request.args.get('to', '').strip()
    if not from_raw or not to_raw: return jsonify({"error": "Both from and to stop required"}), 400
    from_id, from_snap_km = resolve_stop_id(from_raw)
    to_id, to_snap_km = resolve_stop_id(to_raw)

    if not from_id or not to_id: return jsonify({"error": "Couldn't match stops."}), 400
    if from_id == to_id: return jsonify({"error": "Start and destination cannot be same"}), 400
    
    journey = find_journey_bfs(from_id, to_id)
    if journey["type"] == "none": 
        return jsonify({"routes": [], "message": "No routes found connecting these stops."})

    result_routes = []
    notes = []
    if from_snap_km is not None: notes.append(f'"{from_raw}" matched nearest: {STOPS[from_id]["name"]}')
    if to_snap_km is not None: notes.append(f'"{to_raw}" matched nearest: {STOPS[to_id]["name"]}')

    def process_route(route, r_from_id, r_to_id, is_transfer=False):
        stops_data = [{"id": s, **STOPS[s]} for s in route["stops"]]
        road = get_road_route(route)
        road_points = road["points"] if road else [[STOPS[s]["lat"], STOPS[s]["lng"]] for s in route["stops"]]
        buses_data = []
        for bus_id in route.get("active_bus_ids", []):
            live = BUS_STATE[bus_id]
            next_lat = STOPS[route["stops"][live["next_stop_idx"]]]["lat"]
            next_lng = STOPS[route["stops"][live["next_stop_idx"]]]["lng"]
            speed_str = "0 km/h" if live.get("pause_time", 0) > 0 else f"{live['speed_display']} km/h"
            dist_str = "At Stop" if live.get("pause_time", 0) > 0 else f"{int(get_distance_m(live['lat'], live['lng'], next_lat, next_lng))} m"
            buses_data.append({
                "id": bus_id, "lat": live["lat"], "lng": live["lng"], "status": live["status"], 
                "occupancy": live["occupancy"], "type": live.get("type", "Bus"),
                "eta_from": estimate_eta_backend(route, live, r_from_id), "eta_to": estimate_eta_backend(route, live, r_to_id),
                "progress": round(live["dist"] / max(road["total_dist"], 1), 3), "direction": live["direction"],
                "last_stop": STOPS[route["stops"][live["last_stop_idx"]]]["name"],
                "next_stop": STOPS[route["stops"][live["next_stop_idx"]]]["name"], "speed": speed_str, "distance": dist_str
            })
        return {
            "id": route["id"], "name": route["name"], "color": route["color"], "stops": stops_data, 
            "road_points": road_points, "road_matched": road is not None, "buses": buses_data, 
            "from_stop": {"id": r_from_id, **STOPS[r_from_id]}, "to_stop": {"id": r_to_id, **STOPS[r_to_id]},
            "search_from_id": r_from_id, "search_to_id": r_to_id,
            "stop_cum": road["stop_cum"] if road else [0 for _ in route["stops"]],
            "total_dist": road["total_dist"] if road else 1,
            "is_transfer_leg": is_transfer
        }

    with bus_lock:
        if journey["type"] == "direct":
            for r in journey["routes"]:
                result_routes.append(process_route(r, from_id, to_id, False))
        elif journey["type"] == "transfer":
            path = journey["route_path"]
            transfers = journey["transfers"]
            note_str = "Transfer Required: "
            for i, r in enumerate(path):
                if i == 0:
                    start_s = from_id
                    end_s = transfers[i]
                    note_str += f"Take {r['name']} to {STOPS[end_s]['name']}, "
                elif i == len(path) - 1:
                    start_s = transfers[i-1]
                    end_s = to_id
                    note_str += f"then change to {r['name']} to reach destination."
                else:
                    start_s = transfers[i-1]
                    end_s = transfers[i]
                    note_str += f"change to {r['name']} going to {STOPS[end_s]['name']}, "
                result_routes.append(process_route(r, start_s, end_s, True))
            notes.append(note_str)

    return jsonify({"routes": result_routes, "notes": notes})

_simulation_started = False
_simulation_start_lock = threading.Lock()

@socketio.on('connect')
def on_connect():
    global _simulation_started
    with _simulation_start_lock:
        if not _simulation_started:
            socketio.start_background_task(simulation_loop)
            _simulation_started = True
    
    snapshot = {}
    with bus_lock:
        for bus_id, live in BUS_STATE.items():
            route = ROUTES_BY_ID[live["route_id"]]
            road = get_road_route(route)
            next_lat = STOPS[route["stops"][live["next_stop_idx"]]]["lat"]
            next_lng = STOPS[route["stops"][live["next_stop_idx"]]]["lng"]
            speed_str = "0 km/h" if live.get("pause_time", 0) > 0 else f"{live['speed_display']} km/h"
            dist_str = "At Stop" if live.get("pause_time", 0) > 0 else f"{int(get_distance_m(live['lat'], live['lng'], next_lat, next_lng))} m"
            
            snapshot[bus_id] = {
                "route_id": live["route_id"], "lat": live["lat"], "lng": live["lng"],
                "status": live["status"], "occupancy": live["occupancy"], 
                "progress": round(live["dist"] / max(road["total_dist"], 1), 3),
                "direction": live["direction"],
                "last_stop": STOPS[route["stops"][live["last_stop_idx"]]]["name"], 
                "next_stop": STOPS[route["stops"][live["next_stop_idx"]]]["name"],
                "speed": speed_str, "distance": dist_str
            }
    socketio.emit("bus_positions", {"buses": snapshot, "ts": time.time()}, to=request.sid)

init_bus_state()

if __name__ == '__main__':
    socketio.run(app, debug=True)