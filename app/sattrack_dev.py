import os
import ephem
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import geocoder
import numpy as np
import requests
import warnings
import gpsd
import geocoder

warnings.filterwarnings("ignore")

TLE_URL = "https://www.amsat.org/tle/current/nasabare.txt"
OBSERVER_GRID = "FN20"
OBSERVER_ALTITUDE = 0  # in meters


class SatelliteTracker:
    def __init__(self, satellite_name):
        self.satellite_name = satellite_name
        self.download_tle(TLE_URL, "tle.txt", days_old=7, force_download=True)
        self.tle = self.read_tle()
        self.observer_loc = self.get_observer_loc()
        self.grid_loc = self.get_grid_locator(self.observer_loc)
        self.sat_azimuth, self.sat_elevation = self.get_satellite_loc(self.tle, self.observer_loc)
        self.sat_active = self.check_satellite_active(self.tle, self.observer_loc)
        self.rise_time, self.rise_azimuth_deg, self.max_altitude_time, self.max_altitude_deg, self.set_time, self.set_azimuth_deg = self.predict_next_pass(self.tle, self.observer_loc)


    def get_observer_loc(self):
        # Try to get GPS location first (if available)
        try:
            gpsd.connect()
            packet = gpsd.get_current()
            if packet.mode >= 2:  # 2D or 3D fix
                return [packet.lat, packet.lon]
        except Exception:
            pass  # Fallback to IP if GPS not available

        # Fallback: get location from IP
        g = geocoder.ip('me')
        if g.ok:
            return g.latlng
        else:
            return None
    
    def get_grid_locator(self, observer_loc):
        lat, lon = observer_loc
        lat += 90
        lon += 180
        
        A = "ABCDEFGHIJKLMNOPQRSTUVWX"
        a = "abcdefghijklmnopqrstuvwx"

        locator = (
            A[int(lon // 20)] +
            A[int(lat // 10)] +
            str(int((lon % 20) // 2)) +
            str(int(lat % 10)) +
            a[int((lon % 2) * 12)] +
            a[int((lat % 1) * 24)]
        )

        return locator   
            
    def download_tle(self, url, filename="tle.txt", days_old=10, force_download=False):
        if os.path.exists(filename):
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(filename))
            if file_age < timedelta(days=days_old) and not force_download:
                print(f"TLE data in {filename} is up to date.")
                return
            else:
                print(f"TLE data in {filename} is older. Downloading new data.")
        else:
            print(f"TLE file {filename} not found. Downloading TLE data.")
            response = requests.get(url)
            if response.status_code == 200:
                with open(filename, 'w') as f:
                    f.write(response.text)
                    print(f"TLE data downloaded to {filename}")
            else:
                print(f"Failed to download TLE data. Status code: {response.status_code}")


    def read_tle(self, filename="tle.txt"):
        if not os.path.exists(filename):
            print(f"File {filename} does not exist.")
            return None

        with open(filename, 'r') as f:
            lines = f.readlines()

        for i in range(0, len(lines), 3):
            if lines[i].strip() == self.satellite_name:
                return lines[i:i+3]  # Return the three lines for the satellite

        print(f"Satellite '{self.satellite_name}' not found in TLE data.")
        return None


    def get_satellite_loc(self, tle_data, observer_loc, observer_alt=0, observer_time=None):
        observer_lat, observer_lon = observer_loc
        if not tle_data or len(tle_data) != 3:
            print("Invalid TLE data.")
            return None

        observer_time = observer_time or datetime.utcnow()
        satellite = ephem.readtle(tle_data[0].strip(), tle_data[1].strip(), tle_data[2].strip())

        observer = ephem.Observer()
        observer.lat = str(observer_lat)
        observer.lon = str(observer_lon)
        observer.elevation = observer_alt
        observer.date = observer_time

        satellite.compute(observer)

        azimuth = satellite.az / ephem.degree
        elevation = satellite.alt / ephem.degree

        return azimuth, elevation
    
    
    def check_satellite_active(self, tle_data, observer_loc, observer_alt=0):
        observer_lat, observer_lon = observer_loc
        azimuth, elevation = self.get_satellite_loc(tle_data, observer_loc, observer_alt)
        if elevation > 0:
            return True
        return False
    
    def predict_next_pass(self, tle_data, observer_loc, observer_alt=0):
        observer_lat, observer_lon = observer_loc
        if not tle_data or len(tle_data) != 3:
            print("Invalid TLE data.")
            return None

        satellite = ephem.readtle(tle_data[0].strip(), tle_data[1].strip(), tle_data[2].strip())
        observer = ephem.Observer()
        observer.lat = str(observer_lat)
        observer.lon = str(observer_lon)
        observer.elevation = observer_alt
        current_time = datetime.utcnow()
        observer.date = current_time

        info = observer.next_pass(satellite)
        rise_time = info[0]
        rise_azimuth = info[1]
        max_altitude_time = info[2]
        max_altitude = info[3]
        set_time = info[4]
        set_azimuth = info[5]

        
        # Convert to decimal degrees
        rise_azimuth_deg = rise_azimuth / ephem.degree
        set_azimuth_deg = set_azimuth / ephem.degree
        max_altitude_deg = max_altitude / ephem.degree

        return rise_time,rise_azimuth_deg, max_altitude_time, max_altitude_deg, set_time, set_azimuth_deg
    
    def show_pass(self):
        print(f"Satellite Name: {self.satellite_name}")
        print(f"Rise Time: {self.rise_time}   ")
        print(f"Max Altitude: {self.max_altitude_deg} degrees")
        print(f"Rise Azimuth: {self.rise_azimuth_deg} degrees")
        print(f"Set Time: {self.set_time}   ")
        print(f"Set Azimuth: {self.set_azimuth_deg} degrees")
        print(f"Satellite Active: {self.sat_active}")
        print(f"Satellite Azimuth: {self.sat_azimuth} degrees")
        print(f"Satellite Elevation: {self.sat_elevation} degrees")
        print(f"Observer Location: {self.observer_loc}")
        print(f"Grid Locator: {self.grid_loc}")
        print(f"Satellite Name: {self.satellite_name}")

    def plot_pass(self):
        print(f"Plotting pass for {self.satellite_name}...")
        # Plot the satellite pass in polar coordinates (azimuth, elevation)
        fig = plt.figure(figsize=(8, 6))
        ax = fig.add_subplot(111, polar=True)

        # Convert degrees to radians for azimuth
        rise_az_rad = np.deg2rad(self.rise_azimuth_deg)
        set_az_rad = np.deg2rad(self.set_azimuth_deg)

        # Elevation for horizon is 0, max altitude is self.max_altitude_deg
        # For polar plot: azimuth is theta, elevation is radius (invert so 90 is center)
        def polarr(elev):
            return 90 - elev  # 0 at center, 90 at edge

        # Plot rise, max, set points
        ax.plot(rise_az_rad, polarr(0), 'go', label='Rise')
        ax.text(rise_az_rad, polarr(0), 'AOS', color='green', fontsize=10, ha='left', va='bottom')
        ax.plot(set_az_rad, polarr(0), 'ro', label='Set')
        # Max altitude: use midpoint azimuth for demonstration
        max_az_rad = np.deg2rad((self.rise_azimuth_deg + self.set_azimuth_deg) / 2)
        ax.plot(max_az_rad, polarr(self.max_altitude_deg), 'ks', label='Max Altitude')

        # Draw trajectory: from rise to max to set
        azs = np.array([self.rise_azimuth_deg, (self.rise_azimuth_deg + self.set_azimuth_deg) / 2, self.set_azimuth_deg])
        elevs = np.array([0, self.max_altitude_deg, 0])
        ax.plot(np.deg2rad(azs), polarr(elevs), 'b-', label='Pass trajectory')

        # Set up polar plot
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_rlim(0, 90)
        ax.set_yticks([0, 30, 60, 90])
        ax.set_yticklabels(['90°', '60°', '30°', '0°'])  # 0° at edge, 90° at center
        ax.set_title(f'Satellite Pass for {self.satellite_name}', va='bottom')
        # Place legend outside the polar plot
        #ax.legend(loc='center left', bbox_to_anchor=(1.1, 0.5))
        plt.show()


             
if __name__ == "__main__":
    tracker = SatelliteTracker("FO-29")
    tracker.show_pass()
    tracker.plot_pass()
