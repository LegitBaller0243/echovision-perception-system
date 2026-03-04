# yolo_detector.py
from ultralytics import YOLO
import os
from dotenv import load_dotenv

load_dotenv()

# Load YOLO model once at import
MODEL_PATH = os.getenv("YOLO_MODEL_PATH")
model = YOLO('yolov8n.pt', verbose=False)


def yolo_detect(image_path: str):
    # Run YOLO inference
    results = model.predict(image_path, verbose=False)[0]

    objects = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist() # tensor -> [x1, y1, x2, y2]
        objects.append({
            "class": results.names[cls_id],
            "confidence": round(conf, 3),
            "position": {
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2
            }
        })

    return {"Objects": objects}

# Example standalone test
if __name__ == "__main__":
    sample_image = "test.jpg"
    output = yolo_detect(sample_image)
    print(output)
