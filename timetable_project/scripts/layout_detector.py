# layout_detector.py
import os
import pandas as pd
import numpy as np
from PIL import Image
from rapidfuzz import fuzz
from scripts.utils.ocr_utils import clean_text
from ultralytics import YOLO

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "../yolov8/runs/detect/train_3_class/weights/best.pt")
model = YOLO(MODEL_PATH)

def run_yolo_detection(image: Image.Image):
    img_array = np.array(image.convert("RGB"))
    results = model(img_array)
    boxes = []
    for box in results[0].boxes:
        cls = int(box.cls[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        boxes.append({
            "class": cls,
            "x1": x1, "x2": x2,
            "y1": y1, "y2": y2
        })
    return pd.DataFrame(boxes)

def refine_yolo_boxes_with_fallback(box_df, ocr_df, ocr_line_gap=10):
    refined = {}

    # Group OCR lines
    ocr_df_sorted = ocr_df.sort_values("y1")
    grouped_lines = []
    current_line = []
    last_y = None
    for _, row in ocr_df_sorted.iterrows():
        if last_y is None or abs(row["y1"] - last_y) <= ocr_line_gap:
            current_line.append(row)
        else:
            grouped_lines.append(current_line)
            current_line = [row]
        last_y = row["y1"]
    if current_line:
        grouped_lines.append(current_line)

    def find_line_pair(start_str, end_str):
        for i in range(len(grouped_lines) - 1):
            line1 = " ".join(clean_text(w["text"]) for w in grouped_lines[i])
            line2 = " ".join(clean_text(w["text"]) for w in grouped_lines[i + 1])
            if start_str in line1 and end_str in line2:
                y1 = min(w["y1"] for w in grouped_lines[i])
                y2 = max(w["y2"] for w in grouped_lines[i + 1])
                return y1, y2
        return None, None

    # === Week (class 1) ===
    week_boxes = box_df[box_df["class"] == 1]
    if week_boxes.empty:
        return refined
    wk = week_boxes.iloc[0].copy()
    for _, row in ocr_df.iterrows():
        txt = clean_text(row["text"])
        if any(fuzz.partial_ratio(txt, key) > 80 for key in ["WEEK", "VEEK", "EEK", "EKS"]):
            if row["x1"] < wk["x1"]:
                wk["x1"] = row["x1"] - 30
        if "13" in txt and row["x2"] > wk["x2"]:
            wk["x2"] = row["x2"] + 60
    refined[1] = wk

    # === TimeSlot (class 0) ===
    time_col_width = (wk["x2"] - wk["x1"]) * 0.08 # Get proportional width for fallback
    time_boxes = box_df[box_df["class"] == 0]
    ts = time_boxes.iloc[0].copy() if not time_boxes.empty else {}
    if "x1" in ts and "x2" in ts:
        x_shift = wk["x1"] - ts["x1"]
        ts["x1"] += x_shift
        ts["x2"] += x_shift
    else:
        ts["x1"] = wk["x1"]
        ts["x2"] = ts["x1"] + time_col_width

    # 👇 NEW: use "Week" label OCR to clamp x2
    first_week_col_width = (wk["x2"] - wk["x1"]) / 15
    ts["x2"] = ts["x1"] + first_week_col_width - 30

    y1_pair = find_line_pair("0830", "0900")
    y2_pair = find_line_pair("2200", "2230")
    if y1_pair[0] is not None:
        ts["y1"] = y1_pair[0] - 15
    if y2_pair[1] is not None:
        ts["y2"] = y2_pair[1] + 15
    refined[0] = ts

    # === CourseCell (class 2) ===
    course_boxes = box_df[box_df["class"] == 2]
    cc = course_boxes.iloc[0].copy() if not course_boxes.empty else {}
    cc["x1"] = ts["x2"] + 1
    cc["x2"] = wk["x2"]
    cc["y1"] = ts["y1"]
    cc["y2"] = ts["y2"]
    refined[2] = cc

    return refined

def get_refined_layout_boxes(image: Image.Image, ocr_df: pd.DataFrame) -> dict:
    """
    Given a PIL image, returns refined bounding boxes for layout classes.
    Output: { class_id: {x1, y1, x2, y2}, ... }
    """

    box_df = run_yolo_detection(image)
    return refine_yolo_boxes_with_fallback(box_df, ocr_df)
