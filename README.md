
# 🗓️ Timetable to ICS Converter (Final Year Project)

This project extracts course schedules from university timetable PDFs using layout detection and OCR, and converts them into `.ics` calendar files compatible with Google Calendar, Outlook, and Apple Calendar.

Built with `Streamlit`, `YOLOv8`, `pytesseract`, and custom timetable layout rules.

---

## 🚀 Features

- Upload timetable **PDF**
- Detect timetable layout using YOLOv8 + OCR
- Automatically extract:
  - Course code, group, location
  - Weeks and dates
  - Start/end times
  - Holidays (e.g. Deepavali)
- Manual edits via Streamlit interface
- Export to `.ics` calendar format
- Date parsing from timetable headers (Week 1 column)
- Stacked course block detection across vertical slices
- Holiday detection using fuzzy OCR (e.g. “Union Day”, “Deepavali”)
- 1-click launch support (Windows and macOS/Linux)

---

## 🧱 Folder Structure
```
📁 FYP-Timetable-Extraction-App/
│
├── 📁 timetable_env/ 
│   └─ Python virtual environment
│
├── 📁 timetable_project/  
│   ├── 🧠 timetable_app.py  
│   │ Main Streamlit entrypoint that launches the timetable-to-ICS app.
│   │
│   ├── 📄 requirements.txt  
│   │ Clean list of only necessary packages.
│   │
│   ├── 📁 yolov8/  
│   │ Stores YOLOv8 model files (weights/configs) used for layout detection.
│   │
│   └── 📁 scripts/  
│       ├── extract_timetable.py – Full pipeline for PDF + OCR + JSON conversion  
│       ├── layout_detector.py – Handles YOLO layout prediction and fallback methods  
│       └── 📁 utils/  
│           ├── constants.py – Defines time slots, weeks, days, holidays  
│           ├── ocr_utils.py – Text cleaning and preprocessing for OCR  
│           └── ui_helpers.py – Time/date inputs and ICS export logic
│
├── 📄packages.txt 
│ Configuration for deployment to be installed - Have to be in your PATH
│
├── ▶️ run.bat  
│ One-click launcher for Windows (activates env + runs app)
│
├── ▶️ run.sh  
│ One-click launcher for macOS/Linux (source env + runs app)
│
└── 📘 README.md  
 The file you’re reading now ✨ includes setup, usage, and structure.
```
---

## 🛠️ Setup Instructions

### 1️⃣ Option A: Use pre-built environment (Windows)

If `timetable_env/` is included:

```bash
# Activate environment
timetable_env\Scripts\activate
```

Then launch:

```bash
run.bat
```

---

### 2️⃣ Option B: Create your own environment

```bash
# From project root
python -m venv timetable_env
timetable_env\Scripts\activate         # Windows
# or
source timetable_env/bin/activate        # macOS/Linux

# Install dependencies
pip install -r timetable_project/requirements.txt
```

Then launch the app:

```bash
cd timetable_project
streamlit run timetable_app.py
```

---

## 📤 How to Use the App

1. **Upload your timetable PDF**
2. Click **🧠 Extract Timetable**
3. Review and edit any fields:
   - Course code, group, location
   - Day and time (time picker)
   - Start date (can be inferred)
   - Holiday notes
4. Press **📥 Convert to ICS**
5. Click **⬇️ Download ICS File** to save it

---

## 🔁 Re-importing `.ics` files

If the calendar changes and you re-export:

- Most calendar apps (Google Calendar, Outlook) **do not auto-replace** old events
- It's recommended to **delete the old calendar or events** before re-importing
- Alternatively, import into a new calendar group each time

---

## 🛑 Important Notes

- **Closing the browser tab does not stop the app**
- You must close the terminal window or press `Ctrl+C` before closing the browser
- Streamlit keeps the server running in the background by design

---

## 📦 Optional: Launcher Scripts

### `run.bat` (Windows)

```bat
@echo off
call timetable_env\Scripts\activate
cd timetable_project
streamlit run timetable_app.py
pause
```

### `run.sh` (macOS/Linux)

```bash
#!/bin/bash
source timetable_env/bin/activate
cd timetable_project
streamlit run timetable_app.py
```

Make `run.sh` executable:

```bash
chmod +x run.sh
```
---

## 🧾 Sample Timetable Format

This app is designed to work with PDF timetables that follow a grid layout similar to the one below:

![Sample Timetable](./timetable_project/images/timetable_layout.png)

1. **Course Grids**
   - 🚫 *If a holiday clashes with a class, the holiday overrides the course block*
   - 🆔 Course Code (e.g., `EG0001`)
   - 🧑‍🤝‍🧑 Group (e.g., `G1`, `G3`)
   - 🏫 Location (e.g., `TR201`, `LT2`)

2. **Week Row**  
   Appears in each column cell, used to determine week repetition logic.

3. **Date Range Row**  
   Usually above the table, used to infer start dates.

4. **Time Slot Column**  
   Located on the far left — anchors the timetable’s grid structure.

🧠 Don’t worry — the app uses **YOLOv8 layout detection + OCR** to handle all this automatically.

---

## 🌐 Live Demo

[Demo Link](https://ysjsean-fyp-timetable-extraction.streamlit.app/)

---

## 📚 Acknowledgements

- YOLOv8 via Ultralytics
- Tesseract OCR
- Streamlit for interactive UI
- PDF2Image and OpenCV for preprocessing

---

## 📬 Author

Final Year Project  
Timetable Extraction to ICS Calendar Converter  
Developed by: **Sean Young Song Jie**  
School: **Nanyang Technological University**  
Matric Number: **U2122305F**  
Academic Year: **2024/2025**  
