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
            return json.load(file)
    except json.JSONDecodeError:
        st.error("Error reading the database file. Starting fresh.", icon="⚠️")
        return {'chats': {}}

def save_db(db):
    """Saves the chat database to the JSON file."""
    with open(DB_FILE, 'w') as file:
        json.dump(db, file, indent=4)

def generate_title(chat_history):
    """Generates a title for a chat using OpenAI."""
    title_prompt = f"""
    Based on the following conversation, generate a short, concise title (4-5 words max).
    ---
    {json.dumps(chat_history)}
    ---
    Title:
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Use a fast model for titles
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=15,
            temperature=0.2
        )
        title = response.choices[0].message.content.strip().replace('"', '')
        return title
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

# Sort chats by creation time, newest first
sorted_chat_ids = sorted(
    db.get('chats', {}).keys(),
    key=lambda cid: db['chats'][cid].get('created_at', 0),
    reverse=True
)

for chat_id in sorted_chat_ids:
    chat_title = db['chats'][chat_id].get('title', 'Untitled')
    if st.sidebar.button(chat_title, key=f"chat_{chat_id}", use_container_width=True):
        st.session_state.active_chat_id = chat_id
        st.rerun()

# --- Model Selection ---
st.sidebar.divider()
st.sidebar.header("Configuration")
models = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
st.session_state["openai_model"] = st.sidebar.selectbox("Select OpenAI model", models, index=0)

# --- Main Chat Interface ---

# Determine the active chat
if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = None

# If no chat is active, create a new one
if st.session_state.active_chat_id is None and sorted_chat_ids:
    st.session_state.active_chat_id = sorted_chat_ids[0]

# Display messages for the active chat
if st.session_state.active_chat_id:
    current_chat = db['chats'][st.session_state.active_chat_id]['messages']
    for message in current_chat:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
else:
    st.info("Start a new conversation by typing below or clicking 'New Chat'.")


# Accept user input
if prompt := st.chat_input("What would you like to research?"):
    # If this is the first message in a new chat, create the chat entry
    if st.session_state.active_chat_id is None:
        new_chat_id = str(time.time())
        st.session_state.active_chat_id = new_chat_id
        db['chats'][new_chat_id] = {
            'title': DEFAULT_TITLE,
            'messages': [],
            'created_at': time.time()
        }

    # Add user message to the active chat and display it
    active_id = st.session_state.active_chat_id
    db['chats'][active_id]['messages'].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get assistant's response
    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in db['chats'][active_id]['messages']
            ],
            stream=True,
        )
        response = st.write_stream(stream)

    # Add assistant response to the active chat
    db['chats'][active_id]['messages'].append({"role": "assistant", "content": response})

    # Check if a title needs to be generated (only for new chats on the first exchange)
    should_generate_title = (
        db['chats'][active_id]['title'] == DEFAULT_TITLE and
        len(db['chats'][active_id]['messages']) == 2
    )

    if should_generate_title:
        with st.spinner("Generating title..."):
            new_title = generate_title(db['chats'][active_id]['messages'])
            db['chats'][active_id]['title'] = new_title
        save_db(db)
        st.rerun() # Rerun to show the new title in the sidebar
    else:
        save_db(db) # Save chat history without rerunning