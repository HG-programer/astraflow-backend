# AstraFlow API Contract & Frontend Integration Guide 🚦

This document defines the REST API contract between the **AstraFlow Python AI Backend** (`http://127.0.0.1:5000`) and the **Angular Frontend** (`http://localhost:4200`).

All response models are directly aligned with the TypeScript interfaces in AstraFlow frontend (`DashboardComponent`, `LiveMonitorComponent`, `ViolationsComponent`, `AnalyticsComponent`).

---

## 1. Base URL & Configuration

- **Backend Base URL**: `http://127.0.0.1:5000/api`
- **CORS Enabled**: Yes (configured for `http://localhost:4200` and `http://localhost:4300`)
- **Content-Type**: `application/json` (or `multipart/form-data` for image/video uploads)

---

## 2. API Endpoints Overview

| Method | Endpoint | Description | Frontend Page / Service |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status | System health check |
| `GET` | `/api/dashboard` | Main dashboard summary & metrics | `DashboardComponent` |
| `GET` | `/api/live-monitor`| Live cameras & active detections | `LiveMonitorComponent` |
| `GET` | `/api/violations` | Traffic violations log & stats | `ViolationsComponent` |
| `GET` | `/api/analytics` | Analytical breakdown & KPIs | `AnalyticsComponent` |
| `POST` | `/api/detect/image`| Real-time image inference (YOLOv8)| Live Monitor / Upload |
| `POST` | `/api/track/frame` | Multi-Object Tracking (ByteTrack) | Live Stream / Camera feed |
| `POST` | `/api/auth/login` | Administrator authentication | `AuthService` (`/login`) |
| `POST` | `/api/auth/signup`| User registration | `AuthService` (`/signup`) |

---

## 3. Detailed Endpoint Specifications

### A. Dashboard Data (`GET /api/dashboard`)

Maps directly to `DashboardComponent` (`dashboardMetrics`, `vehicleTypes`, `trafficZones`, `events`, `detections`).

#### Sample Response:
```json
{
  "currentDate": "05 Oct 2026",
  "dashboardMetrics": [
    {
      "label": "Total Vehicles",
      "value": "248",
      "comparison": "+12%",
      "trend": "up",
      "icon": "vehicles",
      "accent": "blue",
      "description": "Detected across monitored zones"
    },
    {
      "label": "Average Speed",
      "value": "42",
      "unit": "km/h",
      "comparison": "+8%",
      "trend": "up",
      "icon": "speed",
      "accent": "violet",
      "description": "Across active road segments"
    },
    {
      "label": "Active Alerts",
      "value": "12",
      "comparison": "+3%",
      "trend": "up",
      "icon": "alerts",
      "accent": "red",
      "description": "Require attention"
    },
    {
      "label": "Traffic Zones",
      "value": "04",
      "comparison": "Normal",
      "trend": "neutral",
      "icon": "zones",
      "accent": "cyan",
      "description": "All monitored zones"
    }
  ],
  "vehicleTypes": [
    { "label": "Cars", "count": 124, "percentage": 50, "icon": "car", "accent": "blue" },
    { "label": "Bikes", "count": 42, "percentage": 17, "icon": "bike", "accent": "amber" },
    { "label": "Buses", "count": 18, "percentage": 7, "icon": "bus", "accent": "violet" },
    { "label": "Trucks", "count": 8, "percentage": 3, "icon": "truck", "accent": "red" },
    { "label": "Other", "count": 56, "percentage": 23, "icon": "other", "accent": "slate" }
  ],
  "trafficZones": [
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
      "id": "CAM-03",
      "name": "East Corridor",
      "status": "congested",
      "cameras": 2,
      "vehicles": 83,
      "speed": 31,
      "x": 43,
      "y": 67
    }
  ],
  "events": [
    {
      "type": "Speed threshold exceeded",
      "location": "CAM-01 · Car",
      "time": "10:39 AM",
      "severity": "critical",
      "icon": "speed"
    }
  ],
  "detections": [
    {
      "label": "CAR",
      "confidence": 94,
      "trackingId": "094",
      "x": 34,
      "y": 58,
      "width": 16,
      "height": 23,
      "type": "car"
    }
  ]
}
```

