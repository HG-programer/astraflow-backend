# AstraFlow: Computer Vision & AI Research Documentation 🚦
### Academic & Engineering Analysis for Semester 7-8 Project Report and Defense

---

## 1. Architectural Transition: InsightLens to AstraFlow

### The Prototype (`InsightLens`)
The initial prototype utilized an encoder-decoder Vision Transformer model (`nlpconnect/vit-gpt2-image-captioning`).
- **Nature**: Generative Image Captioning (Image-to-Text NLP).
- **Output**: Unstructured text sentence (e.g., *"a busy city street with multiple cars and a bus"*).
- **Shortcomings for Traffic Engineering**:
  - Cannot localize objects (no spatial bounding box coordinates `x, y, w, h`).
  - Cannot count distinct vehicle categories (unable to distinguish 3 cars vs 15 cars).
  - Incapable of temporal tracking across video streams.
  - Incapable of estimating vehicle velocities or directional anomalies.

### The Production Engine (`AstraFlow AI Layer`)
Transitioned to an end-to-end Computer Vision pipeline:
$$\text{Video Frame} \xrightarrow{\text{YOLOv8}} \text{Detections} \xrightarrow{\text{ByteTrack}} \text{Persistent Trajectories} \xrightarrow{\text{Rule Engine}} \text{Violations \& Metrics}$$

---

## 2. Object Detection Model Selection

### Comparative Analysis of Candidate Architectures

| Architecture | Model Family | Parameters / Size | Inference Speed (CPU) | mAP (COCO) | Tracking Suitability |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **YOLOv8 Nano (Ours)** | Single-Stage Anchor-Free CNN | **3.2M / 6.2 MB** | **~25 - 45 ms (~25-40 FPS)** | **37.3** | **Optimal** (Low latency enables real-time MOT) |
| Faster R-CNN (ResNet-50) | Two-Stage Region Proposal | ~41M / 160 MB | ~350 - 500 ms (~2-3 FPS) | 40.2 | Poor for real-time traffic video on CPU |
| SSD (MobileNetV2) | Single-Stage Anchor-Based | ~4.3M / 15 MB | ~40 - 60 ms (~18 FPS) | 22.1 | Moderate (Lower accuracy on small distant bikes/cars) |
| DETR (Transformer) | End-to-End Object Query Transformer | ~41M / 167 MB | ~450 - 650 ms (~1.5 FPS) | 42.0 | Impractical without dedicated multi-GPU setup |

### Why YOLOv8 Nano (`yolov8n`) Was Selected:
1. **Anchor-Free Detection Head**: Decouples classification and bounding box regression branches, improving small-object detection (critical for bikes and pedestrians in distant traffic).
2. **Extreme CPU Efficiency**: With 3.2M parameters and 6.2 MB disk size, it runs comfortably at 25-40 FPS on a standard quad-core CPU (such as AMD Ryzen 5 3400G) without dropping video frames.
3. **COCO Class Alignment**: Out-of-the-box pretrained weights directly support vehicles (Car, Motorcycle, Bus, Truck, Bicycle) and Pedestrians with zero fine-tuning required for Phase 1.

---

## 3. Multi-Object Tracking (MOT): Why ByteTrack?

Multi-Object Tracking assigns persistent IDs ($ID_k$) to vehicles across frames $t, t+1, \dots, t+N$.

### Comparison: SORT vs DeepSORT vs ByteTrack

1. **SORT (Simple Online and Realtime Tracking)**:
   - Uses Kalman filter and Hungarian algorithm based only on high-confidence bounding box IoU.
   - *Limitation*: Drops tracks during partial occlusion (e.g., when a motorcycle is momentarily shielded by a bus).
2. **DeepSORT**:
   - Adds deep visual feature re-identification (ReID) embedding network.
   - *Limitation*: The ReID CNN feature extractor adds 30-50ms latency per frame on CPU, making it unfeasible for multi-camera streams without a high-end GPU.
3. **ByteTrack (Adopted in AstraFlow)**:
   - Introduces **BYTE data association**: retains both high-confidence AND low-confidence detection boxes.
   - First matches high-confidence boxes to existing tracks; then attempts to match remaining unmatched tracks with low-confidence detections.
   - Eliminates false track terminations caused by occlusion, glare, or motion blur, while running at **over 30 FPS on CPU** because it requires no separate ReID neural network.

---

## 4. Mathematical Formulations

### A. Velocity & Trajectory Estimation
Given track centroid $\mathbf{P}(t) = (c_x(t), c_y(t))$ and calibrated spatial scale $\alpha$ (pixels/meter):
$$\Delta s = \frac{\sqrt{(c_x(t) - c_x(t - \Delta t))^2 + (c_y(t) - c_y(t - \Delta t))^2}}{\alpha}$$
$$v = \frac{\Delta s}{\Delta t} \times 3.6 \quad [\text{km/h}]$$

### B. Wrong-Way Movement Detection
Given nominal road travel vector $\vec{u}_{norm}$ and estimated trajectory vector $\vec{v}_{veh} = \mathbf{P}(t) - \mathbf{P}(t - \Delta t)$:
$$\cos \theta = \frac{\vec{u}_{norm} \cdot \vec{v}_{veh}}{\|\vec{u}_{norm}\| \|\vec{v}_{veh}\|}$$
If $\cos \theta < -0.5$ (trajectory counter to flow by $>120^\circ$) over consecutive frames, a **Wrong-Way Critical Violation** is triggered.

---

## 5. System Limitations & Future Scope

### Current Limitations:
1. **Camera Perspective Distortion**: Without per-camera homography matrix calibration ($3\times3$ projective transform), speed estimations remain an approximation based on 2D pixel displacement.
2. **Adverse Environmental Conditions**: Nighttime glare, heavy rain, or severe headlight reflection can reduce detection confidence below the $0.25$ threshold.
3. **Extreme Occlusion**: Complete vehicle occlusion exceeding 30 consecutive frames causes ByteTrack to reassign a new tracking ID upon reappearance.

### Future Enhancements:
1. **Homography Calibration Tool**: Interactive bird's-eye view (BEV) ground plane mapping in Angular for centimeter-accurate speed estimation.
2. **License Plate Recognition (ANPR)**: Integration of a secondary OCR model (e.g., PaddleOCR / EasyOCR) triggered on violation bounding boxes.
3. **Edge Deployment**: Model export to ONNX / OpenVINO / TensorRT for deployment on edge gateway devices (Jetson Orin Nano or Raspberry Pi 5).
