import os
import cv2
import numpy as np
from PIL import Image
import io
import base64
from ultralytics import YOLO

# COCO Classes relevant for Smart Traffic Monitoring
TRAFFIC_CLASSES = {
    0: {"name": "pedestrian", "type": "pedestrian", "frontend_type": "other"},
    1: {"name": "bicycle",    "type": "bike",       "frontend_type": "bike"},
    2: {"name": "car",        "type": "car",        "frontend_type": "car"},
    3: {"name": "motorcycle", "type": "bike",       "frontend_type": "bike"},
    5: {"name": "bus",        "type": "bus",        "frontend_type": "bus"},
    7: {"name": "truck",      "type": "truck",      "frontend_type": "truck"}
}

DEFAULT_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "yolov8n.pt")


class TrafficDetector:
    """
    Core AI Detection Engine for AstraFlow
    Utilizes YOLOv8 nano model optimized for real-time CPU & Edge inference.
    """

    def __init__(self, model_path: str = None):
        self.model_path = model_path or DEFAULT_MODEL_PATH
        if not os.path.exists(self.model_path):
            # Fallback to local default if path not yet resolved
            self.model_path = "yolov8n.pt"
            
        print(f"[AstraFlow AI Engine] Loading YOLO detection model from {self.model_path}...")
        self.model = YOLO(self.model_path)
        print("[AstraFlow AI Engine] Model loaded successfully.")

    def detect_image(self, image_input, conf_thresh: float = 0.25):
        """
        Run inference on image bytes or cv2 numpy image.
        Returns structured detection output formatted for AstraFlow Angular UI.
        """
        if isinstance(image_input, bytes):
            image = Image.open(io.BytesIO(image_input)).convert("RGB")
            cv_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        elif isinstance(image_input, np.ndarray):
            cv_img = image_input
        elif isinstance(image_input, str):
            cv_img = cv2.imread(image_input)
        else:
            raise ValueError("Unsupported image input type.")

        img_h, img_w = cv_img.shape[:2]

        # Filter only traffic-related classes (0, 1, 2, 3, 5, 7)
        target_classes = list(TRAFFIC_CLASSES.keys())
        results = self.model.predict(
            source=cv_img,
            conf=conf_thresh,
            classes=target_classes,
            verbose=False
        )

        detections = []
        vehicle_mix_counter = {"car": 0, "bike": 0, "bus": 0, "truck": 0, "other": 0}

        annotated_img = cv_img.copy()

        result = results[0]
        boxes = result.boxes

        for idx, box in enumerate(boxes):
            cls_id = int(box.cls[0].item())
            conf_score = float(box.conf[0].item())
            xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2] in pixels
            x1, y1, x2, y2 = xyxy

            # Compute bounding box dimensions
            box_w = x2 - x1
            box_h = y2 - y1

            # Compute percentage coordinates for AstraFlow UI (0-100%)
            pct_x = round((x1 / img_w) * 100, 1)
            pct_y = round((y1 / img_h) * 100, 1)
            pct_w = round((box_w / img_w) * 100, 1)
            pct_h = round((box_h / img_h) * 100, 1)

            class_meta = TRAFFIC_CLASSES.get(cls_id, {"name": "vehicle", "type": "car", "frontend_type": "other"})
            vehicle_type = class_meta["frontend_type"]
            label_text = class_meta["name"].upper()

            # Increment count
            if vehicle_type in vehicle_mix_counter:
                vehicle_mix_counter[vehicle_type] += 1
            else:
                vehicle_mix_counter["other"] += 1

            det_obj = {
                "id": f"DET-{idx + 1:03d}",
                "trackingId": f"{idx + 1:03d}",
                "label": label_text,
                "type": vehicle_type,
                "confidence": round(conf_score * 100, 1),
                "box_pixels": {
                    "x1": round(x1, 1),
                    "y1": round(y1, 1),
                    "x2": round(x2, 1),
                    "y2": round(y2, 1)
                },
                # AstraFlow Angular UI percentage format
                "x": pct_x,
                "y": pct_y,
                "width": pct_w,
                "height": pct_h
            }
            detections.append(det_obj)

            # Draw bounding box on visualization frame
            color = (0, 200, 255)  # Default yellow-orange
            if vehicle_type == "car":
                color = (255, 120, 0)   # Blueish in BGR
            elif vehicle_type == "bike":
                color = (0, 215, 255)   # Amber
            elif vehicle_type == "bus":
                color = (210, 50, 180)  # Violet
            elif vehicle_type == "truck":
                color = (50, 50, 220)   # Red

            cv2.rectangle(annotated_img, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            caption = f"{label_text} {round(conf_score * 100)}%"
            (tw, th), _ = cv2.getTextSize(caption, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated_img, (int(x1), int(y1) - 20), (int(x1) + tw, int(y1)), color, -1)
            cv2.putText(annotated_img, caption, (int(x1), int(y1) - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        total_vehicles = len(detections)

        # Calculate vehicle mix distribution
        vehicle_mix = []
        for v_type, count in vehicle_mix_counter.items():
            percentage = round((count / total_vehicles * 100), 1) if total_vehicles > 0 else 0
            accent_map = {
                "car": "blue",
                "bike": "amber",
                "bus": "violet",
                "truck": "red",
                "other": "slate"
            }
            label_text = "Buses" if v_type == "bus" else (v_type.capitalize() + "s" if v_type != "other" else "Other")
            vehicle_mix.append({
                "label": label_text,
                "count": count,
                "percentage": percentage,
                "icon": v_type,
                "accent": accent_map.get(v_type, "slate")
            })

        # Encode annotated image to base64 for direct API response
        _, buffer = cv2.imencode(".jpg", annotated_img)
        img_base64 = base64.b64encode(buffer).decode("utf-8")

        return {
            "total_vehicles": total_vehicles,
            "vehicle_mix": vehicle_mix,
            "detections": detections,
            "annotated_image_base64": f"data:image/jpeg;base64,{img_base64}",
            "image_dimensions": {"width": img_w, "height": img_h}
        }
