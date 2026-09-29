import streamlit as st
import sqlite3
import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="AI Learning Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-4o-mini"
).strip()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

DATABASE = "database.db"


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

.main {
    padding-top: 1rem;
}

.hero {
    padding: 35px;
    border-radius: 20px;
    background: linear-gradient(135deg, #2563eb, #7c3aed);
    color: white;
    margin-bottom: 25px;
}

.hero h1 {
    font-size: 38px;
    margin-bottom: 10px;
}

.hero p {
    font-size: 17px;
}

.card {
    background: white;
    padding: 25px;
    border-radius: 18px;
    border: 1px solid #e5e7eb;
    margin-bottom: 20px;
}

.section-title {
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 5px;
}

.section-subtitle {
    color: #64748b;
    margin-bottom: 25px;
}

.result-box {
    background: #ffffff;
    border-left: 5px solid #2563eb;
    padding: 25px;
    border-radius: 12px;
    margin-top: 20px;
}

.metric-box {
    background: white;
    padding: 25px;
    text-align: center;
    border-radius: 16px;
    border: 1px solid #e5e7eb;
}

.metric-number {
    font-size: 32px;
    font-weight: 700;
    color: #2563eb;
}

.metric-label {
    color: #64748b;
}

.footer {
    text-align: center;
    color: #64748b;
    margin-top: 40px;
    padding: 20px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# DATABASE
# =========================================================

def get_connection():
    return sqlite3.connect(DATABASE)


def create_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            education TEXT,
            skills TEXT,
            career_goal TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            score INTEGER,
            total INTEGER,
            percentage REAL,
            date TEXT
        )
    """)

    conn.commit()
    conn.close()


create_database()


# =========================================================
# STUDENT DATABASE FUNCTIONS
# =========================================================

def save_student(name, education, skills, career_goal):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM student")

    cursor.execute("""
        INSERT INTO student
        (name, education, skills, career_goal)
        VALUES (?, ?, ?, ?)
    """, (
        name,
        education,
        skills,
        career_goal
    ))

    conn.commit()
    conn.close()


def get_student():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, education, skills, career_goal
        FROM student
        ORDER BY id DESC
        LIMIT 1
    """)

    student = cursor.fetchone()

    conn.close()

    return student


# =========================================================
# PROGRESS DATABASE FUNCTIONS
# =========================================================

