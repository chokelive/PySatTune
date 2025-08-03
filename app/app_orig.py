from numpy import long
from rigcontrol import RigCtlClient
from dopplercal import DopplerCalculator
import ephem
import time

from flask import Flask, jsonify
app = Flask(__name__)


GRID_LOCATOR = "NK93"
ALTITUDE = 11  # in meters
SQF_DATA = "ISS,437800,145990,FM,FM,NOR,0,0,FM tone 67.0Hz 9k6 GFSK"
#SQF_DATA = "RS-44,435640,145964,USB,LSB,REV,0,0,SSB"



@app.route('/api/data')
def get_data():
    data = {
        'name': 'ChatGPT',
        'version': 4,
        'status': 'active'
    }
    return jsonify(data)



if __name__ == "__main__":
    app.run(debug=True)
    
    # Initialize RigControl and DopplerCalculator
    rig = RigCtlClient()

    # Example usage
    doppler_calculator = DopplerCalculator()

    sqf = doppler_calculator.read_sqf_data(sqf_data=SQF_DATA) 
    satellite_name = sqf["satellite"]
    tx_org_freq = sqf["uplink_freq"]
    tx_mode = sqf["uplink_mode"]
    rx_org_freq = sqf["downlink_freq"]
    print(f"Satellite: {satellite_name}, TX Frequency: {tx_org_freq} Hz, RX Frequency: {rx_org_freq} Hz")
    
    tle_data = doppler_calculator.read_tle(satellite_name=satellite_name)

    lat, lon = doppler_calculator.grid_to_latlon(GRID_LOCATOR)
    print(f"Grid Locator {GRID_LOCATOR} corresponds to Lat/Lon: {lat}, {lon}")

    myloc = ephem.Observer()
    myloc.lon = str(lon)
    myloc.lat = str(lat)
    myloc.elevation = ALTITUDE

    print(f"Observer Location: {myloc.lat}, {myloc.lon}, Altitude: {myloc.elevation} m")

    print(tle_data[0].strip())
    print(tle_data[1].strip())
    print(tle_data[2].strip())

    mysat = ephem.readtle(tle_data[0].strip(), tle_data[1].strip(), tle_data[2].strip())

    try:
        rx_doppler = 0
        tx_doppler = 0
        rx_org_freq = rx_org_freq*1000  # Convert to Hz
        tx_org_freq = tx_org_freq * 1000  # Convert to Hz

        # set frequency and mode on the rig
        rig.set_freq(rx_org_freq)
        rig.set_split()
        rx_tune =  long(rig.get_freq())  # Initialize RX tune frequency
        rx_actual_freq = rx_tune # initial RX actual frequency
        rx_tune_predict = rx_tune # initial RX tune prediction

        while True:

            # Update RX frequency if rig tune new frequency.
            if rx_actual_freq != long(rig.get_freq()):
                rx_tune = long(rig.get_freq()) + rx_doppler
            else:
                rx_tune = rx_tune_predict
            
            
            # RX Doppler calculation loop
            rx_doppler = doppler_calculator.dopplercalc(myloc, mysat, F0=rx_org_freq)
            rx_diff_freq =  (rx_tune - rx_doppler) - (rx_org_freq - rx_doppler)
            rx_tune_predict = rx_org_freq + rx_diff_freq
            rx_actual_freq = rx_tune_predict - rx_doppler
            print(f"RX Tune Frequency: {rx_tune_predict} Hz, RX Doppler Shift: {rx_doppler} Hz, RX Actual Frequency: {rx_actual_freq} Hz")

            rig.set_freq(rx_actual_freq)

            # TX Doppler calculation loop
            #tx_tune = 145800000
            tx_doppler = doppler_calculator.dopplercalc(myloc, mysat, F0=tx_org_freq)
            tx_tune_predict = tx_org_freq - rx_diff_freq # Invert the RX diff frequency for TX
            tx_actual_freq = tx_tune_predict - tx_doppler
            print(f"TX Tune Frequency: {tx_tune_predict} Hz, TX Doppler Shift: {tx_doppler} Hz, TX Actual Frequency: {tx_actual_freq} Hz")

            rig.set_split_freq(tx_actual_freq)

            time.sleep(1)
    except KeyboardInterrupt:
        rig.reset_split()
        print("\nExiting Doppler calculation loop.")