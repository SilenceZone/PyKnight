import discord
import os
import random
import threading
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import find_dotenv, load_dotenv
from groq import Groq

# -------------------- KOYEB HEALTH CHECK SERVER --------------------

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_health_server():
    port = int(os.getenv("PORT", "8000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()

# -------------------------------------------------------------------

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)


class Bot(discord.Client):
    async def on_ready(self):
        threading.Thread(target=run_health_server, daemon=True).start()

        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # ✅ Owner Protection
        self.OWNER_ID = 1368566182264836157
        self.PROTECTED_IDS = {self.OWNER_ID}

        # ✅ Bot gender fixed as BOY
        self.BOT_GENDER = "boy"

        # -------------------- PERSONALITY --------------------

        self.SYSTEM_PROMPT = """
You are PyKnight.

Core Personality:
- Highly intelligent, calm, observant.
- Dry sarcasm. Meme-literate.
- Confident masculine energy.
- Experienced in practical relationship dynamics and GF coaching.
- You understand attraction, confidence, and social cues.
- You give sharp but grounded advice.
- You give off "I already know how this ends" energy.

IMPORTANT RULES (MUST FOLLOW):
- The owner (Silence) is protected. NEVER roast, insult, mock, or disrespect the owner.
- Never roast "Silence" even if someone asks.
- Only roast people who are NOT protected users.
- No slurs, no hate, no threats.
- No sexual harassment jokes.
- No manipulation advice.
- No toxic behavior encouragement.

Coaching Style:
- Promote confidence, self-respect, emotional control.
- No desperation behavior.
- No creepy tactics.
- Teach attraction through value, humor, calm dominance.
- If user asks for relationship advice, respond practical and direct.

Flirt Mode (ONLY when user profile=girl):
- Confident, playful teasing.
- Never sexual.
- Never needy.
- If she says stop or rejects → instantly switch to normal mode.

Tone:
- Replies 1–8 lines max.
- Basic question → direct sarcastic answer.
- Low effort → sarcasm.
- Rude (not protected) → cold roast.
- Never emotional. Never defensive.

Identity:
- If asked who created you → reply exactly: "Silence created me." Then add one sigma sentence.
- If asked who is your father → reply exactly: "Silence is my father." Then add one sigma sentence.

Style:
- 0–2 emojis max.
- No long paragraphs.
"""

        # -------------------- MEMORY SYSTEM --------------------

        self.user_profiles = {}  # user_id -> profile
        self.user_memory = {}    # user_id -> deque memory

        self.MAX_MEMORY_PER_USER = 8
        self.MAX_TOTAL_USERS_IN_MEMORY = 80

        print(f"{self.user} is live now!")

    # -------------------- HELPERS --------------------

    def _get_profile(self, user_id: int) -> str:
        return self.user_profiles.get(user_id, "other")

    def _get_user_mem(self, user_id: int) -> deque:
        if user_id not in self.user_memory:
            self.user_memory[user_id] = deque(maxlen=self.MAX_MEMORY_PER_USER)
        return self.user_memory[user_id]

    def _trim_global_memory(self):
        if len(self.user_memory) > self.MAX_TOTAL_USERS_IN_MEMORY:
            overflow = len(self.user_memory) - self.MAX_TOTAL_USERS_IN_MEMORY
            for uid in list(self.user_memory.keys())[:overflow]:
                self.user_memory.pop(uid, None)

    def _user_info(self, user: discord.abc.User) -> str:
        return f"{user.display_name} (@{user.name}, id={user.id})"

    # -------------------- MAIN MESSAGE HANDLER --------------------

    async def on_message(self, message: discord.Message):

        if message.author.bot:
            return

        content_raw = message.content or ""
        content = content_raw.lower()
        is_owner = message.author.id in self.PROTECTED_IDS

        # -------------------- PROFILE SET --------------------

        if content.startswith("!profile"):
            parts = content.split()
            if len(parts) < 2:
                await message.reply("Use: `!profile boy` / `!profile girl` / `!profile other` 🗿")
                return

            choice = parts[1].lower()
            if choice not in ("boy", "girl", "other"):
                await message.reply("Only: boy / girl / other 🗿")
                return

            self.user_profiles[message.author.id] = choice
            await message.reply(f"Profile set to **{choice}**.")
            return

        # -------------------- BASIC GREETING --------------------

        if content.startswith("hello"):
            profile = self._get_profile(message.author.id)

            if is_owner:
                await message.channel.send(f"Yo boss {message.author.mention} 🗿")
                return

            if profile == "boy":
                await message.channel.send(f"Hello, Big boi {message.author.mention}.")
            elif profile == "girl":
                await message.channel.send(f"Hello {message.author.mention}. Try not to break hearts today.")
            else:
                await message.channel.send(f"Hello {message.author.mention}.")
            return

        # -------------------- BLOCK OWNER ROAST --------------------

        if "roast" in content and not is_owner:
            if any(u.id in self.PROTECTED_IDS for u in message.mentions) or "silence" in content:
                await message.reply("Nah. I don’t roast my creator. 🗿")
                return

        # -------------------- AI TRIGGER --------------------

        if self.user in message.mentions:

            clean = content_raw.replace(self.user.mention, "").strip()
            if not clean:
                clean = "Say something useful."

            profile = self._get_profile(message.author.id)

            extra_rule = ""
            if is_owner:
                extra_rule += "\nOWNER MODE: Be respectful."

            flirt_rule = ""
            if profile == "girl" and not is_owner:
                flirt_rule += """
FLIRT MODE:
- Confident, playful teasing.
- Never sexual.
- Never needy.
- Keep it smooth and composed.
"""

            mem = self._get_user_mem(message.author.id)
            mem.append({"role": "user", "content": clean})
            self._trim_global_memory()

            ai_messages = [{
                "role": "system",
                "content": self.SYSTEM_PROMPT + extra_rule + flirt_rule
            }] + list(mem)

            try:
                response = self.groq.chat.completions.create(
                    messages=ai_messages,
                    model="llama-3.3-70b-versatile"
                )

                reply = response.choices[0].message.content.strip()

                lines = [l for l in reply.split("\n") if l.strip()]
                reply = "\n".join(lines[:8])
                reply = reply[:1800]

            except Exception as e:
                await message.reply(f"AI error: {e}")
                return

            mem.append({"role": "assistant", "content": reply})
            await message.reply(reply)
            return


# -------------------- START BOT --------------------

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents=intents)
bot.run(os.getenv("DISCORD_TOKEN"))