def save_quiz_result(topic, score, total):

    percentage = 0

    if total > 0:
        percentage = round(
            (score / total) * 100,
            2
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO progress
        (topic, score, total, percentage, date)
        VALUES (?, ?, ?, ?, ?)
    """, (
        topic,
        score,
        total,
        percentage,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def get_progress():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT topic, score, total, percentage, date
        FROM progress
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


# =========================================================
# OPENROUTER AI FUNCTION
# =========================================================

def ask_ai(prompt):

    if not API_KEY:

        return None, (
            "OPENROUTER_API_KEY is missing. "
            "Please check your .env file."
        )

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "AI Personal Learning Assistant"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an AI Personal Learning Assistant "
                    "for BCA students. "
                    "Give simple, accurate and practical answers. "
                    "Use headings, bullet points and examples."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1500
    }

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:

            try:
                error_json = response.json()

                error_message = (
                    error_json
                    .get("error", {})
                    .get("message", response.text)
                )

            except Exception:

                error_message = response.text

            return None, (
                f"OpenRouter Error "
                f"{response.status_code}: "
                f"{error_message}"
            )

        data = response.json()

        if "choices" not in data:

            return None, (
                "The AI server returned an unexpected response."
            )

        answer = data["choices"][0]["message"]["content"]

        return answer, None

    except requests.exceptions.Timeout:

        return None, (
            "The AI request timed out. "
            "Please try again."
        )

    except requests.exceptions.ConnectionError:

        return None, (
            "Cannot connect to OpenRouter. "
            "Check your internet connection."
        )

    except Exception as e:

        return None, f"AI Error: {str(e)}"


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div style="text-align:center;">
            <div style="font-size:50px;">🤖</div>
            <h2>AI Learning Assistant</h2>
            <p>Personalized Learning Platform</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "👤 Student Profile",
            "🧠 Skill Gap Analysis",
            "📚 Study Plan",
            "📝 AI Quiz",
            "🤖 AI Tutor",
            "📊 Progress"
        ]
    )

    st.divider()

    st.caption("BCA Project")
    st.caption("Python + Streamlit + SQLite + OpenRouter")


# =========================================================
# GET STUDENT
# =========================================================

student = get_student()


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    st.markdown(
        """
        <div class="hero">
            <h1>Learn Smarter. Grow Faster. 🚀</h1>
            <p>
                AI-powered personal learning and skill gap assistant
                for students and future software developers.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-title">AI Personal Learning Assistant</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="section-subtitle">
        Discover your skill gaps, generate study plans,
        practice quizzes and learn with an AI tutor.
        </div>
        """,
        unsafe_allow_html=True
    )

    progress = get_progress()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(
            """
            <div class="metric-box">
                <div class="metric-number">👤</div>
                <div class="metric-label">Student Profile</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div class="metric-box">
                <div class="metric-number">🧠</div>
                <div class="metric-label">Skill Gap AI</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            """
            <div class="metric-box">
                <div class="metric-number">📚</div>
                <div class="metric-label">Study Planner</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:
        st.markdown(
            f"""
            <div class="metric-box">
                <div class="metric-number">{len(progress)}</div>
                <div class="metric-label">Quiz Attempts</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("### ✨ Features")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            """
            <div class="card">
                <h3>🧠 AI Skill Gap Analysis</h3>
                <p>
                Compare your current skills with your career goal
                and discover what you need to learn.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="card">
                <h3>📝 AI Quiz</h3>
                <p>
                Generate MCQ quizzes and track your performance.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            """
            <div class="card">
                <h3>📚 Personalized Study Plan</h3>
                <p>
                Generate a learning roadmap according to your
                career goal.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="card">
                <h3>🤖 AI Tutor</h3>
                <p>
                Ask programming and technical questions
                and receive simple explanations.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )


# =========================================================
# STUDENT PROFILE
# =========================================================

elif page == "👤 Student Profile":

    st.markdown(
        '<div class="section-title">Student Profile</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="section-subtitle">
        Enter your education, skills and career goal.
        </div>
        """,
        unsafe_allow_html=True
    )

    if student:

        old_name = student[0]
        old_education = student[1]
        old_skills = student[2]
        old_goal = student[3]

    else:

        old_name = ""
        old_education = ""
        old_skills = ""
        old_goal = ""

    with st.form("profile_form"):

        name = st.text_input(
            "Student Name",
            value=old_name,
            placeholder="Example: Anju"
        )

        education = st.text_input(
            "Education",
            value=old_education,
            placeholder="Example: BCA 4th Semester"
        )

        skills = st.text_area(
            "Current Skills",
            value=old_skills,
            placeholder="Example: Python, C, Java"
        )

        career_goal = st.text_input(
            "Career Goal",
            value=old_goal,
            placeholder="Example: Software Developer"
        )

        save = st.form_submit_button(
            "💾 Save Profile",
            use_container_width=True
        )

        if save:

            if not name.strip():

                st.error("Please enter your name.")

            elif not career_goal.strip():

                st.error("Please enter your career goal.")

            else:

                save_student(
                    name.strip(),
                    education.strip(),
                    skills.strip(),
                    career_goal.strip()
                )

                st.success(
                    "✅ Student profile saved successfully!"
                )

                st.rerun()


# =========================================================
# SKILL GAP ANALYSIS
# =========================================================

elif page == "🧠 Skill Gap Analysis":

    st.markdown(
        '<div class="section-title">AI Skill Gap Analysis</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="section-subtitle">
        Discover the skills you need to reach your career goal.
        </div>
        """,
        unsafe_allow_html=True
    )

    if not student:

        st.warning(
            "Please complete your Student Profile first."
        )

    else:

        st.info(
            f"Current Skills: {student[2]}  |  "
            f"Career Goal: {student[3]}"
        )

        if st.button(
            "🧠 Analyze My Skills",
            type="primary",
            use_container_width=True
        ):

            prompt = f"""
Analyze this student's skill gap.

Student Name: {student[0]}
Education: {student[1]}
Current Skills: {student[2]}
Career Goal: {student[3]}

Give the following sections:

1. Current Skills
2. Strengths
3. Missing Skills
4. Skill Gaps
5. Recommended Technologies
6. Recommended Learning Topics
7. Suggested Projects
8. Career Preparation Tips

Keep the answer simple and suitable for a BCA student.
"""

            with st.spinner(
                "🤖 AI is analyzing your skills..."
            ):

                answer, error = ask_ai(prompt)

            if error:

                st.error(error)

            else:

                st.markdown(
                    '<div class="result-box">',
                    unsafe_allow_html=True
                )

                st.markdown(answer)

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )


