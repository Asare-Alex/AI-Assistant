import streamlit as st
from google import genai
from google.genai import types
from PyPDF2 import PdfReader
import io
from pyexpat.errors import messages
import os

def serve_manifest():
    with open('manifest.json', 'r') as f:
        return f.read()

st.markdown("""
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta name="apple-mobile-web-app-capable" content="yes" >
        <meta name="apple-mobile-web-app-status-bar-style" content="black-trasnlucent">
        <meta name="mobile-web-app-capable" content="yes" >
        <link rel="manifest" href="manifest.json">
        <meta name="theme-color" content="#007bff">
    </head>
""", unsafe_allow_html=True)

st.markdown("""
    <script>
    if('serviceWorker' in navigator) {
        windows.addEventListener('load', function() {
            navigator.serviceWorker.register('/sw.js').then(function(registration) {
            console.log(registration);console.log('ServiceWorker registration successful');
            }, function(err) {
                console.log('ServiceWorker registration failed', err);
                });
            });
        }
    </script>
""", unsafe_allow_html=True)

# --- 1. CONFIGURATION ---
# gemini-1.5-flash is the most reliable free-tier model for students
MODEL_ID = "gemini-2.5-flash"

st.set_page_config(page_title="University AI Workspace", page_icon="knust.png", layout="wide", initial_sidebar_state="collapsed")


