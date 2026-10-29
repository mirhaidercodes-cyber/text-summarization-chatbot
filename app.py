import re
import math
from collections import Counter
from datetime import datetime

import streamlit as st
from supabase import create_client


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Text Summarization Chatbot",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# DATABASE CONNECTION
# --------------------------------------------------

@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


try:
    supabase = get_supabase()
except Exception:
    st.error(
        "Unable to connect to the database. "
        "Please check the application's configuration."
    )
    st.stop()


# --------------------------------------------------
# SESSION MANAGEMENT
# --------------------------------------------------

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

if "user" not in st.session_state:
    st.session_state.user = None

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

if "generated_summary" not in st.session_state:
    st.session_state.generated_summary = None


def restore_session():
    if not st.session_state.access_token:
        return False

    try:
        response = supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )

        user = response.user

        if user:
            st.session_state.user = user
            st.session_state.access_token = (
                response.session.access_token
            )
            st.session_state.refresh_token = (
                response.session.refresh_token
            )
            return True

    except Exception:
        try:
            response = supabase.auth.refresh_session(
                st.session_state.refresh_token
            )

            if response.session and response.user:
                st.session_state.access_token = (
                    response.session.access_token
                )
                st.session_state.refresh_token = (
                    response.session.refresh_token
                )
                st.session_state.user = response.user
                return True

        except Exception:
            pass

    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user = None
    return False


def logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.access_token = None
    st.session_state.refresh_token = None
    st.session_state.user = None
    st.session_state.generated_summary = None
    st.session_state.page = "Dashboard"


def save_session(response):
    if response.session and response.user:
        st.session_state.access_token = (
            response.session.access_token
        )
        st.session_state.refresh_token = (
            response.session.refresh_token
        )
        st.session_state.user = response.user


# --------------------------------------------------
# SUMMARIZATION ALGORITHM
# --------------------------------------------------

STOPWORDS = set("""
a an the and or but if while with to of in on for from by is are
was were be been being it this that these those as at after before
into about over under between through during can could should would
will may might do does did have has had not no so than then very
also
""".split())


def split_sentences(text):
    text = re.sub(r"\s+", " ", text.strip())

    return [
        sentence.strip()
        for sentence in re.split(
            r"(?<=[.!?])\s+", text
        )
        if sentence.strip()
    ]


def summarize_text(text, length):
    sentences = split_sentences(text)

    if not sentences:
        return "Please enter some text."

    if len(sentences) <= 2:
        return " ".join(sentences)

    words = re.findall(
        r"\b[a-zA-Z]+\b", text.lower()
    )

    useful_words = [
        word for word in words
        if word not in STOPWORDS and len(word) > 2
    ]

    frequencies = Counter(useful_words)

    if not frequencies:
        return " ".join(sentences[:2])

    maximum = max(frequencies.values())

    frequencies = {
        word: count / maximum
        for word, count in frequencies.items()
    }

    scores = []

    for sentence in sentences:
        sentence_words = re.findall(
            r"\b[a-zA-Z]+\b",
            sentence.lower()
        )

        important = [
            word for word in sentence_words
            if word not in STOPWORDS and len(word) > 2
        ]

        score = (
            sum(
                frequencies.get(word, 0)
                for word in important
            ) / math.sqrt(len(important))
            if important else 0
        )

        scores.append(score)

    if length == "Short":
        count = max(
            1, math.ceil(len(sentences) * 0.25)
        )
    elif length == "Detailed":
        count = max(
            1, math.ceil(len(sentences) * 0.65)
        )
    else:
        count = max(
            1, math.ceil(len(sentences) * 0.40)
        )

    count = min(count, len(sentences))

    chosen = sorted(
        range(len(sentences)),
        key=lambda index: scores[index],
        reverse=True
    )[:count]

    chosen.sort()

    return " ".join(
        sentences[index] for index in chosen
    )


# --------------------------------------------------
# AUTHENTICATION PAGE
# --------------------------------------------------

