from flask import Flask, render_template, session, request, jsonify
from flask_socketio import SocketIO, emit
import sqlite3
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = "super_secret_key"
socketio = SocketIO(app, cors_allowed_origins="*")

DB_PATH = "community_chat.db"

# Initialize DB with messages table
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

def save_message(msg_id, session_id, message):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (id, session_id, message, timestamp) VALUES (?, ?, ?, ?)",
            (msg_id, session_id, message, datetime.now())
        )

def get_all_messages():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("SELECT id, session_id, message, timestamp FROM messages ORDER BY timestamp ASC")
        return cur.fetchall()

# Assign session_id on first visit
@app.before_request
def assign_session():
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

@app.route("/")
def index():
    return render_template("community.html")

@app.route("/load_messages")
def load_messages():
    msgs = get_all_messages()
    messages = [
        {"id": m[0], "session_id": m[1], "message": m[2], "timestamp": m[3]} for m in msgs
    ]
    return jsonify(messages)

# SocketIO Events
@socketio.on("send_message")
def handle_send_message(data):
    msg_text = data.get("message", "").strip()
    sender_sid = session.get("session_id")
    if not msg_text:
        return

    # Save message
    msg_id = str(uuid.uuid4())
    save_message(msg_id, sender_sid, msg_text)

    # Broadcast new message with id and timestamp
    msg_data = {
        "id": msg_id,
        "session_id": sender_sid,
        "message": msg_text,
        "timestamp": datetime.now().isoformat()
    }
    emit("new_message", msg_data, broadcast=True)

@socketio.on("typing")
def handle_typing():
    sender_sid = session.get("session_id")
    emit("user_typing", {"session_id": sender_sid}, broadcast=True, include_self=False)

@socketio.on("typing")
def handle_typing(data):
    sender_sid = session.get("session_id")
    is_typing = data.get("typing", False)
    emit("user_typing", {"session_id": sender_sid, "typing": is_typing}, broadcast=True, include_self=False)

if __name__ == "__main__":
    init_db()
    socketio.run(app, debug=True)
