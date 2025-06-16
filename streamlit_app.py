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

# --- REVISED: Custom CSS for sidebar buttons ---
st.markdown("""
<style>
    /* Target the container of the chat title buttons in the sidebar */
    section[data-testid="stSidebar"] .stButton button {
        /* Force text alignment to the left */
        justify-content: left !important;
        text-align: left !important;
        
        /* Ensure the button itself doesn't grow with long text */
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
        display: block; /* Required for text-overflow to work */
    }

    /* Target the popover specifically to remove the bulge and background */
    section[data-testid="stSidebar"] div[data-testid="stPopover"] > button {
        /* Make the button itself invisible */
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        width: auto; /* Allow it to fit the content (the arrow) */
        
        /* Position the arrow correctly */
        display: flex;
        justify-content: flex-end; /* Push the arrow to the right */
    }
    
    /* Ensure the popover arrow is visible */
    section[data-testid="stSidebar"] div[data-testid="stPopover"] svg {
        stroke: currentColor;
    }
</style>
""", unsafe_allow_html=True)


# Initialize OpenAI client from Streamlit secrets
try:
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
except Exception:
    st.error("OpenAI API key not found. Please add it to your Streamlit secrets.", icon="🚨")
    st.stop()


# --- Database Functions (no changes) ---
def load_db():
    """Loads the chat database from the JSON file."""
    if not os.path.exists(DB_FILE) or os.path.getsize(DB_FILE) == 0:
        return {'chats': {}}
    try:
        with open(DB_FILE, 'r') as file:
            data = json.load(file)
            if 'chats' not in data or not isinstance(data.get('chats'), dict):
                return {'chats': {}}
            return data
    except (json.JSONDecodeError, FileNotFoundError):
        return {'chats': {}}

def save_db(db):
    """Saves the chat database to the JSON file."""
    with open(DB_FILE, 'w') as file:
        json.dump(db, file, indent=4)

def generate_title(chat_history):
    """Generates a title for a chat using OpenAI."""
    history_summary = [{"role": msg["role"], "content": msg["content"][:200]} for msg in chat_history]
    title_prompt = f"""
    Based on the following conversation, generate a short, concise title (4-5 words max).
    The title should be plain text, without any markdown or quotation marks.
    ---
    {json.dumps(history_summary)}
    ---
    Title:"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": title_prompt}],
            max_tokens=15,
            temperature=0.2,
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
    reverse=True,
)

for chat_id in sorted_chat_ids:
    chat_info = db['chats'][chat_id]
    chat_title = chat_info.get('title', 'Untitled')
    
    col1, col2 = st.sidebar.columns([0.8, 0.2])
    
    with col1:
        if st.button(
            chat_title, 
            key=f"select_{chat_id}", 
            use_container_width=True,
            type="primary" if st.session_state.get('active_chat_id') == chat_id else "secondary"
        ):
            st.session_state.active_chat_id = chat_id
            st.rerun()

    with col2:
        # Using an empty string for the popover label to hide any icon
        popover = st.popover("", use_container_width=True, help="Chat options")

        new_title = popover.text_input("Rename", value=chat_title, key=f"rename_{chat_id}")
        if new_title != chat_title:
            db['chats'][chat_id]['title'] = new_title
            save_db(db)
            st.rerun()

        if popover.button("Delete Chat", key=f"delete_{chat_id}", type="primary", use_container_width=True):
            del db['chats'][chat_id]
            if st.session_state.get('active_chat_id') == chat_id:
                st.session_state.active_chat_id = None
            save_db(db)
            st.rerun()

# --- Model Selection (no changes) ---
st.sidebar.divider()
st.sidebar.header("Configuration")
models = ["gpt-4.1-nano", "gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
st.session_state["openai_model"] = st.sidebar.selectbox("Select OpenAI model", models, index=0)

# --- Main Chat Interface (no changes) ---
if "active_chat_id" not in st.session_state:
    st.session_state.active_chat_id = sorted_chat_ids[0] if sorted_chat_ids else None

active_chat_id = st.session_state.active_chat_id

if active_chat_id and active_chat_id in db.get('chats', {}):
    current_chat = db['chats'][active_chat_id]['messages']
    for message in current_chat:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
else:
    st.info('Start a new conversation by typing below or clicking "New Chat".')

if prompt := st.chat_input("What would you like to research?"):
    if active_chat_id is None:
        active_chat_id = str(time.time())
        st.session_state.active_chat_id = active_chat_id
        db['chats'][active_chat_id] = {
            'title': DEFAULT_TITLE,
            'messages': [],
            'created_at': time.time()
        }
    
    db['chats'][active_chat_id]['messages'].append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream = client.chat.completions.create(
            model=st.session_state["openai_model"],
            messages=[{"role": m["role"], "content": m["content"]} for m in db['chats'][active_chat_id]['messages']],
            stream=True,
        )
        response = st.write_stream(stream)
    
    db['chats'][active_chat_id]['messages'].append({"role": "assistant", "content": response})

    if db['chats'][active_chat_id]['title'] == DEFAULT_TITLE and len(db['chats'][active_chat_id]['messages']) == 2:
        with st.spinner("Generating title..."):
            new_title = generate_title(db['chats'][active_chat_id]['messages'])
            db['chats'][active_chat_id]['title'] = new_title
        save_db(db)
        st.rerun()
    else:
        save_db(db)