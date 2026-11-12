"""Streamlit web app for the AI Practice Problem Generator.

Run locally:  streamlit run app.py
"""

import os

import streamlit as st

import practice_gen as pg

MAX_RUNS_PER_SESSION = 10

SAMPLE_PROBLEMS = [
    {"question": "Solve for x: 3x + 7 = 22",
     "answer": "x = 5",
     "explanation": "Subtract 7 from both sides to get 3x = 15, then divide by 3."},
    {"question": "Solve for x: 5x - 4 = 2x + 11",
     "answer": "x = 5",
     "explanation": "Subtract 2x from both sides (3x - 4 = 11), add 4 (3x = 15), divide by 3."},
    {"question": "A tutor charges $25 per hour plus a $10 booking fee. "
                 "A session cost $72.50. How many hours was it?",
     "answer": "2.5 hours",
     "explanation": "Set up 25h + 10 = 72.50. Subtract 10 to get 25h = 62.50, then divide by 25."},
]


def get_api_key():
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:  # no secrets file configured
        key = None
    return key or os.environ.get("ANTHROPIC_API_KEY")


st.set_page_config(page_title="AI Practice Problem Generator", page_icon="📝")
st.title("📝 AI Practice Problem Generator")
st.caption("Personalized math and coding worksheets for tutoring students, "
           "with difficulty that adapts to each student's last score. "
           "Built by Brody Gordon · [Source on GitHub](https://github.com/Brogor12/ai-practice-generator)")

api_key = get_api_key()
if not api_key:
    st.info("Demo mode: no API key is configured, so this shows a sample worksheet. "
            "The adaptive difficulty logic below still runs for real.")

with st.form("generate"):
    col1, col2 = st.columns(2)
    student = col1.text_input("Student name", value="Alex")
    subject = col2.selectbox("Subject", ["math", "coding"])
    topic = st.text_input("Topic", value="linear equations")
    count = st.slider("Number of problems", 1, 5, 3)

    st.markdown("**Adaptive difficulty**: enter the student's last score on this topic, "
                "or leave it at 0/0 for a new student.")
    c1, c2, c3 = st.columns(3)
    correct = c1.number_input("Correct", min_value=0, max_value=20, value=0)
    total = c2.number_input("Out of", min_value=0, max_value=20, value=0)
    last_level = c3.selectbox("Last difficulty", pg.DIFFICULTIES, index=1)
    submitted = st.form_submit_button("Generate worksheet")

if submitted:
    if not topic.strip():
        st.error("Enter a topic.")
        st.stop()
    if total and correct > total:
        st.error("Correct can't be more than the total.")
        st.stop()

    students = {}
    if total:
        pg.record_score(students, student, topic, f"{correct}/{total}", last_level)
    difficulty = pg.pick_difficulty(students, student, topic)
    if total:
        st.success(f"Last score {correct}/{total} at {last_level} → "
                   f"next worksheet is **{difficulty}**.")
    else:
        st.success(f"New student → starting at **{difficulty}**.")

    if api_key:
        runs = st.session_state.get("runs", 0)
        if runs >= MAX_RUNS_PER_SESSION:
            st.warning("Demo limit reached for this session. Refresh later to try again.")
            st.stop()
        st.session_state["runs"] = runs + 1
        prompt = pg.build_prompt(subject, topic, difficulty, count)
        with st.spinner("Writing problems..."):
            try:
                problems = pg.parse_problems(pg.call_claude(prompt, api_key=api_key))
            except (RuntimeError, ValueError) as e:
                st.error(f"Couldn't generate problems: {e}")
                st.stop()
    else:
        problems = SAMPLE_PROBLEMS[:count]

    worksheet = pg.render_worksheet(student, topic, difficulty, problems)
    answer_key = pg.render_answer_key(student, topic, problems)

    tab1, tab2 = st.tabs(["Worksheet", "Answer key"])
    with tab1:
        st.markdown(worksheet)
        st.download_button("Download worksheet", worksheet,
                           file_name=f"{student}-{topic}-worksheet.md")
    with tab2:
        st.markdown(answer_key)
        st.download_button("Download answer key", answer_key,
                           file_name=f"{student}-{topic}-answers.md")
