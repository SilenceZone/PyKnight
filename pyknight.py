import discord
import os
import random
import threading
import json
import time
import math
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

USERDATA_FILE = "userdata.json"
USERDATA_LOCK = threading.Lock()

def load_userdata():
    with USERDATA_LOCK:
        try:
            with open(USERDATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except Exception:
            return {}

def save_userdata(data):
    with USERDATA_LOCK:
        with open(USERDATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)

def default_user_entry():
    return {"xp": 0, "attraction": 0, "last_gift": 0.0, "last_compliment": 0.0}

# -------------------- BOT CLASS --------------------

class Bot(discord.Client):
    async def on_ready(self):
        threading.Thread(target=run_health_server, daemon=True).start()

        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # ✅ Owner Protection
        self.OWNER_ID = 1368566182264836157
        self.PROTECTED_IDS = {self.OWNER_ID}

        # ✅ Bot gender fixed as BOY
        self.BOT_GENDER = "boy"

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
- desperation behavior.
- creepy tactics.
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

        # -------------------- PER-USER TINY MEMORY --------------------
        self.user_profiles = {}   # user_id -> "boy"/"girl"/"other"
        self.user_memory = {}     # user_id -> deque
        self.MAX_MEMORY_PER_USER = 8
        self.MAX_TOTAL_USERS_IN_MEMORY = 80

        # -------------------- XP / ATTRACTION STORE --------------------
        self.userdata = load_userdata()
        for uid, entry in list(self.userdata.items()):
            if not isinstance(entry, dict):
                self.userdata[uid] = default_user_entry()

        self.GIFT_COOLDOWN = 60.0
        self.COMPLIMENT_COOLDOWN = 30.0

        print(f"{self.user} is live now!")

    # -------------------- XP/LEVEL/ATTRACTION --------------------

    def _ensure_userdata(self, user_id: int):
        sid = str(user_id)
        if sid not in self.userdata:
            self.userdata[sid] = default_user_entry()
            save_userdata(self.userdata)
        return self.userdata[sid]

    def add_xp(self, user_id: int, amount: int):
        entry = self._ensure_userdata(user_id)
        entry["xp"] = int(entry.get("xp", 0)) + int(amount)
        save_userdata(self.userdata)

    def add_attraction(self, user_id: int, amount: int):
        entry = self._ensure_userdata(user_id)
        newval = int(entry.get("attraction", 0)) + int(amount)
        newval = max(0, min(1000, newval))
        entry["attraction"] = newval
        save_userdata(self.userdata)

    def get_xp(self, user_id: int) -> int:
        return int(self._ensure_userdata(user_id).get("xp", 0))

    def get_attraction(self, user_id: int) -> int:
        return int(self._ensure_userdata(user_id).get("attraction", 0))

    def set_last_gift(self, user_id: int, ts: float):
        self._ensure_userdata(user_id)["last_gift"] = ts
        save_userdata(self.userdata)

    def set_last_compliment(self, user_id: int, ts: float):
        self._ensure_userdata(user_id)["last_compliment"] = ts
        save_userdata(self.userdata)

    def can_gift(self, user_id: int) -> bool:
        last = float(self._ensure_userdata(user_id).get("last_gift", 0.0))
        return (time.time() - last) >= self.GIFT_COOLDOWN

    def can_compliment(self, user_id: int) -> bool:
        last = float(self._ensure_userdata(user_id).get("last_compliment", 0.0))
        return (time.time() - last) >= self.COMPLIMENT_COOLDOWN

    def xp_to_level(self, xp: int) -> int:
        return int(math.isqrt(int(xp // 50)))

    def next_level_xp(self, xp: int) -> int:
        lvl = self.xp_to_level(xp)
        return ((lvl + 1) ** 2) * 50

    # -------------------- MEMORY / PROFILE --------------------

    def _get_profile(self, user_id: int) -> str:
        return self.user_profiles.get(user_id, "other")

    def _get_user_mem(self, user_id: int) -> deque:
        if user_id not in self.user_memory:
            self.user_memory[user_id] = deque(maxlen=self.MAX_MEMORY_PER_USER)
        return self.user_memory[user_id]

    def _trim_global_user_memory(self):
        if len(self.user_memory) > self.MAX_TOTAL_USERS_IN_MEMORY:
            overflow = len(self.user_memory) - self.MAX_TOTAL_USERS_IN_MEMORY
            for uid in list(self.user_memory.keys())[:overflow]:
                self.user_memory.pop(uid, None)

    # -------------------- MESSAGE HANDLER --------------------

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content_raw = message.content or ""
        content = content_raw.lower()
        is_owner = message.author.id in self.PROTECTED_IDS

        # -------------------- HELP COMMAND (PUBLIC) --------------------
        if content.startswith("!help"):
            embed = discord.Embed(
                title="PyKnight Commands",
                description="Here are my available commands:",
                color=0x2F3136
            )

            embed.add_field(
                name="👤 Profile System",
                value="`!profile boy`\n`!profile girl`\n`!profile other`",
                inline=False
            )

            embed.add_field(
                name="📊 Level System",
                value="`!rank` → View your stats\n`!rank @user` → View someone else's stats",
                inline=False
            )

            embed.add_field(
                name="💝 Attraction System",
                value="`!gift @user` → +15 attraction (1 min cooldown)\n"
                      "`!compliment @user` → +8 attraction (30s cooldown)",
                inline=False
            )

            embed.add_field(
                name="🤖 AI Interaction",
                value="Mention me to talk.\nFlirt mode activates only if profile = girl.",
                inline=False
            )

            embed.set_footer(text="PyKnight • Calm. Dangerous. Experienced.")
            await message.reply(embed=embed)
            return

        # -------------------- PROFILE COMMAND --------------------
        if content.startswith("!profile"):
            parts = content.split()
            if len(parts) < 2:
                await message.reply("Use: `!profile boy` / `!profile girl` / `!profile other` 🗿")
                return

            choice = parts[1].strip().lower()
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

        # -------------------- RANK COMMAND --------------------
        if content.startswith("!rank"):
            if message.mentions:
                target = message.mentions[0]
                target_id = target.id
                target_name = target.display_name
            else:
                target_id = message.author.id
                target_name = message.author.display_name

            xp = self.get_xp(target_id)
            attraction = self.get_attraction(target_id)
            level = self.xp_to_level(xp)
            next_xp = self.next_level_xp(xp)
            xp_to_next = max(0, next_xp - xp)

            if attraction >= 900:
                grade = "S+"
            elif attraction >= 750:
                grade = "S"
            elif attraction >= 600:
                grade = "A"
            elif attraction >= 400:
                grade = "B"
            elif attraction >= 200:
                grade = "C"
            else:
                grade = "D"

            embed = discord.Embed(title=f"{target_name}'s Profile", color=0x2F3136)
            embed.add_field(name="Level", value=str(level), inline=True)
            embed.add_field(name="XP", value=f"{xp} (Next: {next_xp}, +{xp_to_next} to level)", inline=False)
            embed.add_field(name="Attraction", value=f"{attraction} / 1000 ({grade})", inline=True)
            await message.reply(embed=embed)
            return

        # -------------------- GIFT COMMAND --------------------
        if content.startswith("!gift"):
            if not message.mentions:
                await message.reply("Mention who you want to gift. Usage: `!gift @user`")
                return

            target = message.mentions[0]
            giver_id = message.author.id
            target_id = target.id

            if target_id == giver_id:
                await message.reply("Don’t gift yourself, that's awkward. 💀")
                return

            if not self.can_gift(giver_id):
                await message.reply("You must wait before gifting again. (1 minute cooldown)")
                return

            self.add_attraction(target_id, 15)
            self.add_xp(giver_id, 8)
            self.set_last_gift(giver_id, time.time())
            await message.reply(f"{message.author.mention} gifted {target.mention} — attraction +15.")
            return

        # -------------------- COMPLIMENT COMMAND --------------------
        if content.startswith("!compliment"):
            if not message.mentions:
                await message.reply("Mention who you want to compliment. Usage: `!compliment @user`")
                return

            target = message.mentions[0]
            giver_id = message.author.id
            target_id = target.id

            if not self.can_compliment(giver_id):
                await message.reply("You must wait before complimenting again. (30s cooldown)")
                return

            self.add_attraction(target_id, 8)
            self.add_xp(giver_id, 4)
            self.set_last_compliment(giver_id, time.time())
            await message.reply(f"{message.author.mention} complimented {target.mention} — attraction +8.")
            return

        # -------------------- OWNER ONLY (HIDDEN) --------------------
        if content.startswith("!resetstats"):
            if message.author.id != self.OWNER_ID:
                await message.reply("Only the owner can reset stats.")
                return
            self.userdata = {}
            save_userdata(self.userdata)
            await message.reply("All stats reset.")
            return

        # -------------------- AI TRIGGER (MENTION BOT) --------------------
        if self.user in message.mentions:
            clean = content_raw.replace(self.user.mention, "").strip()
            if not clean:
                clean = "Say something useful."

            profile = self._get_profile(message.author.id)

            extra_rule = ""
            if is_owner:
                extra_rule = "\nOWNER MODE: The message author is the owner. Be respectful."

            flirt_rule = ""
            will_flirt = False
            if profile == "girl" and not is_owner:
                flirt_rule = """
FLIRT MODE:
- Confident, playful teasing.
- a bit when need sexual.
- Never needy.
- Keep it smooth and composed.
"""
                will_flirt = True

            mem = self._get_user_mem(message.author.id)
            mem.append({"role": "user", "content": clean})
            self._trim_global_user_memory()

            self.add_xp(message.author.id, 2)

            ai_messages = [{"role": "system", "content": self.SYSTEM_PROMPT + extra_rule + flirt_rule}] + list(mem)

            try:
                response = self.groq.chat.completions.create(
                    messages=ai_messages,
                    model="llama-3.3-70b-versatile"
                )
                reply = (response.choices[0].message.content or "").strip()
                lines = [l for l in reply.split("\n") if l.strip()]
                reply = "\n".join(lines[:8])
                reply = reply[:1800]
            except Exception as e:
                await message.reply(f"AI error: {e}")
                return

            if will_flirt:
                self.add_attraction(message.author.id, 5)
                self.add_xp(message.author.id, 5)

            mem.append({"role": "assistant", "content": reply})
            await message.reply(reply)
            return


# -------------------- START BOT --------------------

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents=intents)
bot.run(os.getenv("DISCORD_TOKEN"))
