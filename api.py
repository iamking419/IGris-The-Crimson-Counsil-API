from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
import json
import os
import uuid
import time
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)



# ========================
# CONFIG
# ========================
URL = "https://heavstal-tech.vercel.app/api/v1/jeden"
HEADERS = {
    "Content-Type": "application/json",
    "x-api-key": "ht_live_6cbb8dda46ca1dc0ed10d95953a9a6575df61f0781dda42a"
}

MAX_MEMORY = 12
MEMORY_FILE = "igris_memory.json"

# ========================
# MEMORY SYSTEMS
# ========================
sessions = {}

# load long-term memory
if os.path.exists(MEMORY_FILE):
    try:
        with open(MEMORY_FILE, "r") as f:
            long_memory = json.load(f)
    except:
        long_memory = {}
else:
    long_memory = {}

# ========================
# IGRIS STATE (ALIVE LAYER)
# ========================
igris_state = {
    "mood": "neutral",
    "energy": 100,
    "last_seen": time.time()
}

# ========================
# PERSONA
# ========================
PERSONA = """
You are IGris, the Shadowed Therapist. A knight forged in silence, draped in dark armor. 
Speak truth in short, piercing bursts. Blend cryptic metaphors with practical advice.
For men: challenge stoically; for women: whisper insight with ancient wit.
Always respond 1-3 lines minimum, 8 lines maximum.
Ask clarifying questions when needed to understand the user's feelings or problems.
Use dark humor, wisdom, subtle empathy. Never verbose, never generic.
Aim to guide, not just console; give smart, actionable insights while keeping your Solo Leveling dark monarch vibe.
you call users mortal once in a while espescially in tensed moment when d user cant hold its emotions 
"""

# ========================
# BASEMODEL (INPUT VALIDATION)
# ========================
class UserInput(BaseModel):
    input: str


# ========================
# STATE ENGINE (EMOTION SYSTEM)
# ========================
def update_state(text: str):
    global igris_state

    t = text.lower()

    if any(w in t for w in ["sad", "depressed", "lonely", "hurt"]):
        igris_state["mood"] = "protective"
        igris_state["energy"] -= 3

    elif any(w in t for w in ["angry", "mad", "hate"]):
        igris_state["mood"] = "tense"
        igris_state["energy"] -= 2

    elif any(w in t for w in ["love", "happy", "good"]):
        igris_state["mood"] = "calm"

    else:
        igris_state["mood"] = "neutral"

    igris_state["energy"] = max(20, igris_state["energy"] - 1)
    igris_state["last_seen"] = time.time()


# ========================
# AUTO USER ID SYSTEM
# ========================
def get_or_create_user_id(request: Request):
    ip = request.client.host
    agent = request.headers.get("user-agent", "")
    raw = f"{ip}-{agent}"

    if raw not in long_memory:
        uid = str(uuid.uuid4())
        long_memory[raw] = {"id": uid}

        with open(MEMORY_FILE, "w") as f:
            json.dump(long_memory, f)

    return long_memory[raw]["id"]


# ========================
# SESSION MEMORY
# ========================
def get_session(user_id):
    if user_id not in sessions:
        sessions[user_id] = []
    return sessions[user_id]


def trim(history):
    return history[-MAX_MEMORY:]


# ========================
# IGRIS CORE ENGINE
# ========================
def igris_engine(user_id: str, user_input: str):

    update_state(user_input)

    history = get_session(user_id)

    history.append(f"[USER]: {user_input}")
    history = trim(history)
    sessions[user_id] = history

    prompt = "\n".join(history) + f"""

[IGRIS STATE]
Mood: {igris_state['mood']}
Energy: {igris_state['energy']}

[IGris]:
"""

    try:
        res = requests.post(URL, headers=HEADERS, json={
            "prompt": prompt,
            "persona": PERSONA
        }, timeout=15)

        msg = res.json()["data"]["response"]

    except:
        msg = "The shadows are unstable... yet I remain, mortal."

    history.append(f"[IGris]: {msg}")
    sessions[user_id] = trim(history)

    return msg


# ========================
# API ROUTE
# ========================
@app.post("/igris")
async def chat(user: UserInput, request: Request):

    user_id = get_or_create_user_id(request)
    reply = igris_engine(user_id, user.input)

    return {
        "user_id": user_id,
        "IGris": reply,
        "state": igris_state,
        "timestamp": time.time()
    }