# =========================================================
# STUDY PLAN
# =========================================================

elif page == "📚 Study Plan":

    st.markdown(
        '<div class="section-title">Personalized Study Plan</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="section-subtitle">
        Get a learning roadmap based on your skills and career goal.
        </div>
        """,
        unsafe_allow_html=True
    )

    if not student:

        st.warning(
            "Please complete your Student Profile first."
        )

    else:

        days = st.selectbox(
            "📅 Number of Days",
            [7, 14, 21, 30]
        )

        if st.button(
            "📚 Generate Study Plan",
            type="primary",
            use_container_width=True
        ):

            prompt = f"""
Create a personalized {days}-day study plan.

Student:
{student[0]}

Education:
{student[1]}

Current Skills:
{student[2]}

Career Goal:
{student[3]}

For every day include:

Day number
Topic
What to learn
Practical activity
Expected outcome

The plan should start from basic concepts
and gradually move towards practical projects.

Use simple English.
"""

            with st.spinner(
                "📚 Creating your study plan..."
            ):

                answer, error = ask_ai(prompt)

            if error:

                st.error(error)

            else:

                st.markdown(
                    '<div class="result-box">',
                    unsafe_allow_html=True
                )

                st.markdown(answer)

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )


# =========================================================
# AI QUIZ
# =========================================================

elif page == "📝 AI Quiz":

    st.markdown(
        '<div class="section-title">AI Quiz</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="section-subtitle">
        Generate a 5-question technical quiz.
        </div>
        """,
        unsafe_allow_html=True
    )

    topic = st.text_input(
        "Quiz Topic",
        placeholder="Example: Python Lists"
    )

    if st.button(
        "📝 Generate Quiz",
        type="primary",
        use_container_width=True
    ):

        if not topic.strip():

            st.warning(
                "Please enter a quiz topic."
            )

        else:

            prompt = f"""
Create exactly 5 multiple-choice questions about:

{topic}

Return ONLY valid JSON.

Use this exact format:

[
  {{
    "question": "Question",
    "options": [
      "Option A",
      "Option B",
      "Option C",
      "Option D"
    ],
    "answer": "Option A"
  }}
]

The answer must exactly match one of the options.
Do not include markdown.
"""

            with st.spinner(
                "📝 Generating quiz..."
            ):

                answer, error = ask_ai(prompt)

            if error:

                st.error(error)

            else:

                try:

                    clean_answer = answer.strip()

                    if clean_answer.startswith("```"):

                        clean_answer = clean_answer.replace(
                            "```json",
                            ""
                        )

                        clean_answer = clean_answer.replace(
                            "```",
                            ""
                        )

                    quiz = json.loads(
                        clean_answer.strip()
                    )

                    if len(quiz) != 5:

                        st.error(
                            "AI did not generate exactly 5 questions."
                        )

                    else:

                        st.session_state.quiz = quiz
                        st.session_state.quiz_topic = topic

                        st.success(
                            "✅ Quiz generated successfully!"
                        )

                except Exception as e:

                    st.error(
                        f"Could not read the AI quiz: {e}"
                    )

    if "quiz" in st.session_state:

        quiz = st.session_state.quiz

        st.markdown("### 🎯 Answer the Questions")

        selected_answers = {}

        for i, question in enumerate(quiz):

            st.markdown(
                f"#### Question {i + 1}"
            )

            st.write(
                question["question"]
            )

            selected_answers[i] = st.radio(
                "Select answer:",
                question["options"],
                key=f"quiz_{i}"
            )

        if st.button(
            "✅ Submit Quiz",
            type="primary",
            use_container_width=True
        ):

            score = 0

            for i, question in enumerate(quiz):

                if (
                    selected_answers[i]
                    == question["answer"]
                ):

                    score += 1

            total = len(quiz)

            percentage = round(
                (score / total) * 100
            )

            st.success(
                f"🎉 Your Score: {score}/{total} "
                f"({percentage}%)"
            )

            save_quiz_result(
                st.session_state.quiz_topic,
                score,
                total
            )


