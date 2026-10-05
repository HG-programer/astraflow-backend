from datetime import datetime
from typing import List, Dict, Any


class TrafficAnalytics:
    """
    Analytics Aggregator for AstraFlow Dashboard and Reporting.
    Formats real-time CV engine statistics to match the exact Angular TypeScript models.
    """

    def __init__(self):
        # Initial simulated camera zones representing AstraFlow monitoring stations
        self.zones = [
            {
                "id": "CAM-01",
                "name": "Central Junction",
                "status": "normal",
                "cameras": 2,
                "vehicles": 72,
                "speed": 46,
                "x": 26,
                "y": 30
            },
            {
                "id": "CAM-02",
                "name": "North Avenue",
                "status": "normal",
                "cameras": 1,
                "vehicles": 48,
                "speed": 51,
                "x": 69,
                "y": 28
            },
            {
                "id": "CAM-03",
                "name": "East Corridor",
                "status": "congested",
                "cameras": 2,
                "vehicles": 83,
                "speed": 31,
                "x": 43,
                "y": 67
            },
            {
                "id": "CAM-04",
                "name": "South Junction",
                "status": "normal",
                "cameras": 1,
                "vehicles": 45,
                "speed": 38,
                "x": 76,
                "y": 70
            }
        ]

        self.recent_events = [
            {
                "type": "Vehicle detected",
                "location": "CAM-03 · Car",
                "time": datetime.now().strftime("%I:%M %p"),
                "severity": "normal",
                "icon": "vehicle"
            },
            {
                "type": "Speed threshold exceeded",
                "location": "CAM-01 · Car",
                "time": datetime.now().strftime("%I:%M %p"),
                "severity": "critical",
                "icon": "speed"
            },
            {
                "type": "Camera connection active",
                "location": "CAM-02 · North Avenue",
                "time": datetime.now().strftime("%I:%M %p"),
                "severity": "normal",
                "icon": "camera"
            }
        ]

    def record_event(self, event_type: str, location: str, severity: str = "normal", icon: str = "vehicle"):
        """Record an alert or activity event."""
        event_obj = {
            "type": event_type,
            "location": location,
            "time": datetime.now().strftime("%I:%M %p"),
            "severity": severity,
            "icon": icon
        }
        self.recent_events.insert(0, event_obj)
        if len(self.recent_events) > 20:
            self.recent_events.pop()

    def update_zone_vehicle_count(self, zone_id: str, count: int, avg_speed: float = None):
        """Update live camera zone metrics from CV engine."""
        for zone in self.zones:
            if zone["id"] == zone_id:
                zone["vehicles"] = count
                if avg_speed is not None:
                    zone["speed"] = round(avg_speed, 1)

                # Determine congestion status
                if count > 75:
                    zone["status"] = "congested"
                elif count > 50:
                    zone["status"] = "moderate"
                else:
                    zone["status"] = "normal"
                break

    def get_dashboard_metrics(self, live_total_vehicles: int = None, live_alerts_count: int = None) -> List[Dict[str, Any]]:
        """Return KPI metrics matching AstraFlow DashboardMetric model."""
        total_vehicles = live_total_vehicles if live_total_vehicles is not None else sum(z["vehicles"] for z in self.zones)
        avg_speed = round(sum(z["speed"] for z in self.zones) / len(self.zones))
        alerts_count = live_alerts_count if live_alerts_count is not None else 12

        return [
            {
                "label": "Total Vehicles",
                "value": str(total_vehicles),
                "comparison": "+12%",
                "trend": "up",
                "icon": "vehicles",
                "accent": "blue",
                "description": "Detected across monitored zones"
            },
            {
                "label": "Average Speed",
                "value": str(avg_speed),
                "unit": "km/h",
                "comparison": "+8%",
                "trend": "up",
                "icon": "speed",
                "accent": "violet",
                "description": "Across active road segments"
            },
            {
                "label": "Active Alerts",
                "value": str(alerts_count),
                "comparison": "+3%",
                "trend": "up",
                "icon": "alerts",
                "accent": "red",
                "description": "Require attention"
            },
            {
                "label": "Traffic Zones",
                "value": f"{len(self.zones):02d}",
                "comparison": "Normal",
                "trend": "neutral",
                "icon": "zones",
                "accent": "cyan",
                "description": "All monitored zones"
            }
        ]

    def get_zones(self) -> List[Dict[str, Any]]:
        """Return list of traffic zones."""
        return self.zones

    def get_zone_performance(self) -> List[Dict[str, Any]]:
        """Return ZonePerformance model for Analytics page."""
        return [
            {
                "id": z["id"],
                "name": z["name"],
                "vehicles": z["vehicles"],
                "speed": z["speed"],
                "status": z["status"],
                "statusLabel": z["status"].capitalize()
            }
            for z in self.zones
        ]

    def get_recent_events(self) -> List[Dict[str, Any]]:
        """Return recent traffic events."""
        return self.recent_events
