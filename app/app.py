import numpy as np
from numpy import long
from rigcontrol import RigCtlClient
from dopplercal import DopplerCalculator
from maptracker import SatelliteTrackPlotter
from sattrack import SatelliteTracker
import ephem
import time
import threading

from flask import Flask, jsonify, request, send_file, render_template


app = Flask(__name__, template_folder='templates')

GRID_LOCATOR = "NK93"
ALTITUDE = 11  # in meters
SQF_DATA = "ISS,437800,145990,FM,FM,NOR,0,0,FM tone 67.0Hz 9k6 GFSK"
#SQF_DATA = "RS-44,435640,145965,USB,LSB,REV,0,0,SSB"
#SQF_DATA = "FO-29,435850,145950,USB,LSB,REV,0,0,SSB"
#SQF_DATA = "MO-122,435825,145925,USB,LSB,REV,0,0,SSB"


# Global state for rig control
# This will be updated by the doppler_loop thread
RIG_CONTROL = {
    "tx_tune_freq": 0,
    "rx_tune_freq": 0,
    "doppler_rx": 0,
    "doppler_tx": 0,
    "rx_actual_freq": 0,
    "tx_actual_freq": 0,
    "running": True
}

# Satellite information for the UI
# This can be dynamically updated based on the SQF data or other sources
SAT_INFO = {
    "name": None,
    "uplink_freq": 0,  # in kHz
    "downlink_freq": 0,  # in kHz
    "mode": None,
    "sqf_data": SQF_DATA,
    "TLE_DATA": None
}

thread_rig = None
rig = RigCtlClient()


@app.route('/api/version')
def get_data():
    data = {
        'name': 'PySatTune',
        'version': 1.0
    }
    return jsonify(data)

@app.route('/api/rig')
def get_rig_data():
    data = {
        'RIG_CONTROL': {
            k: int(v) if isinstance(v, (int, np.integer)) else v
            for k, v in RIG_CONTROL.items()
        }
    }
    return jsonify(data)


@app.route('/api/resetrig')
def get_resetrig():
    global thread_rig

    print("Resetting Rig Control...")

    if thread_rig is not None and thread_rig.is_alive():
        RIG_CONTROL["running"] = False
        thread_rig.join()

    RIG_CONTROL["running"] = True
    thread_rig = threading.Thread(target=doppler_loop, daemon=True)
    thread_rig.start()

    return jsonify({"status": "Rig reset command completed."})


@app.route('/api/setmodeRX', methods=['GET'])
def set_mode_rx():
    mode = request.args.get("mode")    
    rig.set_mode(mode=mode)
    return jsonify({"status": f"Setting RX mode to: {mode}"})

@app.route('/api/setmodeTX', methods=['GET'])
def set_mode_tx():
    mode = request.args.get("mode")    
    rig.set_split_mode(mode=mode)
    return jsonify({"status": f"Setting TX mode to: {mode}"})


@app.route("/api/track")
def track():
    tle = SAT_INFO["TLE_DATA"]
    tracker = SatelliteTracker(tle[0], tle[1], tle[2])
    info = tracker.get_tracking_info()
    return jsonify(info)


@app.route('/satmap')
def get_satellite_map():
    # tle = [
    #     "1 25544U 98067A   25214.49566479  .00011663  00000-0  20985-3 0  9998",
    #     "2 25544  51.6359  77.5427 0002034 138.8478 290.2759 15.50294044522345"
    # ]
    tle = SAT_INFO["TLE_DATA"]
    if not tle or len(tle) < 3:
        return jsonify({"error": "TLE data not available"}), 400
    tracker = SatelliteTrackPlotter(tle)
    image_stream = tracker.plot_track(duration_minutes=180, interval_seconds=60)
    return send_file(image_stream, mimetype='image/png')


@app.route('/')
def rig_page():
    return render_template('main.html') 


###############################################
# Doppler calculation loop
###############################################
def doppler_loop():
    doppler_calculator = DopplerCalculator()

    sqf = doppler_calculator.read_sqf_data(sqf_data=SQF_DATA)
    satellite_name = sqf["satellite"]
    tx_org_freq = sqf["uplink_freq"] * 1000  # Convert to Hz
    rx_org_freq = sqf["downlink_freq"] * 1000  # Convert to Hz

    tle_data = doppler_calculator.read_tle(satellite_name=satellite_name)
    lat, lon = doppler_calculator.grid_to_latlon(GRID_LOCATOR)

    print(tle_data)

    myloc = ephem.Observer()
    myloc.lon = str(lon)
    myloc.lat = str(lat)
    myloc.elevation = ALTITUDE

    mysat = ephem.readtle(tle_data[0].strip(), tle_data[1].strip(), tle_data[2].strip())

    try:

        # Initial Values
        rx_doppler = 0
        tx_doppler = 0
        rig.set_freq(rx_org_freq)
        rig.set_split()
        rx_tune = long(rig.get_freq())
        rx_actual_freq = rx_tune
        rx_tune_predict = rx_tune

        while RIG_CONTROL["running"]:


            # Update frequencies if radio change.
            if rx_actual_freq != long(rig.get_freq()):
                rx_tune = long(rig.get_freq()) + rx_doppler
            else:
                rx_tune = rx_tune_predict

            rx_doppler = doppler_calculator.dopplercalc(myloc, mysat, F0=rx_org_freq)
            rx_diff_freq = (rx_tune - rx_doppler) - (rx_org_freq - rx_doppler)
            rx_tune_predict = rx_org_freq + rx_diff_freq
            rx_actual_freq = rx_tune_predict - rx_doppler

            rig.set_freq(rx_actual_freq)

            tx_doppler = doppler_calculator.dopplercalc(myloc, mysat, F0=tx_org_freq)
            tx_tune_predict = tx_org_freq - rx_diff_freq
            tx_actual_freq = tx_tune_predict - tx_doppler

            rig.set_split_freq(tx_actual_freq)

            print(f"[RX] Tune: {rx_tune_predict}, Doppler: {rx_doppler}, Actual: {rx_actual_freq}")
            print(f"[TX] Tune: {tx_tune_predict}, Doppler: {tx_doppler}, Actual: {tx_actual_freq}")

            # Update global state
            RIG_CONTROL["rx_actual_freq"] = rx_actual_freq
            RIG_CONTROL["tx_actual_freq"] = tx_actual_freq
            RIG_CONTROL["rx_tune_freq"] = rx_tune_predict
            RIG_CONTROL["tx_tune_freq"] = tx_tune_predict
            RIG_CONTROL["doppler_rx"] = rx_doppler
            RIG_CONTROL["doppler_tx"] = tx_doppler
            SAT_INFO["name"] = satellite_name
            SAT_INFO["uplink_freq"] = tx_org_freq // 1000  # Convert to kHz
            SAT_INFO["downlink_freq"] = rx_org_freq // 1000  # Convert to kHz

            
            SAT_INFO["TLE_DATA"] = tle_data

            time.sleep(1)
    except KeyboardInterrupt:
        rig.reset_split()
        print("\nExiting Doppler calculation loop.")


if __name__ == "__main__":
    # Start doppler loop in background
    #global thread_rig 
    thread_rig = threading.Thread(target=doppler_loop, daemon=True)
    thread_rig.start()

    # Start Flask server
    app.run(debug=True, use_reloader=False)  # use_reloader=False avoids double-threading issue on reload
