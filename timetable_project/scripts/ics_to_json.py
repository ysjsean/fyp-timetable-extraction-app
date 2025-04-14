# For troubleshooting if ICS is generated correctly

from ics import Calendar
from dateutil import tz
from datetime import timedelta
import pandas as pd

# Load your .ics file
with open("./timetable.ics", "r", encoding="utf-8") as f:
    cal = Calendar(f.read())

sgt = tz.gettz("Asia/Singapore")

events_list = []
for event in cal.events:
    dt_start = event.begin.datetime.astimezone(sgt)
    dt_end = event.end.datetime.astimezone(sgt)

    name = event.name.strip()
    course_code = name.split("(", 1)[0].strip()
    group = name.split("(")[1].replace(")", "").strip() if "(" in name else ""

    desc_lines = event.description.splitlines() if event.description else []
    weeks_line = next((line for line in desc_lines if line.lower().startswith("weeks")), "")
    note_line = next((line for line in desc_lines if "note" in line.lower()), "")
    weeks = [w.strip() for w in weeks_line.split(":", 1)[1].split(",")] if ":" in weeks_line else None
    note = note_line.split(":", 1)[1].strip() if ":" in note_line else None

    events_list.append({
        "date": dt_start.strftime("%Y-%m-%d"),
        "day": dt_start.strftime("%A"),
        "start": dt_start.strftime("%H:%M"),
        "end": dt_end.strftime("%H:%M"),
        "courseCode": course_code,
        "group": group,
        "location": event.location,
        "note": note,
        "weeks": ", ".join(weeks) if weeks else None
    })

# Create sorted DataFrame
df = pd.DataFrame(events_list)
df["datetime"] = pd.to_datetime(df["date"] + " " + df["start"])
df = df.sort_values(by=["datetime", "courseCode"]).drop(columns="datetime")

# Save to CSV or display
# df.to_csv("./timetable_sgt.csv", index=False)
print(df)
