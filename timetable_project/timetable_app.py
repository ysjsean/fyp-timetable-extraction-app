import streamlit as st
import tempfile
import uuid
from ultralytics import __version__ as yolo_version
from datetime import datetime

from scripts.utils.constants import DAYS, WEEKS
from scripts.utils.ui_helpers import render_time_inputs, render_date_input, generate_ics_from_courses, log_error, timezone_converter


# To fix 2 issues:
# 1) torch.classes raised:
#     Traceback (most recent call last):
#     File "D:\NTU\FYP\timetable_env\Lib\site-packages\streamlit\web\bootstrap.py", line 347, in run
#         if asyncio.get_running_loop().is_running():
#         ^^^^^^^^^^^^^^^^^^^^^^^^^^
#     RuntimeError: no running event loop
# 2) RuntimeError: Tried to instantiate class '__path__._path', but it does not exist! Ensure that it is registered via torch::class_
import torch
torch.classes.__path__ = []

st.set_page_config(page_title="Timetable to ICS", layout="wide")
st.title("📅 Timetable → ICS Converter")

st.markdown("""
Upload your university timetable **PDF**, extract the schedule, review/edit all fields, and download as an `.ics` calendar file.

ℹ️ **startDate** may be inferred automatically from other course blocks with matching week/day.
""")

REQUIRED_FIELDS = ["courseCode", "group", "location", "weeks", "day", "time", "startDate"]
FIELD_LABELS = {
    "courseCode": "Course Code",
    "group": "Group",
    "location": "Location",
    "weeks": "Weeks",
    "day": "Day",
    "time": "Time",
    "startDate": "Start Date"
}

uploaded_pdf = st.file_uploader("📤 Upload Timetable PDF", type=["pdf"])

if uploaded_pdf and st.button("🧠 Extract Timetable"):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_pdf.read())
        tmp_path = tmp.name

    with st.spinner("Extracting timetable from PDF..."):
        try:
            from scripts.extract_timetable import extract_timetable
            extracted = extract_timetable(tmp_path)
            
            for c in extracted:
                c["id"] = str(uuid.uuid4())
            st.session_state.courses = extracted

        except Exception as e:
            log_error(e)

if "courses" not in st.session_state:
    st.session_state.courses = []

if st.button("➕ Add New Course"):
    st.session_state.courses.append({
        "id": str(uuid.uuid4()),
        "courseCode": "",
        "group": "",
        "location": "",
        "weeks": [],
        "day": "Monday",
        "time": "",
        "startDate": "",
        "note": ""
    })

invalid_count = sum(
    any(not c.get(f) for f in REQUIRED_FIELDS)
    for c in st.session_state.courses
)
if invalid_count > 0:
    st.error(f"⚠️ {invalid_count} course block(s) are missing required fields. Please review them before downloading.")

updated_courses = []
st.markdown("### ✏️ Review and Edit Each Course Block")

for idx, course in enumerate(st.session_state.courses):
    with st.expander(f"Course {idx+1}: {course.get('courseCode', '') or 'New Entry'}", expanded=True):
        missing_fields = [f for f in REQUIRED_FIELDS if not course.get(f)]
        if missing_fields:
            readable = [FIELD_LABELS[f] for f in missing_fields]
            st.warning(f"⚠️ Missing required fields: {', '.join(readable)}")

        cols = st.columns([1, 1, 1, 1])
        course["courseCode"] = cols[0].text_input("Course Code *", course["courseCode"], key=f"code_{course['id']}")
        course["group"] = cols[1].text_input("Group *", course["group"], key=f"group_{course['id']}")
        course["location"] = cols[2].text_input("Location *", course["location"], key=f"loc_{course['id']}")
        course["day"] = cols[3].selectbox("Day *", DAYS, index=DAYS.index(course["day"]), key=f"day_{course['id']}")

        course["weeks"] = st.multiselect("Weeks *", WEEKS, default=course["weeks"], key=f"weeks_{course['id']}")

        # Structured time input
        course, time_error = render_time_inputs(st, course)
        if time_error:
            st.error(time_error)

        # Inferred + formatted date input
        c1, c2 = st.columns([1, 3])
        course = render_date_input(c1, course, st.session_state.courses)
        c2.markdown("""
                    🛈 Should be the **first occurance** date for the course
                    
                    🛈 Date format DD/MM/YYYY
                    """)

        course["note"] = st.text_area("Note (optional)", course["note"], key=f"note_{course['id']}")

        delete_btn_name = f"❌ Delete Course {course['courseCode']} ({course['group']})" if (course['courseCode'] != "" and course['group'] != "") else f"❌ Delete New Course {idx+1}"
        if st.button(delete_btn_name, key=f"delete_{course['id']}"):
            continue

        updated_courses.append(course)

st.session_state.courses = updated_courses

# === ICS Export ===
if st.button("📥 Convert to ICS"):
    cal, errors = generate_ics_from_courses(st.session_state.courses)

    if errors:
        for err in errors:
            st.error(err)
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ics", mode="w", encoding="utf-8") as f:
            f.writelines(cal)
            f.flush()
            tmp_path = f.name

        with open(tmp_path, "rb") as f:
            st.download_button("⬇️ Download ICS File", f, file_name="timetable.ics", mime="text/calendar")

with st.expander("🛠 Developer Debug Info", expanded=False):
    st.caption("This section helps debug upload and extraction issues.")
    st.text(f"PDF uploaded: {uploaded_pdf.name if uploaded_pdf else 'None'}")
    st.text(f"YOLOv8 model version: {yolo_version}")
    st.text(f"Streamlit version: {st.__version__}")
    st.text("Extracted at:", timezone_converter(datetime.now().strftime('%d %b %y %H:%M:%S'), "Asia/Singapore"))