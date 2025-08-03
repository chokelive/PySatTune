from skyfield.api import load, EarthSatellite, wgs84
from datetime import datetime, timedelta, timezone
import math

class SatelliteTracker:
    def __init__(self, tle_name, tle_line1, tle_line2):
        self.name = tle_name
        self.ts = load.timescale()
        self.satellite = EarthSatellite(tle_line1, tle_line2, tle_name, self.ts)
        #self.observer = wgs84.latlon()  # Example: Bangkok, Thailand
        self.observer = wgs84.latlon(13.808596988865355, 99.78500659188863)
        #13.808596988865355, 99.78500659188863

    def get_tracking_info(self):
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        t = self.ts.utc(now)

        # Current satellite position
        geocentric = self.satellite.at(t)
        subpoint = geocentric.subpoint()
        sat_lat = subpoint.latitude.degrees
        sat_lon = subpoint.longitude.degrees
        sat_height_km = subpoint.elevation.km

        difference = self.satellite - self.observer
        topocentric = difference.at(t)
        el, az, distance = topocentric.altaz()

        # Compute next AOS and LOS
        t0 = self.ts.utc(now)
        t1 = self.ts.utc(now + timedelta(hours=12))
        times, events = self.satellite.find_events(self.observer, t0, t1, altitude_degrees=1.0)

        aos_time = los_time = None
        aos_az = los_az = None
        max_el_value = 0.0

        for ti, event in zip(times, events):
            if event == 0 and aos_time is None:
                aos_time = ti
                _, aos_az, _ = difference.at(ti).altaz()
            if event == 2 and los_time is None:
                los_time = ti
                _, los_az, _ = difference.at(ti).altaz()
                break  # We only consider the first AOS-LOS pair

        # Sample max elevation between AOS and LOS
        if aos_time is not None and los_time is not None:
            start_dt = aos_time.utc_datetime()
            end_dt = los_time.utc_datetime()
            duration_seconds = (end_dt - start_dt).total_seconds()
            steps = int(duration_seconds // 10)

            for i in range(steps + 1):
                ti = self.ts.utc(start_dt + timedelta(seconds=i * 10))
                alt, _, _ = difference.at(ti).altaz()
                if alt.degrees > max_el_value:
                    max_el_value = alt.degrees

        info = {
            "sat_pos": f"{az.degrees:.1f}° / {el.degrees:.1f}°",
            "ant_pos": f"{az.degrees:.1f}° / {el.degrees:.1f}°" if el.degrees > 0 else "N/A",
            "range": f"{distance.km:.2f} km / {distance.km * 0.621371:.2f} mi",
            "aos": f"{aos_time.utc_datetime().strftime('%I:%M:%S %p')} @ {aos_az.degrees:.1f}°" if aos_time is not None else "---",
            "los": f"{los_time.utc_datetime().strftime('%I:%M:%S %p')} @ {los_az.degrees:.1f}°" if los_time is not None else "---",
            "max_el": f"{max_el_value:.1f}°" if max_el_value > 0 else f"{el.degrees:.1f}°",
            "utc_time": now.strftime("%H:%M:%S"),
            "last_msg": "--:--"
        }

        return info


if __name__ == "__main__":
    # Example TLE for ISS
    tle_name = "ISS (ZARYA)"
    tle_line1 = "1 25544U 98067A   25214.49566479  .00011663  00000-0  20985-3 0  9998"
    tle_line2 = "2 25544  51.6359  77.5427 0002034 138.8478 290.2759 15.50294044522345"

    tracker = SatelliteTracker(tle_name, tle_line1, tle_line2)
    tracking_info = tracker.get_tracking_info()
    print(tracking_info)
