from flask import Flask, render_template, request, jsonify
from spoofer import DroneSpoofer

app = Flask(__name__)
spoofer = DroneSpoofer()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/connect', methods=['POST'])
def connect_vehicle():
    ip = request.json.get('ip', '127.0.0.1:14550')
    try:
        msg = spoofer.connect_drone(ip)
        return jsonify({'status': 'success', 'message': msg})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/takeoff', methods=['POST'])
def takeoff():
    # Nueva ruta para el botón de despegue
    success, msg = spoofer.takeoff_sequence(altitude=15)
    status = 'success' if success else 'error'
    return jsonify({'status': status, 'message': msg})

@app.route('/status', methods=['GET'])
def vehicle_status():
    return jsonify(spoofer.get_status())

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    success, msg = spoofer.start_attack(
        data.get('strategy'), 
        float(data.get('n_offset', 0)), 
        float(data.get('e_offset', 0)), 
        float(data.get('param', 0))
    )
    return jsonify({'status': 'success' if success else 'error', 'message': msg})

@app.route('/stop', methods=['POST'])
def stop():
    return jsonify({'status': 'success', 'message': spoofer.stop_attack()})

if __name__ == '__main__':
    app.run(debug=True, port=5000)