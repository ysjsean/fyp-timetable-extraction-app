import re
import pandas as pd
from datetime import datetime, timedelta
from pdf2image import convert_from_path
from pytesseract import image_to_data, Output
from sklearn.cluster import DBSCAN
import numpy as np
from rapidfuzz import process, fuzz
import cv2
from scripts.utils.ocr_utils import clean_text
from scripts.utils.constants import DAYS, WEEKS, KNOWN_HOLIDAYS
from scripts.layout_detector import get_refined_layout_boxes
from dateutil import parser

def dedup(text):
    tokens = text.split()
    clean_tokens = []
    seen = set()
    for token in tokens:
        key = re.sub(r"[^A-Z0-9+]", "", token)
        if key and key not in seen:
            clean_tokens.append(token)
            seen.add(key)
    return " ".join(clean_tokens)

def week_sort_key(w):
    return 7.5 if w == "Recess" else int(w)

def time_overlap(t1, t2):
    def to_minutes(t): return int(t[:2]) * 60 + int(t[2:])
    s1, e1 = t1.split('-')
    s2, e2 = t2.split('-')
    return not (to_minutes(e1) <= to_minutes(s2) or to_minutes(e2) <= to_minutes(s1))


def is_month_like(token, threshold=80):
    token = token.lower()
    months = [m.lower() for m in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']]
    return any(fuzz.partial_ratio(token, m) >= threshold for m in months)



def extract_week_date_ranges(image, weeks_box):
    week_columns = get_weeks(weeks_box)
    box_height = weeks_box["y2"] - weeks_box["y1"]
    y1 = weeks_box["y2"]
    y2 = y1 + box_height * 2  # Go below to get both lines

    week_to_date_pair = {}
    for i, wk in enumerate(week_columns[1:]):  # skip "Week"
        x1, x2 = int(wk["x1"]), int(wk["x2"])
        crop = image.crop((x1 - 5, int(y1), x2 + 5, int(y2)))

        lines = [line.strip() for line in image_to_data(crop, output_type=Output.DICT)["text"] if line.strip()]

        if len(lines) >= 6:
            try:
                start_str = " ".join(lines[0:3])
                end_str   = " ".join(lines[3:6])
                start = datetime.strptime(start_str, "%d %b %y")
                end = datetime.strptime(end_str, "%d %b %y")

                week_to_date_pair[wk["label"]] = (start, end)
            except:
                week_to_date_pair[wk["label"]] = ("UNKNOWN", "UNKNOWN")
        else:
            week_to_date_pair[wk["label"]] = ("UNKNOWN", "UNKNOWN")

    return week_to_date_pair


def extract_base_start_date_from_weeks(image, week_boxes):
    if week_boxes.empty:
        # print("❌ No week box (class 1) found.")
        return None

    weeks = get_weeks(week_boxes)

    # Use Week 1 column
    week1 = weeks[1]  # Index 1 = Week 1
    x1, x2 = week1["x1"], week1["x2"]
    y2 = week_boxes["y1"]
    y1 = y2 - 60  # go upwards above week label

    # Crop image
    cropped = image.crop((x1, y1, x2, y2))
    img = np.array(cropped.convert("RGB"))

    # HSV masking & preprocessing
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    cyan_mask = cv2.inRange(hsv, (70, 20, 100), (110, 255, 255))
    img[cyan_mask > 0] = [255, 255, 255]
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    thresh = cv2.adaptiveThreshold(norm, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 15, 10)

    config = r'--psm 6'
    ocr_data = image_to_data(thresh, output_type=Output.DICT, config=config)
    lines = [t.strip() for t in ocr_data["text"] if t.strip()]
    text = " ".join(lines)

    # Try fuzzy date parsing
    try:
        parsed = parser.parse(text, fuzzy=True, dayfirst=True)
        return parsed
    except:
        return "UNKNOWN"



def detect_holiday_from_ocr(lines, threshold=80):
    """Try to match joined OCR lines to a known holiday using fuzzy matching."""
    joined = " ".join(lines).lower().strip()
    match, score, _ = process.extractOne(joined, KNOWN_HOLIDAYS, scorer=fuzz.token_sort_ratio)
    if score >= threshold:
        return match.upper()  # standardized clean name
    return None


def get_weeks(week_box, shrink_ratio=0.1):
    week_labels = ["Week"] + WEEKS
    col_width = (week_box["x2"] - week_box["x1"]) / 15

    boxes = []
    for i in range(15):
        x1 = week_box["x1"] + i * col_width
        x2 = week_box["x1"] + (i + 1) * col_width
        pad = (x2 - x1) * shrink_ratio / 2
        boxes.append({
            "label": week_labels[i],
            "x1": x1 + pad,
            "x2": x2 - pad,
            "index": i
        })
    return boxes


def get_time_rows(time_box):
    start = datetime.strptime("0830", "%H%M")
    row_height = (time_box["y2"] - time_box["y1"]) / 28
    return [{
        "label": f"{(start + timedelta(minutes=30 * i)).strftime('%H%M')}-{(start + timedelta(minutes=30 * (i + 1))).strftime('%H%M')}",
        "y1": time_box["y1"] + i * row_height,
        "y2": time_box["y1"] + (i + 1) * row_height
    } for i in range(28)]

def extract_ocr_df(image):
    ocr = image_to_data(image, output_type=Output.DICT)
    df = pd.DataFrame({
        "text": pd.Series(ocr["text"]).str.strip(),
        "conf": ocr["conf"],
        "x1": ocr["left"],
        "y1": ocr["top"],
        "width": ocr["width"],
        "height": ocr["height"]
    })
    df = df[(df["text"] != "") & (df["conf"] != "-1")].copy()
    df["x2"] = df["x1"] + df["width"]
    df["y2"] = df["y1"] + df["height"]
    df["xc"] = (df["x1"] + df["x2"]) / 2
    df["yc"] = (df["y1"] + df["y2"]) / 2
    return df

def extract_ocr_from_block(img_pil, offset_x=0, offset_y=0):
    img = np.array(img_pil.convert("RGB"))
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    cyan_mask = cv2.inRange(hsv, (70, 20, 100), (110, 255, 255))
    img[cyan_mask > 0] = [255, 255, 255]
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    norm = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    thresh = cv2.adaptiveThreshold(norm, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 15, 10)
    config = r'--oem 3 --psm 6'
    data = image_to_data(thresh, output_type=Output.DICT, config=config)
    df = pd.DataFrame({
        "text": pd.Series(data["text"]).str.strip(),
        "conf": data["conf"],
        "x1": data["left"],
        "y1": data["top"],
        "width": data["width"],
        "height": data["height"]
    })
    df = df[(df["text"] != "") & (df["conf"] != "-1")].copy()
    df["x1"] += offset_x
    df["x2"] = df["x1"] + df["width"]
    df["y1"] += offset_y
    df["y2"] = df["y1"] + df["height"]
    df["xc"] = (df["x1"] + df["x2"]) / 2
    df["yc"] = (df["y1"] + df["y2"]) / 2
    return df


def extract_courses(image, course_df, weeks, time_rows, day, week_to_date_pair):
    entries = []
    for _, blk in course_df.iterrows():
        bx1, bx2, by1, by2 = blk["x1"], blk["x2"], blk["y1"], blk["y2"]
        for wk in weeks:
            if wk["index"] == 0 or bx2 < wk["x1"] or bx1 > wk["x2"]:
                continue

            margin = 10  # pixels
            sx1 = max(bx1, wk["x1"] - margin)
            sx2 = min(bx2, wk["x2"] + margin)
            cropped = image.crop((sx1, by1, sx2, by2))
            ocr_inside = extract_ocr_from_block(cropped, offset_x=sx1, offset_y=by1)
            if ocr_inside.empty:
                continue

            y_coords = ocr_inside["yc"].values.reshape(-1, 1)
            labels = DBSCAN(eps=20, min_samples=1).fit(y_coords).labels_
            ocr_inside["line_group"] = labels
            grouped = list(ocr_inside.groupby("line_group", sort=False))
            line_map = [" ".join(group.sort_values("x1")["text"].values) for _, group in grouped]

            index_to_group_id = {i: group_id for i, (group_id, _) in enumerate(grouped)}

            used_lines = set()
            i = 0
            while i < len(line_map):
                if i in used_lines:
                    i += 1
                    continue

                # === Step 1: Detect holiday block ===
                note_lines = []
                note_index = None

                while i < len(line_map):
                    current = clean_text(line_map[i])
                    next_line = clean_text(line_map[i + 1]) if i + 1 < len(line_map) else ""

                    maybe_combo = detect_holiday_from_ocr([current, next_line])
                    if maybe_combo:
                        if maybe_combo not in note_lines:
                            note_lines.append(maybe_combo)
                        note_index = i + 2
                        i += 2
                        continue

                    maybe_single = detect_holiday_from_ocr([current])
                    if maybe_single:
                        if maybe_single not in note_lines:
                            note_lines.append(maybe_single)
                        note_index = i + 1
                        i += 1
                        continue

                    break

                # === Step 2: Look for next 3 non-holiday lines ===
                while i <= len(line_map) - 3:
                    block = [clean_text(line_map[j]) for j in range(i, i + 3)]
                    if all(line.lower() not in KNOWN_HOLIDAYS for line in block):
                        break
                    i += 1
                else:
                    break

                course_lines = [clean_text(line_map[j]) for j in range(i, i + 3)]

                # ✅ Only attach note if this block comes right after holiday
                note = ""
                if note_lines and i == note_index:
                    unique_lines = list(dict.fromkeys(note_lines))
                    note = f"{' '.join(unique_lines).strip()} on Week {wk['label']}"

                def is_location(t):
                    t = t.upper()
                    return (
                        t.startswith(("TR", "LT", "LKC", "S")) or
                        "+" in t or "-" in t or
                        (any(c.isdigit() for c in t) and any(c.isalpha() for c in t) and len(t) >= 5)
                    )

                def is_course_code(t):
                    t = t.upper()
                    return (
                        len(t) >= 5 and
                        any(c.isdigit() for c in t) and
                        any(c.isalpha() for c in t) and
                        not is_location(t)
                    )

                courseCode = next((x for x in course_lines if is_course_code(x)), course_lines[0])
                location = next((x for x in course_lines if is_location(x) and x != courseCode), course_lines[2])
                group = next((x for x in course_lines if x not in [courseCode, location]), course_lines[1])

                group_ids = [index_to_group_id.get(j, -1) for j in range(i, i+3)]
                y_groups = ocr_inside[ocr_inside["line_group"].isin(group_ids)]
                y1_lines = y_groups["y1"].min()
                y2_lines = y_groups["y2"].max()

                matched_times = [r["label"] for r in time_rows if not (r["y2"] < y1_lines or r["y1"] > y2_lines)]
                if not matched_times:
                    i += 1
                    continue

                time_range = f"{matched_times[0].split('-')[0]}-{matched_times[-1].split('-')[1]}"

                start, end = week_to_date_pair.get(wk["label"], ("UNKNOWN", "UNKNOWN"))
                day_offset = DAYS.index(day)

                if isinstance(start, datetime):
                    start_date = (start + timedelta(days=day_offset)).strftime("%d %b %y")
                else:
                    start_date = "UNKNOWN"

                entries.append({
                    "courseCode": courseCode,
                    "group": group,
                    "location": location,
                    "weeks": [wk["label"]],
                    "time": time_range,
                    "day": day,
                    "startDate": start_date,
                    "note": note
                })

                used_lines.update({i, i+1, i+2})
                i += 3

    return entries


def merge_entries(entries):
    def score_course_code(code):
        tokens = re.findall(r"[A-Z0-9]+", code)
        return (len(tokens), len(code))

    merged = []
    used = [False] * len(entries)
    for i, e1 in enumerate(entries):
        if used[i]:
            continue
        group = [e1]
        used[i] = True
        for j in range(i + 1, len(entries)):
            e2 = entries[j]
            if used[j]:
                continue
            if e1["day"] == e2["day"] and time_overlap(e1["time"], e2["time"]):
                group.append(e2)
                used[j] = True
        course_codes = [e["courseCode"] for e in group]
        best_code = dedup(clean_text(max(course_codes, key=score_course_code)))
        get_common = lambda field: max(set(field), key=field.count)
        group_field = dedup(clean_text(get_common([e["group"] for e in group])))
        location_field = dedup(clean_text(get_common([e["location"] for e in group])))
        weeks = sorted(set(w for e in group for w in e["weeks"]), key=week_sort_key)
        notes = "; ".join(sorted(set(e["note"] for e in group if e["note"])))
        merged.append({
            "courseCode": best_code,
            "group": group_field,
            "location": location_field,
            "weeks": weeks,
            "time": e1["time"],
            "day": e1["day"],
            "startDate": e1["startDate"],
            "note": notes
        })
    return merged

# === MAIN PIPELINE ===
def extract_timetable(pdf_path: str) -> list[dict]: 
    all_output = []

    for idx in range(5):
        day = DAYS[idx]
        
        image = convert_from_path(pdf_path, dpi=300, first_page=idx+1, last_page=idx+1)[0]

        ocr_df = extract_ocr_df(image)
        refined = get_refined_layout_boxes(image, ocr_df)

        time_box = refined[0]
        week_box = refined[1]
        course_df = pd.DataFrame([refined[2]])

        weeks = get_weeks(week_box)
        time_rows = get_time_rows(time_box)

        week_to_date_pair = extract_week_date_ranges(image, week_box)

        day_entries = extract_courses(image, course_df, weeks, time_rows, day, week_to_date_pair)
        merged_day = merge_entries(day_entries)
        all_output.extend(merged_day)

    return all_output