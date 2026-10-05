import sys
import os
import cv2
import time

# Ensure parent path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from astraflow_backend.engine.traffic_tracker import TrafficTracker

def process_video(input_path, output_path):
    print(f"--- AstraFlow Video Processor ---")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")

    # Initialize tracker
    tracker = TrafficTracker()

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps == 0 or fps is None or fps != fps: # Handle NaN
        fps = 30.0

    print(f"Video Info: {width}x{height} @ {fps} FPS | Total Frames: {total_frames}")

    # Initialize VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_count = 0
    start_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        
        if frame_count > 300:
            print("Reached 300 frames test limit. Stopping early for quick preview.")
            break
            
        # Process frame
        # Conf threshold tuned for video stability
        result = tracker.process_frame(frame, conf_thresh=0.25)
        
        # Write annotated frame
        out.write(result["annotated_frame"])

        # Progress reporting every 30 frames
        if frame_count % 30 == 0:
            elapsed = time.time() - start_time
            current_fps = frame_count / elapsed
            print(f"Processed {frame_count}/{total_frames} frames ({current_fps:.1f} fps) - Unique Vehicles: {result['total_unique_count']} - Active: {result['active_count']}")

    cap.release()
    out.release()
    
    total_time = time.time() - start_time
    print(f"\nProcessing Complete!")
    print(f"Total Unique Vehicles Tracked: {len(tracker.unique_vehicle_ids)}")
    print(f"Total Violations Flagged: {len(tracker.violations)}")
    print(f"Time Taken: {total_time:.1f}s ({frame_count/total_time:.1f} avg FPS)")
    print(f"Saved annotated video to: {output_path}")

if __name__ == "__main__":
    input_video = r"C:\Users\Haru\Desktop\sem 7-8 proj\2165-155327596.mp4"
    output_video = r"C:\Users\Haru\Desktop\sem 7-8 proj\astraflow_annotated.mp4"
    process_video(input_video, output_video)
