# ✅ FINAL TIMETABLE EXTRACTION PIPELINE RULES

---

## 📥 1. PDF to Image

- Convert each page using **300 DPI**
- A4 size = 2480 x 3508 pixels
- Process one page at a time, discard after use

---

## 📦 2. Bounding Boxes (YOLO format)

- YOLO boxes are converted to absolute pixels using image size
- Class mapping:
  - `class 0` → Time slot region (to split into 30-min rows)
  - `class 1` → Week region (to split into 15 columns)
  - `class 2` → Course region (can contain multiple stacked courses)

---

## 🧭 3. Split Week Columns & Time Slots

### ➤ Week Columns

- Split `class 1` box into:
  - `"Week"` (skip)
  - `"1"` to `"7"`
  - `"Recess"` (keep, sort last)
  - `"8"` to `"13"`
- Each gets a bounding box (`x1`, `x2`)

### ➤ Time Slots

- Split `class 0` vertically into **28 blocks**
- Each = 30 mins: `0830–0900` to `2200–2230`
- Each block has `y1`, `y2`

---

## 🔍 4. Process Course Region (class 2)

- For each course region:
  - Intersect with each **week column**
    - Clip vertically by `x1–x2`
    - OCR inside this vertical slice only
  - Group OCR lines by vertical clustering (DBSCAN on `yc`)
  - Sort within group by `x1`

---

## 🧱 5. Detect Course Block

### Standard (3 lines)

1. `courseCode`
2. `group`
3. `location`

### Holiday Case (4 lines)

- If line 1 is a known holiday (e.g. `Deepavali`)
  - Save as `note = "Deepavali on Week X"`
  - Lines 2–4 become the valid course block

---

## 🧠 6. Derive Time Range

- Use pixel `y1` and `y2` of the 3-line block
- Match overlapping rows in time grid
- Compose `time` as `"start–end"` (e.g. `"0900–1030"`)

---

## 📤 7. Output Format

```json
{
  "courseCode": "EG1001",
  "group": "E042",
  "location": "TR+92",
  "weeks": ["1", "2"],
  "time": "0830-0900",
  "day": "Monday",
  "startDate": "14 Aug 23",
  "note": "Deepavali on Week 13"
}
```

---

## 🔁 8. Merging Entries

- Merge if:
  - Same `day`
  - Same or overlapping `time`
  - Matching tokens in `courseCode`, `group`, `location`
- Merge `weeks`
- Retain any `note`

---

## ❌ Rules to Avoid

- NO regex filtering
- NO assumption on courseCode validity
- NO merging horizontally before bounding box split
- DO NOT skip “Recess” — retain, but sort last (use key = 7.5)
