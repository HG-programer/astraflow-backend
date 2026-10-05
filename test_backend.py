import os
import sys
import json

# Ensure parent path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from astraflow_backend.engine.detector import TrafficDetector
from astraflow_backend.app import create_app

def test_ai_detector():
    print("\n--- [1] Testing TrafficDetector ---")
    detector = TrafficDetector()
    sample_img_path = os.path.join(os.path.dirname(__file__), "..", "bus.jpg")

    if not os.path.exists(sample_img_path):
        print(f"Error: Sample image not found at {sample_img_path}")
        return False

    with open(sample_img_path, "rb") as f:
        img_bytes = f.read()

    result = detector.detect_image(img_bytes)
    print(f"Total Vehicles Detected: {result['total_vehicles']}")
    print(f"Vehicle Mix: {json.dumps(result['vehicle_mix'], indent=2)}")
    print(f"First 2 Detections (AstraFlow UI Format):")
    for det in result['detections'][:2]:
        print(f" - ID: {det['trackingId']}, Label: {det['label']}, Type: {det['type']}, Conf: {det['confidence']}%, Box: (x={det['x']}%, y={det['y']}%, w={det['width']}%, h={det['height']}%)")

    assert result['total_vehicles'] > 0, "No vehicles detected!"
    print("AI Detector Test: PASSED ✅\n")
    return True

def test_api_endpoints():
    print("--- [2] Testing Flask API Endpoints ---")
    app = create_app()
    client = app.test_client()

    # Health check
    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed with {res.status_code}"
    print(f"GET /api/health -> 200 OK: {res.get_json()['status']}")

    # Dashboard check
    res = client.get("/api/dashboard")
    assert res.status_code == 200, f"Dashboard check failed with {res.status_code}"
    data = res.get_json()
    print(f"GET /api/dashboard -> 200 OK: {len(data['dashboardMetrics'])} KPI metrics, {len(data['trafficZones'])} zones")

    # Live Monitor check
    res = client.get("/api/live-monitor")
    assert res.status_code == 200, f"Live monitor check failed with {res.status_code}"
    data = res.get_json()
    print(f"GET /api/live-monitor -> 200 OK: {len(data['cameras'])} cameras, {len(data['detections'])} detections")

    # Violations check
    res = client.get("/api/violations")
    assert res.status_code == 200, f"Violations check failed with {res.status_code}"
    data = res.get_json()
    print(f"GET /api/violations -> 200 OK: {len(data['violations'])} violations")

    # Image Detection API POST check
    sample_img_path = os.path.join(os.path.dirname(__file__), "..", "bus.jpg")
    with open(sample_img_path, "rb") as f:
        res = client.post("/api/detect/image", data={"imageFile": (f, "test.jpg")}, content_type="multipart/form-data")
    assert res.status_code == 200, f"Image detection failed with {res.status_code}"
    det_data = res.get_json()["data"]
    print(f"POST /api/detect/image -> 200 OK: Detected {det_data['total_vehicles']} vehicles")

    print("Flask API Test: PASSED ✅\n")
    return True

if __name__ == "__main__":
    ai_ok = test_ai_detector()
    api_ok = test_api_endpoints()
    if ai_ok and api_ok:
        print("ALL TESTS PASSED! AstraFlow AI Engine and Backend API are fully functional! 🚦🚀")
