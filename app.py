
import re
import math
from collections import Counter

import streamlit as st

STOPWORDS = set("""
a an the and or but if while with to of in on for from by is are
was were be been being it this that these those as at after before
into about over under between through during can could should would
will may might do does did have has had not no so than then very also
""".split())


def split_sentences(text):
    text = re.sub(r"\s+", " ", text.strip())
    return [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if s.strip()
    ]


def summarize_text(text, length):
    sentences = split_sentences(text)

    if not sentences:
        return "Please enter some text."

    if len(sentences) <= 2:
        return " ".join(sentences)

    words = re.findall(r"\b[a-zA-Z]+\b", text.lower())
    useful_words = [
        w for w in words
        if w not in STOPWORDS and len(w) > 2
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
            r"\b[a-zA-Z]+\b", sentence.lower()
        )
        important = [
            w for w in sentence_words
            if w not in STOPWORDS and len(w) > 2
        ]

        score = (
            sum(frequencies.get(w, 0) for w in important)
            / math.sqrt(len(important))
            if important else 0
        )
        scores.append(score)

    if length == "Short":
        count = max(1, math.ceil(len(sentences) * 0.25))
    elif length == "Detailed":
        count = max(1, math.ceil(len(sentences) * 0.65))
    else:
        count = max(1, math.ceil(len(sentences) * 0.40))

    count = min(count, len(sentences))

    chosen = sorted(
        range(len(sentences)),
        key=lambda i: scores[i],
        reverse=True
    )[:count]

    chosen.sort()
    return " ".join(sentences[i] for i in chosen)


st.set_page_config(
    page_title="Text Summarization Chatbot",
    page_icon="📝",
    layout="centered"
)

st.title("Text Summarization Chatbot")
st.write(
    "Summarize long passages into shorter, meaningful text."
)

st.info(
    "This application runs locally without an API key. "
    "It selects important sentences from the input."
)

text_input = st.text_area(
    "Enter your text",
    height=250,
    placeholder="Paste an article or paragraph here..."
)

length = st.selectbox(
    "Summary length",
    ["Short", "Medium", "Detailed"]
)

if st.button("Summarize Text", type="primary"):
    if len(text_input.strip()) < 30:
        st.warning("Please enter at least 30 characters.")
    else:
        summary = summarize_text(text_input, length)

        st.subheader("Generated Summary")
        st.write(summary)

        original_words = len(text_input.split())
        summary_words = len(summary.split())

        col1, col2, col3 = st.columns(3)
        col1.metric("Original words", original_words)
        col2.metric("Summary words", summary_words)

        reduction = (
            (1 - summary_words / original_words) * 100
        )
        col3.metric("Word reduction", f"{reduction:.1f}%")

        st.download_button(
            "Download Summary",
            data=summary,
            file_name="summary.txt",
            mime="text/plain"
        )

st.divider()
st.caption("Artificial Intelligence ABL Project")
