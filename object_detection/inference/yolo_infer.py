# yolo_camera_detect.py
import time

import cv2
from matplotlib import pyplot
from ultralytics import YOLO
from backend.services.yolo_detector import yolo_detect


def getObjects(image):
    model = YOLO("../model/yolov8n.pt")

    r = model(image)[0]
    objects = []
    for box in r.boxes:
        cls_id = int(box.cls)
        conf = float(box.conf)
        x1, y1, x2, y2 = box.xyxy  # tensor -> [x1, y1, x2, y2]
        objects.append({r.names[cls_id], conf, x1, y1, x2, y2})

    return {"Objects": objects}


def main():
    # Load a YOLOv8 model (pretrained or your custom model)
    model = YOLO("../model/yolov8n.pt", verbose=False)  # or 'best.pt' if you've trained your own

    # Open webcam (0 = default camera)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open camera.")
        return

    print("Press 'q' to quit.")

    while True:
        time.sleep(5)

        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame.")
            break
        print(yolo_detect(frame))
        # Run YOLO inference on the frame
        results = model(frame, verbose=False)

        # Draw detection boxes on the frame
        annotated_frame = results[0].plot()

        # Display the annotated frame
        cv2.imshow("YOLOv8 Camera Detection", annotated_frame)

        # Exit on 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release camera and close window
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
