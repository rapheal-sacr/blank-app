import streamlit as st
from openai import OpenAI
import json
import os
import time

# --- Configuration and Constants ---
DB_FILE = 'db.json'
DEFAULT_TITLE = "New Chat"

# --- Main App UI ---
st.title("SACR AI Research UI")

# Initialize OpenAI client from Streamlit secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.", icon="🚨")
    st.stop()


# --- Database Functions ---
def load_db():
    """Loads the chat database from the JSON file."""
    if not os.path.exists(DB_FILE):
        return {'chats': {}}
    try:
        with open(DB_FILE, 'r') as file:
            # Ensure the file is not empty before trying to load
            if os.path.getsize(DB_FILE) > 0:
                data = json.load(file)
                # Ensure the 'chats' key exists, otherwise initialize it
                if 'chats' not in data or not isinstance(data['chats'], dict):
                    return {'chats': {}}
                return data
            else:
                return {'chats': {}}
            # --- FIX END ---
    except (json.JSONDecodeError, FileNotFoundError):
        st.error("Error reading the database file. Starting with a fresh database.", icon="⚠️")
        return {'chats': {}}

def save_db(db):
    """Saves the chat database to the JSON file."""
    with open(DB_FILE, 'w') as file:
        json.dump(db, file, indent=4)

def generate_title(chat_history):
    """Generates a title for a chat using OpenAI."""
    history_summary = [
        {"role": msg["role"], "content": msg["content"][:200]}
        for msg in chat_history
    ]

    title_prompt = f"""
    Based on the following conversation, generate a short, concise title (4-5 words max).
    The title should be plain text, without any markdown or quotation marks.
    ---
    {json.dumps(history_summary)}
    ---
    Title:
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=15,
            temperature=0.2
        )
        title = response.choices[0].message.content.strip().replace('"', '')
        return title if title else DEFAULT_TITLE
    except Exception as e:
        st.toast(f"Could not generate title: {e}", icon="🤖")
        return DEFAULT_TITLE

# --- Load Database ---
db = load_db()

# --- Sidebar for Chat Management ---
st.sidebar.header("Chat Controls")

if st.sidebar.button("➕ New Chat", use_container_width=True):
    st.session_state.active_chat_id = None
    st.rerun()

st.sidebar.subheader("Previous Chats")

sorted_chat_ids = sorted(
    db.get('chats', {}).keys(),
    key=lambda cid: db['chats'][cid].get('created_at', 0),
    reverse=True
)

for chat_id in sorted_chat_ids:
    chat_info = db['chats'][chat_id]
    chat_title = chat_info.get('title', 'Untitled')
    if st.sidebar.button(chat_title, key=f"chat_{chat_id}", use_container_width=True):
        st.session_state.active_chat_id = chat_id
        st.rerun()

st.sidebar.divider()
st.sidebar.header("Configuration")
models = ["gpt-4.1-nano", "gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
st.session_state["openai_model"] = st.sidebar.selectbox("Select OpenAI model", models, index=0)

# --- Main Chat Interface ---

if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = sorted_chat_ids[0] if sorted_chat_ids else None

if st.session_state.active_chat_id and st.session_state.active_chat_id in db.get('chats', {}):
    current_chat = db['chats'][st.session_state.active_chat_id]['messages']
    for message in current_chat:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
else:
    st.session_state.active_chat_id = None
    st.info("Start a new conversation by typing below or clicking 'New Chat'.")

if prompt := st.chat_input("What would you like to research?"):
    if st.session_state.active_chat_id is None:
        new_chat_id = str(time.time())
        st.session_state.active_chat_id = new_chat_id
        # This is the line from the traceback. It's now safe because db is guaranteed to have 'chats'
        db['chats'][new_chat_id] = {
            'title': DEFAULT_TITLE,
            'messages': [],
            'created_at': time.time()
        }

    active_id = st.session_state.active_chat_id
    db['chats'][active_id]['messages'].append({"role": "user", "content": prompt})

    # Display user message immediately by re-rendering
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in db['chats'][active_id]['messages']
                ],
                stream=True,
            )
            response = st.write_stream(stream)

    db['chats'][active_id]['messages'].append({"role": "assistant", "content": response})

    # Check for title generation
    if db['chats'][active_id]['title'] == DEFAULT_TITLE and len(db['chats'][active_id]['messages']) == 2:
        with st.spinner("Generating title..."):
            new_title = generate_title(db['chats'][active_id]['messages'])
            db['chats'][active_id]['title'] = new_title
        save_db(db)
        st.rerun()
    else:
        save_db(db)