---

### B. Live Monitor (`GET /api/live-monitor`)

Maps directly to `LiveMonitorComponent` (`cameras`, `detections`, `activities`).

#### Sample Response:
```json
{
  "cameras": [
    {
      "id": "CAM-01",
      "name": "Central Junction",
      "location": "Sector 12 · Main Road",
      "status": "online",
      "vehicles": 72,
      "fps": 28,
      "congestion": "normal"
    },
    {
      "id": "CAM-03",
      "name": "East Corridor",
      "location": "Sector 15 · East Road",
      "status": "warning",
      "vehicles": 83,
      "fps": 26,
      "congestion": "congested"
    }
  ],
  "detections": [
    {
      "id": "094",
      "type": "car",
      "confidence": 94,
      "speed": 42,
      "lane": "Lane 02",
      "status": "normal"
    },
    {
      "id": "091",
      "type": "car",
      "confidence": 91,
      "speed": 51,
      "lane": "Lane 01",
      "status": "warning"
    }
  ],
  "activities": [
    {
      "type": "Speed threshold exceeded",
      "camera": "CAM-01 · Car",
      "time": "10:42 AM",
      "severity": "critical"
    }
  ]
}
```

---

### C. Traffic Violations (`GET /api/violations`)

Maps directly to `ViolationsComponent` (`Violation[]`).

#### Sample Response:
```json
{
  "violations": [
    {
      "id": "VIO-1042",
      "type": "Speed Threshold Exceeded",
      "description": "Vehicle exceeded the configured speed limit",
      "location": "Central Junction",
      "camera": "CAM-01",
      "vehicle": "MH 12 AB 4821",
      "vehicleType": "Car",
      "time": "10:39 AM",
      "date": "02 Oct 2026",
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
      "date": "02 Oct 2026",
      "severity": "critical",
      "status": "open",
      "confidence": 91
    }
  ]
}
```

---

### D. AI Image Detection (`POST /api/detect/image`)

Upload an image to perform real-time YOLOv8 vehicle detection.

- **Request**: `multipart/form-data` with key `imageFile` (or `image`), or JSON `{ "image_base64": "..." }`
- **Query Param (Optional)**: `conf=0.25`

#### Sample Response:
```json
{
  "status": "success",
  "data": {
    "total_vehicles": 3,
    "vehicle_mix": [
      { "label": "Cars", "count": 2, "percentage": 66.7, "icon": "car", "accent": "blue" },
      { "label": "Bikes", "count": 1, "percentage": 33.3, "icon": "bike", "accent": "amber" }
    ],
    "detections": [
      {
        "id": "DET-001",
        "trackingId": "001",
        "label": "CAR",
        "type": "car",
        "confidence": 92.4,
        "x": 34.2,
        "y": 58.1,
        "width": 16.4,
        "height": 23.0
      }
    ],
    "annotated_image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
  }
}
```

---

## 4. How to Connect Angular to Python Backend

In AstraFlow Angular project:
1. Update `src/environments/environment.ts`:
   ```typescript
   export const environment = {
     production: false,
     apiUrl: 'http://127.0.0.1:5000/api'
   };
   ```
2. Create an Angular Service `DashboardService` using `HttpClient`:
   ```typescript
   import { Injectable } from '@angular/core';
   import { HttpClient } from '@angular/common/http';
   import { Observable } from 'rxjs';
   import { environment } from 'src/environments/environment';

   @Injectable({ providedIn: 'root' })
   export class DashboardService {
     constructor(private http: HttpClient) {}

     getDashboardData(): Observable<any> {
       return this.http.get(`${environment.apiUrl}/dashboard`);
     }

     getLiveMonitorData(): Observable<any> {
       return this.http.get(`${environment.apiUrl}/live-monitor`);
     }

     getViolations(): Observable<any> {
       return this.http.get(`${environment.apiUrl}/violations`);
     }
   }
   ```
