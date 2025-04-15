# scripts/utils/ui_helpers.py

from datetime import datetime, timedelta, date
import streamlit as st
from ics import Calendar, Event
from ics.grammar.parse import ContentLine
import pytz
import logging
from datetime import datetime, timedelta
from scripts.utils.constants import DAYS, WEEKS

def red_alert(text):
    st.markdown(f'<div style="color: red; font-weight: bold;">⚠️ {text}</div>', unsafe_allow_html=True)

def log_error(e):
    logging.error("Exception occurred", exc_info=e)
    st.error("🚨 Something went wrong. Please try another file or refresh.")
    st.exception(e)
    st.stop()

def timezone_converter(date, zone):
    timezone = pytz.timezone(zone)
    return timezone.localize(date)

def get_week_index(w):
    return WEEKS.index(w) if w in WEEKS else -1

def extract_semester_year(courses):
    for c in courses:
        raw = str(c.get("startDate", "")).strip()
        try:
            dt = datetime.strptime(raw, "%d %b %y")
            return dt.year
        except:
            continue
    return datetime.today().year

def get_inferred_start_date(course, all_courses):
    """
    Infer course startDate based on other block with:
    - Same day, any week → adjust by week index diff
    - Same week, different day → adjust by weekday diff
    Skips if both week and day are different.
    """
    def day_index(day_name):
        try:
            return DAYS.index(day_name)
        except:
            return -1

    raw = str(course.get("startDate", "")).strip().upper()
    if raw and raw != "UNKNOWN":
        try:
            datetime.strptime(raw, "%d %b %y")
            return None, None  # already valid
        except:
            pass

    try:
        course_weeks = [w for w in course.get("weeks", []) if w in WEEKS]
        course_week = course_weeks[0] if course_weeks else None
    except:
        course_week = None

    course_day = course.get("day")

    for other in all_courses:
        if other["id"] == course["id"]:
            continue

        other_day = other.get("day")
        other_weeks = [w for w in other.get("weeks", []) if w in WEEKS]
        other_week = other_weeks[0] if other_weeks else None

        try:
            known_raw = str(other.get("startDate", "")).strip()
            known_date = datetime.strptime(known_raw, "%d %b %y").date()
        except:
            continue

        # Same week, different day
        if course_week == other_week and course_day != other_day:
            d_diff = day_index(course_day) - day_index(other_day)
            return known_date + timedelta(days=d_diff), other

        # Same day, different week
        if course_day == other_day and course_week != other_week:
            w_diff = get_week_index(course_week) - get_week_index(other_week)
            return known_date + timedelta(weeks=w_diff), other

        # Exact match
        if course_day == other_day and course_week == other_week:
            return known_date, other

    return None, None  # Nothing found



def render_date_input(c1, course, all_courses):
    """
    Display a date_input with safe update logic:
    - Automatically assigns inferred dates
    - Shows red alerts for missing or inferred values
    - Only updates if the user actually changes the date
    """
    from scripts.utils.ui_helpers import get_inferred_start_date, extract_semester_year, red_alert
    from datetime import datetime, date

    raw = str(course.get("startDate", "")).strip()
    parsed_date = None
    inferred_note = ""
    inferred_flag = False

    # Try to parse the course startDate
    if raw and raw.upper() != "UNKNOWN":
        try:
            parsed_date = datetime.strptime(raw, "%d %b %y").date()
        except:
            parsed_date = None
    elif isinstance(course.get("startDate"), date):
        parsed_date = course["startDate"]

    # If not valid, try to infer
    if not parsed_date:
        inferred_date, inferred_from = get_inferred_start_date(course, all_courses)
        if inferred_date:
            parsed_date = inferred_date
            course["startDate"] = inferred_date  # ✅ Save it directly
            inferred_flag = True
            inferred_note = f" (inferred from {inferred_from.get('courseCode', 'another block')})"
        else:
            course["startDate"] = "UNKNOWN"

    # Label setup
    label = "Start Date *"
    if course["startDate"] == "UNKNOWN":
        label += " (⚠️ not selected)"
    elif inferred_flag:
        label += inferred_note

    # Fallback year for dummy UI value
    fallback_year = parsed_date.year if parsed_date else extract_semester_year(all_courses)
    shown_date = parsed_date or date(fallback_year, 1, 1)

    # Render the widget
    picked_date = c1.date_input(
        label,
        value=shown_date,
        key=f"sd_{course['id']}",
        format="DD/MM/YYYY"
    )

    # Save if the user manually changed it
    if parsed_date is None or picked_date != parsed_date:
        course["startDate"] = picked_date

    # Show red alert if missing or inferred
    if course["startDate"] == "UNKNOWN":
        red_alert("❗ Start date is missing. Please select a valid date before exporting.")
    elif inferred_flag:
        red_alert(f"⚠️ This date was inferred from {inferred_from.get('courseCode', 'another course')}. Please confirm it is correct.")

    return course






