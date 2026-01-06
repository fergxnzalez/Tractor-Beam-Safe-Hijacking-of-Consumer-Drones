# Tractor Beam: Safe-Hijacking of Consumer Drones 🚁🛰️

This repository contains a functional implementation of GPS spoofing hijacking strategies based on the research paper: *"Tractor Beam: Safe-hijacking of Consumer Drones with Adaptive GPS Spoofing"*.

The project uses the **ArduPilot (SITL)** simulator and the **DroneKit** library to demonstrate how an attacker can manipulate the trajectory of **Type I** and **Type II** drones safely and accurately.

## 📋 Repository Content

* `web_hijack.py`: Flask-based backend server managing drone connection, vector calculations, and simulation parameter injection.
* `templates/index.html`: Interactive web interface designed with modern CSS to input target coordinates ($p_{target}$) and monitor the attack status.

---

## 🚀 Implemented Hijacking Strategies

### Strategy A: Against Type I Drones (Static NOT IMPLEMENTED)
This strategy was not implemented due to the fact that is very simple, the mechanism to perform this strategy is changing the parameter `SIM_GPS1_GLTCH_X/Y` when the drone is in POSHOLD or LOITER mode to change it position. Then to see the result we must change that parameter to the value `0`.
Targeted at drones that use GPS to maintain a fixed position (e.g., DJI Phantom in LOITER or POSHOLD mode).
* **Mechanism**: A gradual displacement is injected into the GPS error parameters (`SIM_GPS1_GLTCH_X/Y`).
* **Effect**: The drone attempts to compensate for the perceived error by physically flying in the opposite direction of the glitch, allowing it to be "dragged" to a desired location.

### Strategy B: Against Type II Drones (Autopilot)
Designed for drones executing autonomous missions following waypoints (e.g., Parrot Bebop 2).
* **Mechanism**: Manipulation of the path-following algorithm.
* **Hijacking Formula**: The script calculates a fake position ($a$) using the paper's vector equation:
  $$a = p_{waypoint} + k \cdot (p_{target} - p_{init})$$
  where $k$ is a negative parameter that projects the GPS lie to the opposite side of the real target.



---

## 🛠️ Requirements & Installation

1.  **ArduPilot SITL**: Simulation environment configured and running.
2.  **Python Dependencies**:
    ```bash
    pip install flask dronekit
    ```
3.  **Compatibility**: The script includes an automatic patch for the `AttributeError: module 'collections' has no attribute 'MutableMapping'` error common in Python 3.10+.

---

## 💻 Usage Instructions

1.  **Start SITL**:
    ```bash
    sim_vehicle.py -v ArduCopter --console --map
    ```
2.  **Prepare the Drone**: 
    * Load a mission with waypoints in Mission Planner and click **"Write WPs"**.
    * Take off and switch the drone to `AUTO` mode so it begins the mission.
3.  **Launch the Server**:
    ```bash
    python3 web_hijack.py
    ```
4.  **Control Interface**: Access `http://localhost:5000` in your browser.
    * Enter the target coordinates.
    * Click **EXECUTE HIJACK**.
    * Use **UNDO GLITCH** to release the drone, return to `GUIDED` mode, and view the final precision report.

---

## 📊 Result Validation

Upon ending the attack, the system uses the **Haversine formula** to calculate the distance between the drone's real position and the requested target. 
* The attack is marked as **SUCCESSFUL** if the final distance is within 15 meters, meeting the precision standards reported in the study (average angular error of $5.13^{\circ}$).

---

## ⚖️ License, Privacy, and Ethical Use

### License
This project is licensed under the **MIT License**. You are free to use, copy, and modify the software as long as the copyright notice and disclaimer are retained.

### Ethical Use and Responsibility
This software was developed strictly for **academic and research purposes**. The goal is to help the cybersecurity community understand commercial drone vulnerabilities and develop better defense systems (such as spoofing detection).

* **Malicious Use Prohibited**: The author is not responsible for any misuse of this code in real-world environments.
* **Legality**: GPS spoofing and signal interference are heavily regulated and often illegal. This code should be executed **only in simulation environments (SITL)**.

### Privacy
This project does not collect personal data. However, when working with telemetry:
1.  **Network Security**: Run the Flask server on a secure or isolated local network.
2.  **Flight Logs**: Ensure you do not upload telemetry files (`.tlog` or `.bin`) that might contain real coordinates of your physical location if testing outside of simulation.
