from ultralytics import YOLO

# Load model (you can switch to yolov8m.pt later)
model = YOLO("yolov8s.pt")


# Try training, catch any exception
try:
    model.train(
        data="dataset/data.yaml",
        epochs=200,              # 🔁 your call — 200 is good for small dataset
        imgsz=1280,              # 📐 matches A4 resolution at 300 DPI
        batch=4,                 # 🧠 depends on GPU VRAM — safe default
        mosaic=0.0,              # ❌ off — mosaic messes with spatial layout
        translate=0.05,          # 🔄 minor augmentations are OK
        scale=0.1,
        fliplr=0.0,              # ❌ off — timetables shouldn't be flipped
        degrees=0.0,             # ⛔ no rotation either
        shear=0.0,
        perspective=0.0,
        resume=False,
        name="train_3_class"
    )
except Exception as e:
    print("\n❌ Training crashed with error:")
    print(e)