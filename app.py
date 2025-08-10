import re
from datetime import datetime
import math

import streamlit as st
import pandas as pd

def parse_plain_text_schedule(text: str):
    tasks = []
    if not text:
        return tasks

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    time_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*(h|hr|hour|hours)", re.IGNORECASE)
    date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")

    for line in lines:
        hours = None
        date = None

        m = time_pattern.search(line)
        if m:
            try:
                hours = float(m.group(1))
            except Exception:
                hours = None

        d = date_pattern.search(line)
        if d:
            try:
                date = datetime.strptime(d.group(1), "%Y-%m-%d")
            except Exception:
                date = None

        task_text = re.sub(time_pattern, '', line)
        task_text = re.sub(date_pattern, '', task_text)
        task_text = task_text.strip(' -:')

        tasks.append({'date': date, 'task': task_text, 'hours': hours})

    return tasks

def compute_average_available_hours(tasks):
    hours_list = [t['hours'] for t in tasks if t.get('hours') is not None]

    if hours_list:
        avg_busy = sum(hours_list) / len(hours_list)
        baseline = 15.0
        avg_available = max(0.5, baseline - avg_busy)
        return avg_available
    else:
        return 2.0

def infer_required_hours_from_goal(goal_text: str):
    g = goal_text.lower()
    if any(k in g for k in ['basic', 'intro', 'get started']):
        return 30.0
    if any(k in g for k in ['learn', 'python', 'javascript', 'html', 'css']):
        return 60.0
    if any(k in g for k in ['project', 'build', 'app', 'website']):
        return 120.0
    if any(k in g for k in ['cert', 'exam', 'prepare']):
        return 80.0
    return 50.0

def estimate_days(required_hours: float, available_hours_per_day: float, mode: str):
    if available_hours_per_day <= 0:
        return float('inf'), {'reason': 'No available hours'}

    mode_factors = {'basic': 1.5, 'pro': 1.15, 'advanced': 1.02}
    factor = mode_factors.get(mode, 1.15)

    adjusted_hours = required_hours * factor
    days = adjusted_hours / available_hours_per_day

    breakdown = {
        'required_hours': required_hours,
        'factor': factor,
        'adjusted_hours': adjusted_hours,
        'available_hours_per_day': available_hours_per_day,
        'estimated_days': days,
    }
    return days, breakdown

st.set_page_config(page_title='Simple Schedule Estimator', layout='centered')
st.title('Simple Schedule Estimator (Beginner)')

st.write('Upload a schedule (CSV) or paste a list of tasks. Then enter your goal and click Estimate.')

uploaded_file = st.file_uploader('Upload CSV schedule (optional)', type=['csv'])
raw_text = st.text_area('Or paste schedule here (one task per line). Examples:\n2025-08-10 - Project work - 3 hours\nRead book - 1.5h', height=150)

goal_text = st.text_input('What is your goal? (e.g. Learn basic Python)')
use_infer = st.checkbox('Let the app guess how many hours the goal needs (recommended)', value=True)
manual_hours = st.number_input('If you know required effort (hours), enter here', min_value=0.0, value=0.0)

mode = st.selectbox('Profile', ['basic', 'pro', 'advanced'])

if st.button('Estimate'):
    parsed_tasks = []

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if 'task' in df.columns and 'hours' in df.columns:
                for _, r in df.iterrows():
                    parsed_tasks.append({'date': None, 'task': str(r['task']), 'hours': float(r['hours']) if pd.notna(r['hours']) else None})
            else:
                for _, r in df.iterrows():
                    parsed_tasks.append({'date': None, 'task': ' | '.join([str(x) for x in r.values]), 'hours': None})
        except Exception as e:
            st.error('Failed to read CSV: ' + str(e))
            parsed_tasks = []

    if raw_text.strip():
        parsed_tasks = parse_plain_text_schedule(raw_text)

    if not parsed_tasks:
        st.warning('No tasks detected. Paste some tasks or upload a CSV with tasks.')
    else:
        st.subheader('Parsed tasks (preview)')
        st.table(pd.DataFrame(parsed_tasks))

        if use_infer or manual_hours <= 0:
            required_hours = infer_required_hours_from_goal(goal_text if goal_text else '')
            st.write(f"Inferred required hours for goal: {required_hours} hours")
        else:
            required_hours = manual_hours
            st.write(f"Using your provided required hours: {required_hours} hours")

        avg_avail = compute_average_available_hours(parsed_tasks)
        st.write(f"Estimated available hours per day (based on your schedule): {avg_avail:.1f} hours")

        est_days, breakdown = estimate_days(required_hours, avg_avail, mode)
        st.subheader('Result')
        st.write(f"Mode: **{mode}**")
        st.write(f"Estimated days (rounded up): **{math.ceil(est_days)}** days")
        st.json(breakdown)

        st.markdown('**Suggestions**')
        st.write('- If you increase daily focused time, the total days go down proportionally.')
        weeks = max(1, math.ceil(est_days / 7))
        st.write(f'- Weekly plan suggestion: split the work into {weeks} weeks, ~{required_hours/weeks:.1f} hours per week.')

st.markdown('---')
st.subheader('Search your schedule (simple)')
search_query = st.text_input('Find tasks that contain (e.g. "project", "read")')
if st.button('Search') and search_query.strip():
    try:
        parsed_tasks
    except NameError:
        parsed_tasks = parse_plain_text_schedule(raw_text)

    results = [t for t in parsed_tasks if search_query.lower() in t['task'].lower()]
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.info('No matching tasks found.')

st.markdown('---')
st.markdown('''
**Notes:**
- This simple app is made without LangChain or an LLM so you can run it without an API key.''')

