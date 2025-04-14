@echo off
echo 🔄 Activating virtual environment...
call timetable_env\Scripts\activate

echo 🚀 Launching Streamlit app...
cd timetable_project

streamlit run timetable_app.py
pause
