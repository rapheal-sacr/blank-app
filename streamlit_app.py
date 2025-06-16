import streamlit as st
from openai import OpenAI
import json
import os

DB_FILE = 'db.json'

st.title("SACR AI Research UI")

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Database Functions ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {'chat_history': []}
    with open(DB_FILE, 'r') as file:
        return json.load(file)

def save_db(db):
    with open(DB_FILE, 'w') as file:
        json.dump(db, file, indent=4)

# --- Sidebar ---
st.sidebar.title("Configuration")
models = ["gpt-4.1-nano", "gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
st.session_state["openai_model"] = st.sidebar.selectbox("Select OpenAI model", models, index=2) # Default to gpt-4o for better performance

if st.sidebar.button('Clear Chat History'):
    st.session_state.messages = []
    save_db({'chat_history': []})
    st.rerun()

# --- Main App ---

# Load chat history from session state or db
if "messages" not in st.session_state:
    db = load_db()
    st.session_state.messages = db.get('chat_history', [])

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What would you like to research?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        )
        response = st.write_stream(stream)

    st.session_state.messages.append({"role": "assistant", "content": response})

    # Save the updated chat history to the file
    db = load_db()
    db['chat_history'] = st.session_state.messages
    save_db(db)