import collections
import time
import math
from flask import Flask, render_template, request, jsonify
from dronekit import connect, VehicleMode

# Parche DroneKit
if not hasattr(collections, 'MutableMapping'):
    import collections.abc
    collections.MutableMapping = collections.abc.MutableMapping

app = Flask(__name__)

# Conexión al SITL - Asegúrate de que el puerto coincida con tu sim_vehicle
vehicle = connect('127.0.0.1:14551', wait_ready=True)

ultimo_target = {"lat": 0, "lon": 0}

def calcular_distancia_metros(loc1, loc2):
    R = 6371000
    phi1, phi2 = math.radians(loc1['lat']), math.radians(loc2['lat'])
    dphi = math.radians(loc2['lat'] - loc1['lat'])
    dlambda = math.radians(loc2['lon'] - loc1['lon'])
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1-a)))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ejecutar', methods=['POST'])
def ejecutar():
    global ultimo_target
    data = request.json
    ultimo_target = {'lat': float(data['lat']), 'lon': float(data['lon'])}
    
    # RELAJAR EKF: Es vital para que el dron no ignore el glitch [cite: 806]
    vehicle.parameters['FS_EKF_THRESH'] = 1.0
    
    p_init = {'lat': vehicle.location.global_relative_frame.lat, 
              'lon': vehicle.location.global_relative_frame.lon}
    
    cmds = vehicle.commands
    cmds.download()
    cmds.wait_ready()
    
    # Asegurar que hay una misión y el índice es válido 
    current_wp_idx = vehicle.commands.next
    if current_wp_idx <= 0:
        return jsonify({"status": "error", "message": "Inicia la misión en Mission Planner primero!"})

    p_waypoint = {'lat': cmds[current_wp_idx-1].x, 'lon': cmds[current_wp_idx-1].y}

    # CÁLCULO VECTORIAL: Basado en la fórmula a = p_waypoint + k * (p_target - p_init) [cite: 495]
    k = -2.5
    lat_falsa = p_waypoint['lat'] + k * (ultimo_target['lat'] - p_init['lat'])
    lon_falsa = p_waypoint['lon'] + k * (ultimo_target['lon'] - p_init['lon'])

    # CAMBIO DE MODO: El dron DEBE estar en AUTO para que el rastro se actualice 
    vehicle.mode = VehicleMode("AUTO")
    
    # INYECCIÓN: El glitch es la diferencia entre la mentira calculada y la realidad actual [cite: 412]
    vehicle.parameters['SIM_GPS1_GLTCH_Y'] = lat_falsa - p_init['lat']
    vehicle.parameters['SIM_GPS1_GLTCH_X'] = lon_falsa - p_init['lon']
    
    return jsonify({"status": "success", "message": "Ataque iniciado con éxito"})
@app.route('/deshacer', methods=['POST'])
def deshacer():
    vehicle.parameters['SIM_GPS1_GLTCH_Y'] = 0
    vehicle.parameters['SIM_GPS1_GLTCH_X'] = 0
    vehicle.mode = VehicleMode("GUIDED")
    
    p_actual = {'lat': vehicle.location.global_relative_frame.lat, 'lon': vehicle.location.global_relative_frame.lon}
    distancia = calcular_distancia_metros(p_actual, ultimo_target)
    exito = distancia < 10.0
    
    return jsonify({"status": "success", "message": f"Distancia: {distancia:.2f}m. {'LOGRADO' if exito else 'FALLIDO'}", "exito": exito})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)