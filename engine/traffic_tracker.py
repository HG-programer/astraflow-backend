import os
import cv2
import time
import math
from datetime import datetime
from collections import defaultdict
from ultralytics import YOLO
from .detector import TRAFFIC_CLASSES, DEFAULT_MODEL_PATH


class TrafficTracker:
    """
    Multi-Object Tracking, Trajectory Analysis, and Violation Engine.
    Uses ByteTrack to assign unique persistent tracking IDs to vehicles across frames,
    preventing duplicate counts and calculating speed/direction vectors.
    """

    def __init__(self, model_path: str = None, speed_limit_kmh: float = 50.0):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        if not os.path.exists(self.model_path):
            self.model_path = "yolov8n.pt"

        print(f"[AstraFlow Tracker] Initializing Tracker with model {self.model_path}...")
        self.model = YOLO(self.model_path)
        self.speed_limit = speed_limit_kmh

        # State storage
        self.track_history = defaultdict(list)     # {track_id: [(cx, cy, timestamp), ...]}
        self.unique_vehicle_ids = set()           # Set of all unique IDs seen
        self.vehicle_types = {}                   # {track_id: "car" | "bike" | "bus" | "truck"}
        self.estimated_speeds = {}                # {track_id: speed_kmh}
        self.violations = []                      # List of detected violation dicts
        self.violation_counter = 1000

        # Pixels-to-real-world scale estimation factor (can be calibrated per camera)
        self.pixels_per_meter = 12.0

    def get_lane_for_x(self, x_pct: float) -> str:
        """Estimate lane based on horizontal percentage position."""
        if x_pct < 33.3:
            return "Lane 01"
        elif x_pct < 66.6:
            return "Lane 02"
        else:
            return "Lane 03"

    def process_frame(
        self,
        frame,
        camera_id: str = "CAM-01",
        camera_name: str = "Central Junction",
        flow_direction: str = "down",  # "down" or "up"
        conf_thresh: float = 0.25
    ):
        """
        Process a single video frame with ByteTrack.
        Returns active detections, updated counts, speed estimations, and any newly triggered violations.
        """
        current_time = time.time()
        img_h, img_w = frame.shape[:2]

        target_classes = list(TRAFFIC_CLASSES.keys())
        # Run ByteTrack multi-object tracking
        results = self.model.track(
            source=frame,
            conf=conf_thresh,
            classes=target_classes,
            persist=True,
            tracker="bytetrack.yaml",
            verbose=False
        )

        active_detections = []
        new_violations = []
        annotated_frame = frame.copy()

        if results and results[0].boxes and results[0].boxes.id is not None:
            boxes = results[0].boxes
            track_ids = boxes.id.int().cpu().tolist()
            cls_ids = boxes.cls.int().cpu().tolist()
            confs = boxes.conf.cpu().tolist()
            xyxys = boxes.xyxy.cpu().tolist()

            for track_id, cls_id, conf_val, xyxy in zip(track_ids, cls_ids, confs, xyxys):
                x1, y1, x2, y2 = xyxy
                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0

                box_w = x2 - x1
                box_h = y2 - y1

                pct_x = round((x1 / img_w) * 100, 1)
                pct_y = round((y1 / img_h) * 100, 1)
                pct_w = round((box_w / img_w) * 100, 1)
                pct_h = round((box_h / img_h) * 100, 1)

                class_meta = TRAFFIC_CLASSES.get(cls_id, {"name": "car", "frontend_type": "car"})
                v_type = class_meta["frontend_type"]
                label_text = class_meta["name"].upper()

                self.unique_vehicle_ids.add(track_id)
                self.vehicle_types[track_id] = v_type

                # Update trajectory history (keep last 30 points)
                history = self.track_history[track_id]
                history.append((cx, cy, current_time))
                if len(history) > 30:
                    history.pop(0)

                # Speed estimation & direction analysis
                speed_kmh = 35.0  # Default sensible urban road baseline
                status = "normal"

                if len(history) >= 3:
                    prev_cx, prev_cy, prev_t = history[0]
                    curr_cx, curr_cy, curr_t = history[-1]
                    dt = curr_t - prev_t
                    if dt > 0.05:
                        dx = curr_cx - prev_cx
                        dy = curr_cy - prev_cy
                        pixel_dist = math.sqrt(dx ** 2 + dy ** 2)
                        # meters / sec to km / h
                        speed_mps = (pixel_dist / self.pixels_per_meter) / dt
                        raw_speed_kmh = speed_mps * 3.6
                        # Smooth realistic bounding between 15 km/h and 110 km/h
                        speed_kmh = round(min(max(raw_speed_kmh, 15.0), 95.0), 1)
                        self.estimated_speeds[track_id] = speed_kmh

                        # Direction / Wrong-way check
                        is_wrong_way = False
                        if flow_direction == "down" and dy < -30:
                            is_wrong_way = True
                        elif flow_direction == "up" and dy > 30:
                            is_wrong_way = True

                        if is_wrong_way:
                            status = "critical"
                            self.violation_counter += 1
                            vio = {
                                "id": f"VIO-{self.violation_counter}",
                                "type": "Wrong-Way Movement",
                                "description": f"Vehicle moving against designated traffic direction in {self.get_lane_for_x(pct_x)}",
                                "location": camera_name,
                                "camera": camera_id,
                                "vehicle": f"TRK-{track_id:03d}",
                                "vehicleType": v_type.capitalize(),
                                "time": datetime.now().strftime("%I:%M %p"),
                                "date": datetime.now().strftime("%d %b %Y"),
                                "severity": "critical",
                                "status": "open",
                                "confidence": round(conf_val * 100, 1)
                            }
                            new_violations.append(vio)
                            self.violations.append(vio)

                        # Speed limit check
                        elif speed_kmh > self.speed_limit:
                            status = "warning"
                            if speed_kmh > (self.speed_limit * 1.3):
                                status = "critical"

                            self.violation_counter += 1
                            vio = {
                                "id": f"VIO-{self.violation_counter}",
                                "type": "Speed Threshold Exceeded",
                                "description": f"Vehicle recorded at {speed_kmh} km/h (Limit: {self.speed_limit} km/h)",
                                "location": camera_name,
                                "camera": camera_id,
                                "vehicle": f"TRK-{track_id:03d}",
                                "vehicleType": v_type.capitalize(),
                                "time": datetime.now().strftime("%I:%M %p"),
                                "date": datetime.now().strftime("%d %b %Y"),
                                "severity": status,
                                "status": "open",
                                "confidence": round(conf_val * 100, 1)
                            }
                            new_violations.append(vio)
                            self.violations.append(vio)

                lane_label = self.get_lane_for_x(pct_x)

                det = {
                    "id": f"{track_id:03d}",
                    "trackingId": f"{track_id:03d}",
                    "type": v_type,
                    "confidence": round(conf_val * 100, 1),
                    "speed": speed_kmh,
                    "lane": lane_label,
                    "status": status,
                    "x": pct_x,
                    "y": pct_y,
                    "width": pct_w,
                    "height": pct_h,
                    "label": label_text
                }
                active_detections.append(det)

                # Draw tracking bounding box and ID label
                cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 120), 2)
                caption = f"ID:{track_id} {label_text} {speed_kmh}km/h"
                cv2.putText(annotated_frame, caption, (int(x1), max(20, int(y1) - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120), 2)

        # Vehicle mix of all unique vehicles tracked
        type_counts = defaultdict(int)
        for _, t_type in self.vehicle_types.items():
            type_counts[t_type] += 1

        total_unique = len(self.unique_vehicle_ids)

        return {
            "active_count": len(active_detections),
            "total_unique_count": total_unique,
            "active_detections": active_detections,
            "new_violations": new_violations,
            "annotated_frame": annotated_frame
        }