def render_time_inputs(st, course):
    """
    Render time inputs for start and end. Validates order and limits to 08:30–22:30.
    Returns (updated_course, error_message).
    """
    # Allowed range
    MIN_TIME = datetime.strptime("08:30", "%H:%M").time()
    MAX_TIME = datetime.strptime("22:30", "%H:%M").time()

    # Parse or default
    try:
        start_raw, end_raw = course["time"].split("-")
        start_dt = datetime.strptime(start_raw, "%H%M").time()
        end_dt = datetime.strptime(end_raw, "%H%M").time()
    except:
        start_dt = MIN_TIME
        end_dt = datetime.strptime("09:00", "%H:%M").time()

    # Show inputs
    time_cols = st.columns([1, 1])
    start_time = time_cols[0].time_input("Start Time", value=start_dt, step=timedelta(minutes=30), key=f"start_{course['id']}")
    end_time = time_cols[1].time_input("End Time", value=end_dt, step=timedelta(minutes=30), key=f"end_{course['id']}")

    # Validate inputs
    if start_time >= end_time:
        return course, "⚠️ End time must be after start time."
    if start_time < MIN_TIME or end_time > MAX_TIME:
        return course, "⚠️ Time must be between 08:30 and 22:30."

    # Store formatted string
    course["time"] = f"{start_time.strftime('%H%M')}-{end_time.strftime('%H%M')}"
    return course, None



def split_weeks_into_blocks(weeks):
    blocks = []
    current = []
    prev_index = None

    for w in weeks:
        if w == "Recess":
            if current:
                blocks.append(current)
                current = []
            prev_index = None
            continue

        idx = get_week_index(w)
        if prev_index is not None and idx != prev_index + 1:
            blocks.append(current)
            current = []
        current.append(w)
        prev_index = idx

    if current:
        blocks.append(current)

    return blocks

def generate_ics_from_courses(courses):
    cal = Calendar()
    timezone = "Asia/Singapore"
    errors = []
    all_events = []

    for idx, entry in enumerate(courses):
        try:
            raw_date = entry.get("startDate")
            if isinstance(raw_date, str):
                if raw_date.upper() == "UNKNOWN":
                    raise ValueError("Missing startDate")
                start_date = datetime.strptime(raw_date, "%d %b %y").date()
            elif isinstance(raw_date, date):
                start_date = raw_date
            else:
                raise ValueError("Invalid startDate type")

            start_str, end_str = entry["time"].split("-")
            start_h, start_m = int(start_str[:2]), int(start_str[2:])
            end_h, end_m = int(end_str[:2]), int(end_str[2:])

            course_weeks = entry["weeks"]
            all_blocks = split_weeks_into_blocks(course_weeks)

            course_first_week = course_weeks[0]
            course_first_week_index = get_week_index(course_first_week)

            for block in all_blocks:
                block_first_week = block[0]
                block_week_index = get_week_index(block_first_week)
                week_diff = block_week_index - course_first_week_index

                # ✅ Adjust only by week_diff to preserve original weekday
                session_date = start_date + timedelta(weeks=week_diff)

                dt_start = timezone_converter(datetime(session_date.year, session_date.month, session_date.day, start_h, start_m), timezone)
                dt_end = timezone_converter(datetime(session_date.year, session_date.month, session_date.day, end_h, end_m), timezone)

                e = Event()
                e.name = f"{entry['courseCode']} ({entry['group']})"
                e.location = entry["location"]
                e.begin = dt_start
                e.end = dt_end
                e.description = f"Weeks: {', '.join(block)}"
                if entry.get("note"):
                    e.description += f"\nNote: {entry['note']}"

                # RRULE: recurrence per week block
                e.rrule = {"FREQ": "WEEKLY", "COUNT": len(block)}
                e.extra.append(ContentLine(name="RRULE", value=f"FREQ=WEEKLY;COUNT={len(block)}"))

                all_events.append(e)

        except Exception as e:
            errors.append(f"Error in Course {idx + 1}: {e}")

    # Sort by time and course
    all_events.sort(key=lambda e: (e.begin.datetime, e.name))
    for e in all_events:
        cal.events.add(e)

    return cal, errors


