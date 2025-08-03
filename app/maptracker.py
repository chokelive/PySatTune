import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from skyfield.api import load, EarthSatellite, utc
from datetime import datetime, timedelta
import threading
import time
import matplotlib.image as mpimg
import io
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas



class SatelliteTrackPlotter:
    def __init__(self, tle_lines, output_file="satellite_track.png"):
        self.tle_lines = tle_lines
        self.name = tle_lines[0]
        self.output_file = output_file
        self.ts = load.timescale()
        self.satellite = EarthSatellite(tle_lines[1], tle_lines[2], tle_lines[0], ts=self.ts)


    # Fix for long line across dateline
    def split_track_on_wraparound(self, lons, lats):
        segments = []
        segment = [(lons[0], lats[0])]
        for lon, lat in zip(lons[1:], lats[1:]):
            if abs(lon - segment[-1][0]) > 180:
                segments.append(segment)
                segment = [(lon, lat)]
            else:
                segment.append((lon, lat))
        segments.append(segment)
        return segments
    

    def compute_footprint_radius(self, altitude_km):
        earth_radius_km = 6371
        return np.sqrt((earth_radius_km + altitude_km)**2 - earth_radius_km**2)

    def draw_footprint(self, m, center_lat, center_lon, radius_km=2200):
        """
        Draws only the footprint outline (no background fill).
        """
        angles = np.linspace(0, 360, 100)
        lats = []
        lons = []

        for angle in angles:
            angle_rad = np.deg2rad(angle)
            dlat = (radius_km / 111) * np.cos(angle_rad)
            dlon = (radius_km / (111 * np.cos(np.radians(center_lat)))) * np.sin(angle_rad)
            lats.append(center_lat + dlat)
            lons.append(center_lon + dlon)

        x, y = m(lons, lats)

        # Only draw border — no fill
        plt.plot(x, y, linestyle='--', color='yellow', linewidth=1.5, alpha=0.9)


    def plot_background_image(self, m, ax, image_path):
        img = mpimg.imread(image_path)
        # map corners (in lon/lat)
        llcrnrlon, llcrnrlat = -180, -90
        urcrnrlon, urcrnrlat = 180, 90

        # Convert corners to map projection
        x0, y0 = m(llcrnrlon, llcrnrlat)
        x1, y1 = m(urcrnrlon, urcrnrlat)

        ax.imshow(img, extent=[x0, x1, y0, y1], aspect='auto', zorder=0)
        



    def plot_track(self, duration_minutes=90, interval_seconds=60):
        # Generate time range
        #times = self.ts.utc(datetime.utcnow() + timedelta(seconds=i) for i in range(0, duration_minutes * 60, interval_seconds))
        times = [self.ts.utc((datetime.now(utc) + timedelta(seconds=i))) for i in range(0, duration_minutes * 60, interval_seconds)]
        subpoints = [self.satellite.at(t).subpoint() for t in times]

        lats = [sp.latitude.degrees for sp in subpoints]
        lons = [sp.longitude.degrees for sp in subpoints]

        # Set up map
        fig = plt.figure(figsize=(12.64, 6.32), dpi=100)
        #ax = plt.gca()
        ax = fig.add_axes([0, 0, 1, 1])  # <- key line: use full canvas

        m = Basemap(projection='mill', lat_0=0, lon_0=0, resolution='c', ax=ax)
        self.plot_background_image(m, ax, './app/map/world_map5.jpg')


        # Plot satellite track
        segments = self.split_track_on_wraparound(lons, lats)
        for seg in segments:
            lon_seg, lat_seg = zip(*seg)
            x, y = m(lon_seg, lat_seg)
            m.plot(x, y, color='cyan', linewidth=2)

        # Mark current satellite position
        now_pos = self.satellite.at(self.ts.utc(datetime.now(utc))).subpoint()
        now_lat, now_lon = now_pos.latitude.degrees, now_pos.longitude.degrees
        x_now, y_now = m(now_lon, now_lat)

        # Draw footprint (approximate)
        #self.draw_footprint(m, now_lat, now_lon, radius_km=2200)
        altitude_km = now_pos.elevation.km
        radius_km = self.compute_footprint_radius(altitude_km)
        self.draw_footprint(m, now_lat, now_lon, radius_km=radius_km)

        m.plot(x_now, y_now, 'yo', markersize=8)  # yellow dot

        plt.text(x_now + 150000, y_now + 150000, self.name, 
            color='yellow', fontsize=10, fontweight='bold')


        #plt.title("Satellite Ground Track")
        #plt.savefig(self.output_file, dpi=100, bbox_inches='tight', pad_inches=0)

        #plt.close()
        print(f"Satellite track image saved to {self.output_file}")

        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight', pad_inches=0)
        plt.close(fig)

        buf.seek(0)
        return buf

    def start_auto_refresh(self, interval_seconds=60):
        def update_loop():
            while True:
                self.plot_track()
                time.sleep(interval_seconds)

        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()


if __name__ == "__main__":


    tle = [
        "ISS",
        "1 25544U 98067A   25214.49566479  .00011663  00000-0  20985-3 0  9998",
        "2 25544  51.6359  77.5427 0002034 138.8478 290.2759 15.50294044522345"
    ]

    #tracker = SatelliteTrackPlotter(tle)
    #tracker.plot_track(duration_minutes=270, interval_seconds=60)

    tracker = SatelliteTrackPlotter(tle)
    tracker.plot_track(duration_minutes=180, interval_seconds=60)
    #tracker.start_auto_refresh(interval_seconds=60)  # updates every 60 seconds
