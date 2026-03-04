# train_yolo_household.py
from ultralytics import YOLO

def main():
    # Load a model
    model = YOLO("yolo11n.pt")  # load a pretrained model (recommended for training)

    # Train the model
    results = model.train(data="lvis.yaml", epochs=100, imgsz=640)

    # Evaluate performance on validation set
    model.val()

    # Export trained weights to ONNX or CoreML if needed
    model.export(format="onnx")  # optional

if __name__ == "__main__":
    main()