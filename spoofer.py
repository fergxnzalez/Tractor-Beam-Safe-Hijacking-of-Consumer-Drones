import time
import math
import threading
from dronekit import connect, VehicleMode, LocationGlobalRelative
from pymavlink import mavutil

# --- EARTH CONSTANTS FOR PROJECTION ---
R_EARTH = 6378137.0  # Earth radius in meters

def get_distance_metres(aLocation1, aLocation2):
    """
    Calculates the ground distance between two Location objects.
    Approximate method using simple spherical projection.
    """
    dlat = aLocation2.lat - aLocation1.lat
    dlong = aLocation2.lon - aLocation1.lon
    return math.sqrt((dlat*dlat) + (dlong*dlong)) * 1.113195e5

class DroneSpoofer:
    def __init__(self):
        self.vehicle = None
        self.running = False
        self.thread = None
        # Real-time attack telemetry
        self.attack_metrics = {
            "active": False,
            "phase": "IDLE", # IDLE, JAMMING, DRIFTING
            "distance_moved": 0.0,
            "spoofed_dist": 0.0
        }

    def connect_drone(self, connection_string):
        """Establish connection via MAVLink."""
        try:
            # print(f"[*] Connecting to: {connection_string}")
            self.vehicle = connect(connection_string, wait_ready=True, heartbeat_timeout=15)
            return "Connection Successful"
        except Exception as e:
            raise Exception(f"Error: {str(e)}")

    def get_status(self):
        """Returns a dict with the current vehicle telemetry."""
        if not self.vehicle:
            return {"connected": False}
        
        return {
            "connected": True,
            "armed": self.vehicle.armed,
            "mode": self.vehicle.mode.name,
            "alt": self.vehicle.location.global_relative_frame.alt,
            "gps_fix": self.vehicle.gps_0.fix_type,
            "satellites": self.vehicle.gps_0.satellites_visible,
            # Attack metrics for logging purposes
            "attack_data": self.attack_metrics
        }

    def takeoff_sequence(self, altitude=10):
        """
        Automates: Arm -> Takeoff -> Wait for Alt -> Switch to LOITER/POSHOLD.
        Prepares the scenario for Strategy A (Position Hold Drifting).
        """
        if not self.vehicle or not self.vehicle.is_armable:
            return False, "Drone not ready to arm (Check GPS/Health)"

        def _takeoff_thread():
            # print("[*] Starting Takeoff Sequence...")
            self.vehicle.mode = VehicleMode("GUIDED")
            self.vehicle.armed = True
            while not self.vehicle.armed:
                time.sleep(0.1)
            
            # print("[*] Motors active. Taking off...")
            self.vehicle.simple_takeoff(altitude)
            
            # Wait to reach safe altitude
            while True:
                current_alt = self.vehicle.location.global_relative_frame.alt
                if current_alt >= altitude * 0.95:
                    break
                time.sleep(1)
            
            # print("[*] Altitude reached. Switching to POSHOLD (Simulating Type I)...")
            self.vehicle.mode = VehicleMode("POSHOLD")
        
        t = threading.Thread(target=_takeoff_thread)
        t.start()
        return True, "Takeoff sequence initiated. Waiting for POSHOLD."

    def _send_mavlink_gps(self, lat, lon, alt, fix_type, satellites):
        """
        Sends raw GPS_INPUT mavlink messages.
        Used for 'Hard Spoofing' / Jamming simulation.
        """
        if not self.vehicle: return
        
        # --- DATA SANITIZATION ---
        # If DroneKit returns None (dirty read), default to 0 to prevent crashes.
        # Prevents "struct.error: required argument is not an float/int"
        now_ms = int(time.time() * 1000)
        safe_time_week_ms = now_ms % 4294967295
        safe_lat = int(lat * 1e7) if lat is not None else 0
        safe_lon = int(lon * 1e7) if lon is not None else 0
        safe_alt = float(alt) if alt is not None else 0.0
        # ---------------------------

        # Attempt to build the message.
        # Note: Newer Pymavlink versions require a 'yaw' argument (19 args vs 18).
        try:
            msg = self.vehicle.message_factory.gps_input_encode(
                0, # time_usec
                0, # gps_id
                0, # ignore_flags
                safe_time_week_ms, # time_week_ms
                0, # time_week
                fix_type,
                safe_lat, 
                safe_lon, 
                safe_alt,
                1.0, 1.0, 0, 0, 0, # hdop, vdop, vn, ve, vd
                0.2, 0.2, 0.2,    # accuracy
                satellites        # satellites_visible
            )
            self.vehicle.send_mavlink(msg)
            
        except TypeError:
            # Fallback: If Pymavlink expects the extra 'yaw' argument.
            msg = self.vehicle.message_factory.gps_input_encode(
                0, 0, 0, int(time.time() * 1000), 0, fix_type,
                safe_lat, safe_lon, safe_alt,
                1.0, 1.0, 0, 0, 0, 0.2, 0.2, 0.2, 
                satellites, 
                0 # Extra argument: Yaw (centidegrees)
            )
            self.vehicle.send_mavlink(msg)

    def _hard_spoofing_sequence(self):
        """
        Simulates total GPS loss or override (Jamming).
        """
        self.attack_metrics["phase"] = "JAMMING (Hard Spoof)"
        loc = self.vehicle.location.global_frame
        # Send fix_type=0 to simulate loss of GPS
        self._send_mavlink_gps(loc.lat, loc.lon, loc.alt, fix_type=0, satellites=0)
        
    def start_attack(self, strategy, n_offset, e_offset, param):
        """
        Main entry point for attacks.
        param: Drift speed for Strategy A, or K-factor for Strategy B.
        """
        if self.running: return False, "Attack already active"
        
        # Reset metrics
        self.attack_metrics = {"active": True, "phase": "INIT", "distance_moved": 0.0, "spoofed_dist": 0.0}
        self.running = True
        
        if strategy == 'A':
            target = self._strategy_a_loop
        else:
            target = self._strategy_b_loop
            
        self.thread = threading.Thread(target=target, args=(n_offset, e_offset, param))
        self.thread.start()
        return True, f"Attack {strategy} Started"

    def stop_attack(self):
        """Stops the thread and cleans up simulator glitches."""
        self.running = False
        if self.thread: self.thread.join()
        self.attack_metrics["active"] = False
        
        # Clean up ArduPilot SIM parameters
        if self.vehicle:
            self.vehicle.parameters['SIM_GPS1_GLTCH_Y'] = 0
            self.vehicle.parameters['SIM_GPS1_GLTCH_X'] = 0
            
        self.attack_metrics["phase"] = "IDLE"
        return "Attack Stopped"

    def _meters_to_latlon(self, dn, de):
        """Converts North/East meters back to Latitude/Longitude delta."""
        rn = R_EARTH
        dlat = dn / rn * (180.0 / math.pi)
        dlon = de / rn * (180.0 / math.pi)
        return dlat, dlon
    def _latlon_to_meters(self, dlat, dlon):
        """Converts North/East meters back to Latitude/Longitude delta."""
        rn = R_EARTH
        dn = dlat * rn / (180.0 / math.pi)
        de = dlon * rn / (180.0 / math.pi)
        return math.sqrt((dn*dn) + (de*de))

    def _strategy_a_loop(self, target_n, target_e, iterations):
        """
        STRATEGY A: Position Hold Drift.
        1. Calculates a vector from current pos to target.
        2. Slowly increments SIM_GPS_GLTCH to trick the drone.
        """        
        # 1. Reset logic and simulate jamming
        self.attack_metrics["phase"] = "APLYING JAMMER"

        self.vehicle.parameters['SIM_GPS1_GLTCH_X'] = 0
        self.vehicle.parameters['SIM_GPS1_GLTCH_Y'] = 0
        self._hard_spoofing_sequence()
        self.vehicle.mode = VehicleMode("POSHOLD")
        
        self.attack_metrics["phase"] = "CALCULATING VECTOR"
        
        # 2. Obtain the degrees that should be moved
        target_lat, target_lon = self._meters_to_latlon(target_n, target_e)
        
        # 3. Calculate the Glitch Required
        # We divide by 300 steps for a smooth drift
        glitch_n = (target_lat * -1) / float(iterations)
        glitch_e = (target_lon * -1) / float(iterations)

        self.attack_metrics["phase"] = "HIJACKING (Strategy A)"
        print(f"Calculated Glitch Steps: N={glitch_n}, E={glitch_e}")

        # 4. Monitor Loop
        i = 0
        while self.running and i < iterations and self.vehicle.mode.name == 'POSHOLD':
            # 5. Inject the Glitch (This moves the perceived GPS position)
            # The drone thinks it is moving AWAY from target, so it flies TOWARDS it to compensate.
            self.vehicle.parameters['SIM_GPS1_GLTCH_X'] += glitch_n # Latitude glitch (North)
            self.vehicle.parameters['SIM_GPS1_GLTCH_Y'] += glitch_e # Longitude glitch (East)
            
            dist = self._latlon_to_meters(glitch_n*i, glitch_e*i)
            self.attack_metrics["distance_moved"] = round(dist, 2)
            
            i += 1
            if i % 50 == 0: print(f"Step {i}/{iterations}") # Log every 50 steps
            time.sleep(0.1) # Frequency of injection
            
        print("Exiting Strategy A Loop")
        
        # Cleanup: Remove glitch when stopped
        self.vehicle.parameters['SIM_GPS1_GLTCH_X'] = 0
        self.vehicle.parameters['SIM_GPS1_GLTCH_Y'] = 0

    def _strategy_b_loop(self, target_n, target_e, k_factor):
        """
        STRATEGY B: Waypoint Hijacking.
        Strict Implementation of Equation 3: a = P_waypoint + k * (P_target - P_init)
        
        1. Keeps GPS Type as Default (Internal SIM).
        2. Calculates offsets to re-orient the coordinate frame.
        3. Drone flies to 'waypoint' but physically arrives at 'target'.
        """
        original_loc = self.vehicle.location.global_frame
        
        # 1. Reset logic and simulate jamming
        self.attack_metrics["phase"] = "APLYING JAMMER"
        self._hard_spoofing_sequence()
        self.vehicle.parameters['SIM_GPS1_GLTCH_X'] = 0
        self.vehicle.parameters['SIM_GPS1_GLTCH_Y'] = 0
        # High EKF threshold to prevent "EKF Failsafe" from triggering during the jump
        self.vehicle.parameters['FS_EKF_THRESH'] = 1000000000000.0

        # Ensure we are using the internal simulator GPS
        self.vehicle.parameters['GPS1_TYPE'] = 1 
        
        self.attack_metrics["phase"] = "CALCULATING VECTOR"

        # 2. Get Waypoint Data (The drone must be on a mission for this to work)
        cmds = self.vehicle.commands
        cmds.download()
        cmds.wait_ready()
        
        # Safety Check: Ensure there are actual commands
        if not self.vehicle.commands.next or self.vehicle.commands.next > len(cmds):
            print("[ERROR] No active waypoint found. Cannot execute Strategy B.")
            self.running = False
            return

        target_cmd = cmds[self.vehicle.commands.next-1]

        # P_init: Current location
        p_init = self.vehicle.location.global_frame
        
        # P_waypoint: Where the drone WANTS to go
        p_way_lat = target_cmd.x 
        p_way_lon = target_cmd.y
        
        # 4. Apply Formula: a = P_waypoint + k * (P_target_vector - P_init)
        # Note: target_n and target_e here act as the Target Lat/Lon
        fake_a_n = p_way_lat + k_factor * (target_n - p_init.lat)
        fake_a_e = p_way_lon + k_factor * (target_e - p_init.lon)
        
        # 5. Calculate the Glitch Required
        # To make the drone think it is at 'fake_a' (while it is actually at p_init),
        # The GPS must report: GPS_POS = True_Pos + Glitch
        # We want GPS_POS = fake_a, so: Glitch = fake_a - True_Pos
        
        glitch_n = fake_a_n- p_init.lat 
        glitch_e = fake_a_e - p_init.lon 

        self.attack_metrics["phase"] = "HIJACKING (Strategy B)"
        print(f"[*] STRAT B: Injecting Static Glitch. N={glitch_n:.6f}, E={glitch_e:.6f}")
        
        # 6. Inject the Glitch (This moves the perceived GPS position instantaneously)
        self.vehicle.parameters['SIM_GPS1_GLTCH_X'] = glitch_n # Latitude glitch (North)
        self.vehicle.parameters['SIM_GPS1_GLTCH_Y'] = glitch_e # Longitude glitch (East)

        # 7. Monitor Loop
        while self.running:
            real_loc = self.vehicle.location.global_frame
            dist = get_distance_metres(original_loc, real_loc)
            self.attack_metrics["distance_moved"] = round(dist, 2)
            
            # Keep drone in AUTO so it tries to fly to the waypoint
            # (But because of the glitch, it will fly towards the spoofer target)
            if self.vehicle.mode.name != 'AUTO':
                print("[*] Forcing AUTO mode...")
                self.vehicle.mode = VehicleMode("AUTO")
            
            # print("Monitoring loop active...")
            time.sleep(1)

        # Cleanup: Remove glitch when stopped
        print("[*] Cleaning up Strategy B...")
        self.vehicle.parameters['SIM_GPS1_GLTCH_X'] = 0
        self.vehicle.parameters['SIM_GPS1_GLTCH_Y'] = 0
        self.vehicle.mode = VehicleMode("POSHOLD")