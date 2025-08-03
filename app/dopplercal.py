import os
from time import gmtime, strftime
import ephem
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import geocoder
import numpy as np
import requests
import warnings
import gpsd
import geocoder
import time

warnings.filterwarnings("ignore")

GRID_LOCATOR = "NK93"
ALTITUDE = 11  # in meters
SQF_DATA = "ISS,437800,145990,FM,FM,NOR,0,0,FM tone 67.0Hz 9k6 GFSK"

class DopplerCalculator:
    def __init__(self):
        pass

    def read_tle(self, filename="tle.txt", satellite_name=None):
        """Read TLE data for a given satellite from a file."""
        try:
            with open(filename, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"File {filename} does not exist.")
            return None

        for i in range(0, len(lines) - 2, 3):
            if lines[i].strip() == satellite_name:
                return lines[i:i+3]
        print(f"Satellite '{satellite_name}' not found in TLE data.")
        return None
    
    def read_sqf_data(self, sqf_data=SQF_DATA):
        """Parse SQF data string and return its components as a dictionary."""
        fields = sqf_data.split(",")
        if len(fields) < 8:
            print("Invalid SQF data format.")
            return None
        return {
            "satellite": fields[0],
            "downlink_freq": int(fields[1]),
            "uplink_freq": int(fields[2]),
            "downlink_mode": fields[3],
            "uplink_mode": fields[4],
            "norad_id": fields[5],
            "uplink_offset": int(fields[6]),
            "downlink_offset": int(fields[7]),
            "notes": ",".join(fields[8:]) if len(fields) > 8 else ""
        }
    
    def grid_to_latlon(self, grid):
        if not isinstance(grid, str) or len(grid) < 4:
            raise ValueError("Grid locator must be at least 4 characters long.")

        grid = grid.strip().upper()
        lon = (ord(grid[0]) - ord('A')) * 20 - 180
        lat = (ord(grid[1]) - ord('A')) * 10 - 90
        lon += int(grid[2]) * 2
        lat += int(grid[3]) * 1

        if len(grid) >= 6:
            lon += (ord(grid[4]) - ord('A')) * 5 / 60
            lat += (ord(grid[5]) - ord('A')) * 2.5 / 60
            lon += 2.5 / 60
            lat += 1.25 / 60
        else:
            lon += 1
            lat += 0.5

        return (lat, lon)
    
    def dopplercalc(self, myloc, mysat, F0=145800000):
        myloc.date = strftime('%Y/%m/%d %H:%M:%S', gmtime())
        mysat.compute(myloc)
        doppler = int(mysat.range_velocity * F0 / 299792458.0)  # Doppler shift calculation
        return doppler
    

if __name__ == "__main__":
    # Example usage
    doppler_calculator = DopplerCalculator()

    sqf = doppler_calculator.read_sqf_data() 
    satellite_name = sqf["satellite"]
    tx_org_freq = sqf["uplink_freq"]
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
        while True:
            # RX Doppler calculation loop
            rx_tune = 437900000
            rx_doppler = doppler_calculator.dopplercalc(myloc, mysat, F0=rx_org_freq)
            rx_diff_freq =  (rx_tune - rx_doppler) - (rx_org_freq - rx_doppler)
            rx_tune_predict = rx_org_freq + rx_diff_freq
            rx_actual_freq = rx_tune_predict - rx_doppler
            print(f"RX Tune Frequency: {rx_tune_predict} Hz, RX Doppler Shift: {rx_doppler} Hz, RX Actual Frequency: {rx_actual_freq} Hz")

            # TX Doppler calculation loop
            #tx_tune = 145800000
            tx_doppler = doppler_calculator.dopplercalc(myloc, mysat, F0=tx_org_freq)
            tx_tune_predict = tx_org_freq - rx_diff_freq # Invert the RX diff frequency for TX
            tx_actual_freq = tx_tune_predict - tx_doppler
            print(f"TX Tune Frequency: {tx_tune_predict} Hz, TX Doppler Shift: {tx_doppler} Hz, TX Actual Frequency: {tx_actual_freq} Hz")

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting Doppler calculation loop.")

   

    
    
    