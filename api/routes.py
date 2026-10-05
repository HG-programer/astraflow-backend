from flask import Blueprint, request, jsonify, Response
import base64
import cv2
import numpy as np
from datetime import datetime
import os
import time

from ..engine.detector import TrafficDetector
from ..engine.traffic_tracker import TrafficTracker
from ..engine.analytics import TrafficAnalytics

api_bp = Blueprint("api", __name__)

# Initialize AI and Analytics singletons
detector = TrafficDetector()
tracker = TrafficTracker(speed_limit_kmh=50.0)
analytics = TrafficAnalytics()

def generate_video_frames():
    """Generator function that continuously yields processed video frames."""
    # Use the test video we just created
    video_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "2165-155327596.mp4"))
    
    if not os.path.exists(video_path):
        # Fallback to empty grey frame if video not found
        while True:
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)
            frame[:] = (100, 100, 100)
            cv2.putText(frame, "Video Not Found", (400, 360), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(1)
            
    cap = cv2.VideoCapture(video_path)
    while True:
        ret, frame = cap.read()
        if not ret:
            # Loop video
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        result = tracker.process_frame(frame, conf_thresh=0.25)
        annotated = result["annotated_frame"]
        
        # Update analytics for dashboard
        analytics.update_zone_vehicle_count("CAM-01", result["active_count"])
        for vio in result["new_violations"]:
            analytics.record_event(
                event_type=vio["type"],
                location=f"CAM-01 · {vio['vehicleType']}",
                severity=vio["severity"],
                icon="speed" if "Speed" in vio["type"] else "wrong-way"
            )
            
        _, buffer = cv2.imencode('.jpg', annotated)
        frame_bytes = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@api_bp.route("/video_feed", methods=["GET"])
def video_feed():
    """Live MJPEG video streaming endpoint."""
    return Response(generate_video_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "service": "AstraFlow AI & Backend Engine",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })


# =========================================================
# AI COMPUTER VISION INFERENCE ENDPOINTS
# =========================================================

@api_bp.route("/detect/image", methods=["POST"])
def detect_image():
    """
    Inference endpoint for static image analysis.
    Accepts multipart file 'image' or 'imageFile', or JSON with 'image_base64'.
    Returns structured vehicle detections and base64 visualization.
    """
    image_bytes = None

    if "imageFile" in request.files:
        image_bytes = request.files["imageFile"].read()
    elif "image" in request.files:
        image_bytes = request.files["image"].read()
    elif request.is_json and "image_base64" in request.json:
        raw_b64 = request.json["image_base64"]
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",")[1]
        image_bytes = base64.b64decode(raw_b64)

    if not image_bytes:
        return jsonify({"error": "No valid image provided. Send multipart 'imageFile' or JSON 'image_base64'"}), 400

    try:
        conf_thresh = float(request.args.get("conf", 0.25))
        result = detector.detect_image(image_bytes, conf_thresh=conf_thresh)

        # Record activity event in analytics
        if result["total_vehicles"] > 0:
            top_type = result["vehicle_mix"][0]["label"] if result["vehicle_mix"] else "Vehicle"
            analytics.record_event(
                event_type=f"{result['total_vehicles']} Vehicles Detected",
                location="CAM-01 · Processed Feed",
                severity="normal",
                icon="vehicle"
            )

        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Detection failed: {str(e)}"}), 500