#Changing font to Roboto
st.markdown("""
    <style>
    @import url(https://fonts.googleapis.com/css2?family=Roboto+Sans:wght@300;400;700;ital&display=swap);
    
    html, body, [class*="st-"] { font-family: Roboto, sans-serif !important; }
      /* Remove default Streamlit padding at the very top */
    .block-container {
        padding-top: 0rem !important;
    }
    
    @media (max-width: 600px) {
        div.stButton > button{
            width: 100% !important;
            margin-bottom: 10px;
        }
    }
    /* Make the nav buttons look like links */
    div.stButton > button {
        border-radius: 4px;
        background-color: #007bff;
        color: white;
        padding: 0.5rem;
        padding-right: 10px !important;
        border: 1px solid #007bff;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
        width: auto;
    }
    div.stButton > button:hover {
        background-color: #0069d9;
        border-color: #0062cc;
        color: white;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
    }
    div.stButton > button:hover {
        background-color: #0062cc;
        transform: translateY(1px);
    }
    div.stButton > button:contains("Clear Chat") {
        background-color: #0dc3545 !important;;
        border-color: #dc3545 !important;;;
    }
    div.stButton > button:contains("Clear Chat"):hover {
        background-color: #c82333 !important;;
        border-color: #bd2130 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Install FPDF if you haven't: pip install fpdf2
try:
    from fpdf import FPDF
except ImportError:
    st.error("Missing library! Run: pip install fpdf2")
    st.stop()

# --- 2. API KEY SETUP ---
# Replace the text below with your actual API key from AI Studio
API_KEY = "YOUR_API_KEY".strip()

if not API_KEY or API_KEY == "ANOTHER_BACKUP_API_KEY":
    st.sidebar.warning("⚠️ Enter API Key to start")
    api_input = st.sidebar.text_input("Gemini API Key", type="password")
    if api_input:
        API_KEY = api_input.strip()
    else:
        st.stop()

client = genai.Client(api_key=API_KEY)

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# --- SYSTEM PROMPTS ---
SOCRATIC_PROMPT = """
You are a Socratic Tutor for university students. 
Your goal is to help students learn, NOT to do their homework for them.
RULES:
1. Never give the full answer immediately.
2. Break the problem into small steps. 
3. Ask the student a question to lead them to the next step.
4. If they get a step wrong, explain the concept simply and ask them to try again.
5. Praise progress, even if small.
6. Use university-level terminology but keep explanations clear.
"""

NOTES_PROMPT = """
Convert the following audio transcription or text into structured academic notes.
Include: Main Topic, Key Definitions, and a 'Summary for Revision' section.
"""

# --- APP LAYOUT ---

st.markdown("---")

# Create a container that will stay at the very top
nav_container = st.container()

with nav_container:
    # Use columns to create the menu items
    # Adjust ratios to push links to the right
    logo_col, title_col, space_col, abt_col, use_col, con_col = st.columns([0.2, 3, 1, 0.85, 1.2, 1])

   # with logo_col:
         # st.image("knust.png", width="stretch")

    with title_col:
        st.title("**University AI Workspace**")

    with abt_col:
        if st.button("ℹ️ About"):
            st.info("Uni-Creator AI: Empowering students in Ghana.")

    with use_col:
        if st.button("📖 How to Use",):
            st.info("1. Select a tool above. 2. Chat or Upload PDF. 3. Learn step-by-step!")

    with con_col:
        if st.button("📧 Contact",):
            st.info("Support: baffourasarealex@gmail.com")

st.divider()

# My Tabs
tab1, tab2, tab3 = st.tabs(["💡 Socratic Tutor", "📑 PDF Research Lab", "🎙️ Voice Notes"])

# --- FEATURE 1: SOCRATIC TUTOR ---
with tab1:
    col1, col2 = st.columns([0.83, 0.17])
    with col1:
        st.header("Step-by-Step Learning Guide")
        st.info("I'll guide you through problems without rushing to the answer.")
    with col2:
        # CLEAR CHAT BUTTON
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        icon = "‍🎓" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=icon):
            st.write(msg["content"])

    if user_input := st.chat_input("Ask a question (e.g., 'How do I use the Okumura Model?')"):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👨‍🎓"):
            st.write(user_input)

        with st.chat_message("assistant", avatar="🤖"):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_input,
                config={'system_instruction': SOCRATIC_PROMPT}
            )
            st.write(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

if st.session_state.messages:
    st.divider()
    if st.button("📄 Prepare Study Guide (PDF)"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", 'B', 16)
        pdf.cell(0, 10, "Socratic Study Session Notes", ln=True, align='C')
        pdf.ln(10)

        pdf.set_font("helvetica", size=12)
        for msg in st.session_state.messages:
            role = "STUDENT: " if msg["role"] == "user" else "TUTOR: "
            pdf.set_font("helvetica", 'B', 12)
            pdf.write(5, role)
            pdf.set_font("helvetica", size=12)
            # multi_cell handles long text and wrapping
            pdf.multi_cell(0, 10, txt=msg["content"])
            pdf.ln(5)

        # Export to bytes for Streamlit download button
        pdf_bytes = pdf.output()
        st.download_button(
            label="📥 Download Study Guide",
            data=bytes(pdf_bytes),
            file_name="study_guide.pdf",
            mime="application/pdf"
        )

# --- FEATURE 2: PDF RESEARCH LAB ---
with tab2:
    st.header("Chat with your Textbooks")
    uploaded_file = st.file_uploader("Upload a PDF (Syllabus, Handout, or Textbook)", type="pdf")

    if uploaded_file:
        # Extract text from PDF
        pdf_reader = PdfReader(uploaded_file)
        pdf_text = ""
        for page in pdf_reader.pages:
            pdf_text += page.extract_text()

        st.success(f"Loaded {len(pdf_reader.pages)} pages!")

        query = st.text_input("What do you want to find in this document?")
        if query:
            with st.spinner("Searching document..."):
                # Pass the PDF text as context
                context_prompt = f"Based on this text: {pdf_text[:10000]}... Answer this: {query}"
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=context_prompt
                )
                st.markdown("### 📖 Answer from your Document:")
                st.write(response.text)


# --- FEATURE 3: VOICE NOTES ---
with tab3:
    st.header("Lecture-to-Notes")
    st.write("Record a quick thought or a snippet of a lecture.")

    audio_data = st.audio_input("Record your voice message")

    if audio_data:
        with st.spinner("Processing audio..."):
            # We convert the raw audio bytes into a "Part" that Gemini understands
            audio_part = types.Part.from_bytes(
                data=audio_data.getvalue(),
                mime_type="audio/wav"  # Streamlit's audio_input usually records in wav
            )

            # Now we send it to the model
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[NOTES_PROMPT, audio_part]
            )

            st.markdown("### ✨ Formatted Study Note")
            st.write(response.text)
            st.download_button("Download Note as .txt", response.text)

# --- FOOTER SECTION ---
footer_html = """
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #f1f1f1;
    color: #333;
    text-align: center;
    padding: 10px;
    font-size: 14px;
    border-top: 1px solid #e7e7e7;
    z-index: 1000;
}
.footer a {
    color: #007bff;
    text-decoration: none;
    margin: 0 10px;
}
.footer a:hover {
    text-decoration: underline;
}
</style>
<div class="footer">
    <p>© 2026 Uni-Creator AI Ghana | 
        <a href="#">Privacy Policy</a> | 
        <a href="#">Terms of Service</a> | 
        <a href="mailto:baffourasarealex@gmail.com">Contact Support</a>
    </p>
</div>
"""

st.markdown(footer_html, unsafe_allow_html=True)

