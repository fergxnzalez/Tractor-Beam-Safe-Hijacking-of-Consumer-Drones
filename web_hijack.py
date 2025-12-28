import collections
import time
import math
from flask import Flask, render_template, request, jsonify
from dronekit import connect, VehicleMode

if not hasattr(collections, 'MutableMapping'):
    import collections.abc
    collections.MutableMapping = collections.abc.MutableMapping

app = Flask(__name__)

vehicle = connect('127.0.0.1:14551', wait_ready=True)

last_target = {"lat": 0, "lon": 0}

def compute_distance_meters(loc1, loc2):
    R = 6371000
    phi1, phi2 = math.radians(loc1['lat']), math.radians(loc2['lat'])
    dphi = math.radians(loc2['lat'] - loc1['lat'])
    dlambda = math.radians(loc2['lon'] - loc1['lon'])
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute():
    global last_target
    data = request.json
    last_target = {'lat': float(data['lat']), 'lon': float(data['lon'])}
    
    vehicle.parameters['FS_EKF_THRESH'] = 1.0
    
    p_init = {'lat': vehicle.location.global_relative_frame.lat, 
              'lon': vehicle.location.global_relative_frame.lon}
    
    cmds = vehicle.commands
    cmds.download()
    cmds.wait_ready()
    
    current_wp_idx = vehicle.commands.next
    if current_wp_idx <= 0:
        return jsonify({"status": "error", "message": "Start the mission in Mission Planner first!"})

    p_waypoint = {'lat': cmds[current_wp_idx-1].x, 'lon': cmds[current_wp_idx-1].y}

    k = -2.5
    lat_falsa = p_waypoint['lat'] + k * (last_target['lat'] - p_init['lat'])
    lon_falsa = p_waypoint['lon'] + k * (last_target['lon'] - p_init['lon'])

    vehicle.mode = VehicleMode("AUTO")
    
    vehicle.parameters['SIM_GPS1_GLTCH_Y'] = lat_falsa - p_init['lat']
    vehicle.parameters['SIM_GPS1_GLTCH_X'] = lon_falsa - p_init['lon']
    
    return jsonify({"status": "success", "message": "Attack successfully initiated"})

@app.route('/undo', methods=['POST'])
def undo():
    vehicle.parameters['SIM_GPS1_GLTCH_Y'] = 0
    vehicle.parameters['SIM_GPS1_GLTCH_X'] = 0
    vehicle.mode = VehicleMode("GUIDED")
    
    p_actual = {'lat': vehicle.location.global_relative_frame.lat, 'lon': vehicle.location.global_relative_frame.lon}
    distancia = compute_distance_meters(p_actual, last_target)
    exito = distancia < 10.0
    
    return jsonify({"status": "success", "message": f"Distance: {distancia:.2f}m. {'ACCOMPLISHED' if exito else 'FAILED'}", "SUCCESS": exito})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