def authentication_page():
    st.markdown(
        """
        <div style="text-align:center; padding:30px 0 15px 0;">
            <h1>Text Summarization Chatbot</h1>
            <p style="font-size:17px;">
                Turn lengthy text into clear, meaningful summaries.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    left, center, right = st.columns([1, 1.2, 1])

    with center:
        tab_login, tab_register = st.tabs(
            ["Login", "Create Account"]
        )

        with tab_login:
            st.subheader("Welcome back")

            with st.form("login_form"):
                email = st.text_input(
                    "Email address",
                    placeholder="you@example.com"
                )

                password = st.text_input(
                    "Password",
                    type="password"
                )

                submitted = st.form_submit_button(
                    "Login",
                    type="primary",
                    use_container_width=True
                )

            if submitted:
                if not email.strip() or not password:
                    st.warning(
                        "Enter your email and password."
                    )
                else:
                    try:
                        response = (
                            supabase.auth.sign_in_with_password(
                                {
                                    "email": email.strip(),
                                    "password": password
                                }
                            )
                        )

                        save_session(response)

                        if st.session_state.user:
                            st.session_state.page = "Dashboard"
                            st.rerun()
                        else:
                            st.error(
                                "Login could not be completed."
                            )

                    except Exception:
                        st.error(
                            "Login failed. Check your credentials "
                            "and whether email verification is required."
                        )

        with tab_register:
            st.subheader("Create your account")

            with st.form("register_form"):
                name = st.text_input(
                    "Full name",
                    placeholder="Enter your name"
                )

                email = st.text_input(
                    "Email address",
                    key="register_email",
                    placeholder="you@example.com"
                )

                password = st.text_input(
                    "Password",
                    type="password",
                    key="register_password",
                    help="Use a strong password."
                )

                confirm_password = st.text_input(
                    "Confirm password",
                    type="password"
                )

                submitted = st.form_submit_button(
                    "Register",
                    type="primary",
                    use_container_width=True
                )

            if submitted:
                if not name.strip() or not email.strip():
                    st.warning(
                        "Please complete all fields."
                    )

                elif len(password) < 8:
                    st.warning(
                        "Your password must contain at least 8 characters."
                    )

                elif password != confirm_password:
                    st.warning(
                        "The passwords do not match."
                    )

                else:
                    try:
                        response = supabase.auth.sign_up(
                            {
                                "email": email.strip(),
                                "password": password,
                                "options": {
                                    "data": {
                                        "full_name": name.strip()
                                    }
                                }
                            }
                        )

                        if response.session and response.user:
                            save_session(response)
                            st.session_state.page = "Dashboard"
                            st.success(
                                "Account created successfully."
                            )
                            st.rerun()

                        else:
                            st.success(
                                "Registration received. If email "
                                "verification is enabled, check your "
                                "inbox before logging in."
                            )

                    except Exception as e:
                        st.error(f"Registration error: {e}")

    st.divider()

    st.caption(
        "Artificial Intelligence ABL Project | "
        "Extractive text summarization using Python"
    )


# --------------------------------------------------
# SAVE AND LOAD USER HISTORY
# --------------------------------------------------

def save_summary(original, summary, length):
    try:
        supabase.table("summaries").insert(
            {
                "user_id": st.session_state.user.id,
                "original_text": original,
                "summary_text": summary,
                "summary_length": length
            }
        ).execute()

        return True

    except Exception:
        st.error(
            "The summary was generated, but could not be saved. "
            "Please check your database connection and permissions."
        )
        return False


def load_history():
    response = (
        supabase.table("summaries")
        .select(
            "id, original_text, summary_text, "
            "summary_length, created_at"
        )
        .eq("user_id", st.session_state.user.id)
        .order("created_at", desc=True)
        .execute()
    )

    return response.data or []


# --------------------------------------------------
# APPLICATION DASHBOARD
# --------------------------------------------------

def dashboard_page():
    user = st.session_state.user
    metadata = user.user_metadata or {}

    display_name = metadata.get(
        "full_name",
        user.email.split("@")[0]
    )

    st.title(f"Welcome, {display_name}")
    st.write(
        "Your workspace for intelligent text summarization."
    )

    try:
        history = load_history()
    except Exception:
        history = []
        st.warning(
            "Unable to load statistics right now."
        )

    total_summaries = len(history)

    total_words = sum(
        len(item["original_text"].split())
        for item in history
    )

    total_saved = sum(
        max(
            0,
            len(item["original_text"].split())
            - len(item["summary_text"].split())
        )
        for item in history
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Summaries Created",
        total_summaries
    )

    col2.metric(
        "Original Words Processed",
        f"{total_words:,}"
    )

    col3.metric(
        "Words Removed",
        f"{total_saved:,}"
    )

    st.divider()

    st.subheader("Get started")

    col1, col2 = st.columns(2)

    with col1:
        with st.container(border=True):
            st.subheader("Summarize Text")
            st.write(
                "Paste an article, notes, or other text "
                "and generate a concise summary."
            )

            if st.button(
                "Open Summarizer",
                type="primary",
                use_container_width=True
            ):
                st.session_state.page = "Summarize Text"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("Summary History")
            st.write(
                "Review summaries saved to your account."
            )

            if st.button(
                "View History",
                use_container_width=True
            ):
                st.session_state.page = "History"
                st.rerun()

    st.subheader("Recent Summaries")

    if history:
        for item in history[:5]:
            with st.container(border=True):
                st.write(
                    f"**{item['summary_length']} Summary**"
                )

                st.caption(
                    item["created_at"][:16].replace("T", " ")
                )

                st.write(
                    item["summary_text"][:250]
                    + (
                        "..."
                        if len(item["summary_text"]) > 250
                        else ""
                    )
                )
    else:
        st.info(
            "No summaries yet. Generate your first summary "
            "to see it here."
        )


# --------------------------------------------------
# SUMMARIZER PAGE
# --------------------------------------------------

def summarizer_page():
    st.title("Text Summarization")
    st.write(
        "Paste your text and choose how concise the summary "
        "should be."
    )

    text_input = st.text_area(
        "Enter your text",
        height=260,
        placeholder="Paste an article or paragraph here..."
    )

    length = st.selectbox(
        "Summary length",
        ["Short", "Medium", "Detailed"]
    )

    if st.button(
        "Summarize Text",
        type="primary"
    ):
        if len(text_input.strip()) < 30:
            st.warning(
                "Please enter at least 30 characters."
            )
        else:
            summary = summarize_text(
                text_input,
                length
            )

            st.session_state.generated_summary = {
                "original": text_input,
                "summary": summary,
                "length": length
            }

            save_summary(
                text_input,
                summary,
                length
            )

    result = st.session_state.generated_summary

    if result:
        st.divider()
        st.subheader("Generated Summary")

        st.write(result["summary"])

        original_words = len(
            result["original"].split()
        )

        summary_words = len(
            result["summary"].split()
        )

        reduction = (
            (1 - summary_words / original_words) * 100
            if original_words else 0
        )

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Original Words",
            original_words
        )

        col2.metric(
            "Summary Words",
            summary_words
        )

        col3.metric(
            "Word Reduction",
            f"{reduction:.1f}%"
        )

        st.download_button(
            "Download Summary",
            data=result["summary"],
            file_name="summary.txt",
            mime="text/plain"
        )

        with st.expander("View Original Text"):
            st.write(result["original"])


# --------------------------------------------------
# HISTORY PAGE
# --------------------------------------------------

def history_page():
    st.title("Summary History")
    st.write(
        "View and manage summaries saved to your account."
    )

    try:
        history = load_history()
    except Exception:
        st.error(
            "Unable to load your history. Please try again."
        )
        return

    if not history:
        st.info(
            "You haven't saved any summaries yet."
        )
        return

    for item in history:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])

            with col1:
                st.subheader(
                    f"{item['summary_length']} Summary"
                )

                st.caption(
                    item["created_at"][:16].replace("T", " ")
                )

            with col2:
                st.download_button(
                    "Download",
                    data=item["summary_text"],
                    file_name=f"summary_{item['id'][:8]}.txt",
                    mime="text/plain",
                    key=f"download_{item['id']}"
                )

            with st.expander("View Summary"):
                st.write(item["summary_text"])

            with st.expander("View Original Text"):
                st.write(item["original_text"])

            if st.button(
                "Delete Summary",
                key=f"delete_{item['id']}"
            ):
                try:
                    (
                        supabase.table("summaries")
                        .delete()
                        .eq("id", item["id"])
                        .eq(
                            "user_id",
                            st.session_state.user.id
                        )
                        .execute()
                    )

                    st.success("Summary deleted.")
                    st.rerun()

                except Exception:
                    st.error(
                        "Unable to delete this summary."
                    )


# --------------------------------------------------
# PROFILE PAGE
# --------------------------------------------------

def profile_page():
    st.title("My Profile")

    user = st.session_state.user
    metadata = user.user_metadata or {}

    st.write("### Account Information")

    st.text_input(
        "Full Name",
        value=metadata.get("full_name", ""),
        disabled=True
    )

    st.text_input(
        "Email Address",
        value=user.email or "",
        disabled=True
    )

    st.caption(
        "Account details are managed through Supabase Authentication."
    )


# --------------------------------------------------
# MAIN APPLICATION
# --------------------------------------------------

if not restore_session():
    authentication_page()
    st.stop()


# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------

user = st.session_state.user
metadata = user.user_metadata or {}

display_name = metadata.get(
    "full_name",
    user.email.split("@")[0]
)

with st.sidebar:
    st.title("Text Summarization Chatbot")

    st.caption("AI ABL Project")

    st.divider()

    st.write(f"Signed in as **{display_name}**")

    st.caption(user.email)

    st.divider()

    pages = [
        "Dashboard",
        "Summarize Text",
        "History",
        "Profile"
    ]

    current_index = (
        pages.index(st.session_state.page)
        if st.session_state.page in pages
        else 0
    )

    selected_page = st.radio(
        "Navigation",
        pages,
        index=current_index
    )

    if selected_page != st.session_state.page:
        st.session_state.page = selected_page
        st.rerun()

    st.divider()

    if st.button(
        "Logout",
        use_container_width=True
    ):
        logout()
        st.rerun()


# --------------------------------------------------
# PAGE ROUTING
# --------------------------------------------------

if st.session_state.page == "Dashboard":
    dashboard_page()

elif st.session_state.page == "Summarize Text":
    summarizer_page()

elif st.session_state.page == "History":
    history_page()

elif st.session_state.page == "Profile":
    profile_page()

st.divider()

st.caption(
    "Text Summarization Chatbot | "
    "Artificial Intelligence ABL Project"
)