# =========================================================
# AI TUTOR
# =========================================================

elif page == "🤖 AI Tutor":

    st.markdown(
        '<div class="section-title">AI Tutor</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="section-subtitle">
        Ask questions about programming and technology.
        </div>
        """,
        unsafe_allow_html=True
    )

    level = st.selectbox(
        "Your Level",
        [
            "Beginner",
            "Intermediate",
            "Advanced"
        ]
    )

    question = st.text_area(
        "Your Question",
        placeholder=(
            "Example: Explain Python list "
            "with a simple example."
        )
    )

    if st.button(
        "🤖 Ask AI Tutor",
        type="primary",
        use_container_width=True
    ):

        if not question.strip():

            st.warning(
                "Please enter your question."
            )

        else:

            prompt = f"""
You are an AI tutor.

Student Level:
{level}

Question:
{question}

Explain using:

1. Definition
2. Simple explanation
3. Example
4. Important points

Use simple English.
"""

            with st.spinner(
                "🤖 AI Tutor is preparing the answer..."
            ):

                answer, error = ask_ai(prompt)

            if error:

                st.error(error)

            else:

                st.markdown(
                    '<div class="result-box">',
                    unsafe_allow_html=True
                )

                st.markdown(answer)

                st.markdown(
                    '</div>',
                    unsafe_allow_html=True
                )


# =========================================================
# PROGRESS
# =========================================================

elif page == "📊 Progress":

    st.markdown(
        '<div class="section-title">Learning Progress</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="section-subtitle">
        Track your AI quiz performance.
        </div>
        """,
        unsafe_allow_html=True
    )

    rows = get_progress()

    if not rows:

        st.info(
            "No quiz attempts yet."
        )

    else:

        total_attempts = len(rows)

        average = round(
            sum(row[3] for row in rows)
            / total_attempts
        )

        best = max(
            row[3] for row in rows
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Quiz Attempts",
                total_attempts
            )

        with col2:

            st.metric(
                "Average Score",
                f"{average}%"
            )

        with col3:

            st.metric(
                "Best Score",
                f"{best}%"
            )

        st.markdown("### 📈 Quiz History")

        for row in rows:

            st.markdown(
                f"""
                <div class="card">
                    <h4>📚 {row[0]}</h4>
                    <p>
                    Score: <b>{row[1]}/{row[2]}</b>
                    </p>
                    <p>
                    Percentage: <b>{row[3]}%</b>
                    </p>
                    <p>
                    Date: {row[4]}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">
        🤖 AI Personal Learning & Skill Gap Assistant
        <br>
        Built with Python • Streamlit • SQLite • OpenRouter
    </div>
    """,
    unsafe_allow_html=True
)