@api_bp.route("/track/frame", methods=["POST"])
def track_frame():
    """
    Frame-by-frame Multi-Object Tracking endpoint.
    Maintains persistent vehicle IDs, speeds, and triggers violations.
    """
    if "frame" not in request.files:
        return jsonify({"error": "No 'frame' file found in request"}), 400

    file_bytes = request.files["frame"].read()
    nparr = np.frombuffer(file_bytes, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    camera_id = request.args.get("camera_id", "CAM-01")
    camera_name = request.args.get("camera_name", "Central Junction")
    conf_thresh = float(request.args.get("conf", 0.25))

    try:
        tracking_result = tracker.process_frame(
            frame=frame,
            camera_id=camera_id,
            camera_name=camera_name,
            conf_thresh=conf_thresh
        )

        # Update zone analytics
        analytics.update_zone_vehicle_count(
            zone_id=camera_id,
            count=tracking_result["active_count"]
        )

        # Record any new violations
        for vio in tracking_result["new_violations"]:
            analytics.record_event(
                event_type=vio["type"],
                location=f"{vio['camera']} · {vio['vehicleType']}",
                severity=vio["severity"],
                icon="speed" if "Speed" in vio["type"] else "wrong-way"
            )

        # Convert annotated frame to base64
        _, buffer = cv2.imencode(".jpg", tracking_result["annotated_frame"])
        frame_b64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify({
            "status": "success",
            "active_count": tracking_result["active_count"],
            "total_unique_count": tracking_result["total_unique_count"],
            "active_detections": tracking_result["active_detections"],
            "new_violations": tracking_result["new_violations"],
            "annotated_frame_base64": f"data:image/jpeg;base64,{frame_b64}"
        })
    except Exception as e:
        return jsonify({"error": f"Tracking failed: {str(e)}"}), 500


# =========================================================
# ASTRAFLOW ANGULAR DASHBOARD ENDPOINTS
# =========================================================

@api_bp.route("/dashboard", methods=["GET"])
def get_dashboard():
    """Returns complete payload for DashboardComponent."""
    total_tracked = len(tracker.unique_vehicle_ids)
    display_total = total_tracked if total_tracked > 0 else 248
    alerts_count = len(tracker.violations) if tracker.violations else 12

    metrics = analytics.get_dashboard_metrics(
        live_total_vehicles=display_total,
        live_alerts_count=alerts_count
    )

    # Vehicle types mix
    vehicle_types = [
        {"label": "Cars", "count": 124, "percentage": 50, "icon": "car", "accent": "blue"},
        {"label": "Bikes", "count": 42, "percentage": 17, "icon": "bike", "accent": "amber"},
        {"label": "Buses", "count": 18, "percentage": 7, "icon": "bus", "accent": "violet"},
        {"label": "Trucks", "count": 8, "percentage": 3, "icon": "truck", "accent": "red"},
        {"label": "Other", "count": 56, "percentage": 23, "icon": "other", "accent": "slate"}
    ]

    # Live camera detections sample matching AstraFlow CameraDetection model
    active_dets = [
        {"label": "CAR", "confidence": 94, "trackingId": "094", "x": 34, "y": 58, "width": 16, "height": 23, "type": "car"},
        {"label": "CAR", "confidence": 91, "trackingId": "091", "x": 56, "y": 35, "width": 13, "height": 21, "type": "car"},
        {"label": "BUS", "confidence": 89, "trackingId": "089", "x": 69, "y": 43, "width": 15, "height": 28, "type": "bus"}
    ]

    return jsonify({
        "currentDate": datetime.now().strftime("%d %b %Y"),
        "dashboardMetrics": metrics,
        "vehicleTypes": vehicle_types,
        "trafficZones": analytics.get_zones(),
        "events": analytics.get_recent_events(),
        "detections": active_dets
    })


@api_bp.route("/live-monitor", methods=["GET"])
def get_live_monitor():
    """Returns payload for LiveMonitorComponent."""
    cameras = [
        {"id": "CAM-01", "name": "Central Junction", "location": "Sector 12 · Main Road", "status": "online", "vehicles": 72, "fps": 28, "congestion": "normal"},
        {"id": "CAM-02", "name": "North Avenue", "location": "Sector 8 · North Corridor", "status": "online", "vehicles": 48, "fps": 30, "congestion": "normal"},
        {"id": "CAM-03", "name": "East Corridor", "location": "Sector 15 · East Road", "status": "warning", "vehicles": 83, "fps": 26, "congestion": "congested"},
        {"id": "CAM-04", "name": "South Junction", "location": "Sector 4 · South Road", "status": "online", "vehicles": 45, "fps": 29, "congestion": "normal"}
    ]

    detections = [
        {"id": "094", "type": "car", "confidence": 94, "speed": 42, "lane": "Lane 02", "status": "normal"},
        {"id": "091", "type": "car", "confidence": 91, "speed": 51, "lane": "Lane 01", "status": "warning"},
        {"id": "089", "type": "bus", "confidence": 89, "speed": 38, "lane": "Lane 03", "status": "normal"},
        {"id": "087", "type": "bike", "confidence": 96, "speed": 46, "lane": "Lane 02", "status": "normal"},
        {"id": "081", "type": "truck", "confidence": 92, "speed": 34, "lane": "Lane 03", "status": "normal"}
    ]

    activities = [
        {"type": "Speed threshold exceeded", "camera": "CAM-01 · Car", "time": "10:42 AM", "severity": "critical"},
        {"type": "Vehicle detected", "camera": "CAM-01 · Bus", "time": "10:41 AM", "severity": "normal"},
        {"type": "Possible congestion", "camera": "CAM-01 · Lane 03", "time": "10:39 AM", "severity": "warning"},
        {"type": "Vehicle detected", "camera": "CAM-01 · Bike", "time": "10:37 AM", "severity": "normal"}
    ]

    return jsonify({
        "cameras": cameras,
        "detections": detections,
        "activities": activities
    })


@api_bp.route("/violations", methods=["GET"])
def get_violations():
    """Returns list of violations matching ViolationsComponent."""
    default_violations = [
        {
            "id": "VIO-1042",
            "type": "Speed Threshold Exceeded",
            "description": "Vehicle exceeded the configured speed limit",
            "location": "Central Junction",
            "camera": "CAM-01",
            "vehicle": "MH 12 AB 4821",
            "vehicleType": "Car",
            "time": "10:39 AM",
            "date": datetime.now().strftime("%d %b %Y"),
            "severity": "critical",
            "status": "open",
            "confidence": 96
        },
        {
            "id": "VIO-1041",
            "type": "Wrong-Way Movement",
            "description": "Vehicle detected moving against traffic direction",
            "location": "South Junction",
            "camera": "CAM-04",
            "vehicle": "JH 05 CD 2190",
            "vehicleType": "Car",
            "time": "10:32 AM",
            "date": datetime.now().strftime("%d %b %Y"),
            "severity": "critical",
            "status": "open",
            "confidence": 91
        },
        {
            "id": "VIO-1040",
            "type": "Vehicle Detection",
            "description": "Vehicle entered a monitored restricted zone",
            "location": "East Corridor",
            "camera": "CAM-03",
            "vehicle": "JH 01 EF 7824",
            "vehicleType": "Bus",
            "time": "10:27 AM",
            "date": datetime.now().strftime("%d %b %Y"),
            "severity": "warning",
            "status": "reviewed",
            "confidence": 89
        },
        {
            "id": "VIO-1039",
            "type": "Speed Threshold Exceeded",
            "description": "Vehicle exceeded the configured speed limit",
            "location": "North Avenue",
            "camera": "CAM-02",
            "vehicle": "BR 01 GH 4421",
            "vehicleType": "Bike",
            "time": "10:21 AM",
            "date": datetime.now().strftime("%d %b %Y"),
            "severity": "warning",
            "status": "open",
            "confidence": 94
        }
    ]

    # Combine recorded live violations with default log
    all_violations = tracker.violations + default_violations
    return jsonify({"violations": all_violations})


@api_bp.route("/analytics", methods=["GET"])
def get_analytics():
    """Returns analytics payload matching AnalyticsComponent."""
    return jsonify({
        "currentDate": datetime.now().strftime("%d %b %Y"),
        "kpiMetrics": [
            {"label": "Total Vehicles", "value": "248", "change": "+12.4%", "trend": "up", "icon": "vehicles", "accent": "blue"},
            {"label": "Average Speed", "value": "42", "unit": "km/h", "change": "+8.2%", "trend": "up", "icon": "speed", "accent": "violet"},
            {"label": "Avg. Journey Time", "value": "08:42", "change": "-6.8%", "trend": "down", "icon": "duration", "accent": "cyan"},
            {"label": "Traffic Alerts", "value": "12", "change": "+3.0%", "trend": "up", "icon": "alerts", "accent": "red"}
        ],
        "vehicleDistribution": [
            {"label": "Cars", "count": 124, "percentage": 50, "accent": "blue"},
            {"label": "Bikes", "count": 42, "percentage": 17, "accent": "amber"},
            {"label": "Buses", "count": 18, "percentage": 7, "accent": "violet"},
            {"label": "Trucks", "count": 8, "percentage": 3, "accent": "red"},
            {"label": "Other", "count": 56, "percentage": 23, "accent": "slate"}
        ],
        "zones": analytics.get_zone_performance()
    })


# =========================================================
# AUTHENTICATION ENDPOINTS (FOR ANGULAR AUTH SERVICE)
# =========================================================

@api_bp.route("/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "")
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Demo/Development authentication token
    return jsonify({
        "token": "astraflow_jwt_token_demo_98234",
        "user": {
            "email": email,
            "name": "FIVE.exe",
            "role": "admin"
        }
    })


@api_bp.route("/auth/signup", methods=["POST"])
def auth_signup():
    data = request.get_json(silent=True) or {}
    return jsonify({
        "status": "success",
        "message": "User registered successfully",
        "user": {
            "name": data.get("name", "User"),
            "email": data.get("email", "")
        }
    })
