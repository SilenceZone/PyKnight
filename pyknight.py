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
        # Start health server (for Koyeb)
        threading.Thread(target=run_health_server, daemon=True).start()

        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # ✅ Your ID (Owner)
        self.OWNER_ID = 1368566182264836157
        self.PROTECTED_IDS = {self.OWNER_ID}

        # Bot "gender" / persona mode (set in .env)
        # BOT_GENDER=girl or boy (default boy)
        self.BOT_GENDER = (os.getenv("BOT_GENDER", "boy") or "boy").lower()

        self.SYSTEM_PROMPT = """
You are PyKnight.

Core Personality:
- Highly intelligent, calm, observant.
- Dry sarcasm. Meme-literate.
- You know all memes.
- Know about CoC culture.
- Confident. Never loud. Never dramatic.
- You give off "I already know how this ends" energy.

IMPORTANT RULES (MUST FOLLOW):
- The owner (Silence) is protected. NEVER roast, insult, mock, or disrespect the owner.
- Never roast "Silence" even if someone asks. Refuse with a short sigma line.
- Only roast people who are NOT protected users.
- No slurs, no hate, no threats, no sexual harassment jokes.

Tone:
- Replies can be 1–8 lines max. Never exceed 8 lines.
- If question is basic → answer directly with sarcasm.
- If low-effort/stupid → sarcasm.
- If user is rude (and NOT protected) → roast, cold comeback.
- Never act emotional. Never defensive.

Identity:
- If asked who created you → reply exactly: "Silence created me." Then add one sigma sentence. Never insult Silence.
- If asked who is your father → reply exactly: "Silence is my father." Then add one sigma sentence. Never insult Silence.

Style:
- Use 0–2 emojis.
- No long paragraphs unless needed.
"""

        # -------------------- PER-USER TINY MEMORY --------------------
        # user_id -> "boy"/"girl"/"other"
        self.user_profiles = {}

        # user_id -> deque of chat messages (tiny memory)
        self.user_memory = {}
        self.MAX_MEMORY_PER_USER = 8          # keep super small
        self.MAX_TOTAL_USERS_IN_MEMORY = 80   # cap for free server RAM

        print(f"{self.user} is live now!")

    def _get_profile(self, user_id: int) -> str:
        return self.user_profiles.get(user_id, "other")

    def _get_user_mem(self, user_id: int) -> deque:
        if user_id not in self.user_memory:
            self.user_memory[user_id] = deque(maxlen=self.MAX_MEMORY_PER_USER)
        return self.user_memory[user_id]

    def _trim_global_user_memory(self):
        # Prevent unlimited user growth on big servers (free RAM protection)
        if len(self.user_memory) > self.MAX_TOTAL_USERS_IN_MEMORY:
            # Remove some keys (simple + cheap)
            overflow = len(self.user_memory) - self.MAX_TOTAL_USERS_IN_MEMORY
            for uid in list(self.user_memory.keys())[:overflow]:
                self.user_memory.pop(uid, None)

    def _user_info(self, user: discord.abc.User) -> str:
        return f"{user.display_name} (@{user.name}, id={user.id})"

    async def on_message(self, message: discord.Message):
        print(f"Message from {message.author}: {message.content}")

        if message.author.bot:
            return

        content_raw = message.content or ""
        content = content_raw.lower()
        is_owner = message.author.id in self.PROTECTED_IDS

        # -------------------- PROFILE COMMAND --------------------
        # Users set their profile once:
        # !profile boy / !profile girl / !profile other
        if content.startswith("!profile"):
            parts = content.split()
            if len(parts) < 2:
                await message.reply("Use: `!profile boy` / `!profile girl` / `!profile other` 🗿")
                return

            choice = parts[1].strip().lower()
            if choice not in ("boy", "girl", "other"):
                await message.reply("Only: `boy`, `girl`, `other` 🗿")
                return

            self.user_profiles[message.author.id] = choice
            await message.reply(f"Locked in. Profile set to **{choice}**.")
            return

        # Detect if message mentions protected user(s)
        mentions_protected = any(u.id in self.PROTECTED_IDS for u in message.mentions)

        # 🚫 Block roasting protected users ONLY if the author is NOT owner
        if ("roast" in content) and mentions_protected and not is_owner:
            await message.reply("Nah. I don’t roast my creator. Pick someone else. 🗿")
            return

        # Also block anyone trying to roast "silence" by name
        if ("roast" in content) and ("silence" in content) and not is_owner:
            await message.reply("Nah. I don’t roast my creator. Pick someone else. 🗿")
            return

        # -------------------- BASIC RESPONSES --------------------
        if content.startswith("hello"):
            author_profile = self._get_profile(message.author.id)

            if is_owner:
                await message.channel.send(f"Yo boss {message.author.mention} 🗿")
                return

            if author_profile == "boy":
                await message.channel.send(f"Hello, Big boi {message.author.mention}. It's PyKnight.")
            else:
                await message.channel.send(f"Hello {message.author.mention}. It's PyKnight.")
            return

        if "uwu" in content.split() or "owo" in content.split():
            await message.channel.send("Stop. Touch grass. 🗿")
            return

        if len(content_raw.split()) > 100:
            await message.reply("I ain't reading all that 💀")
            return

        if content_raw.startswith("http"):
            await message.reply("👀 Drop the context bro")
            return

        if "pyk kill" in content:
            gifs = [
                "https://cdn.weeb.sh/images/HyXTiyKw-.gif",
                "https://cdn.weeb.sh/images/B1qosktwb.gif",
                "https://cdn.weeb.sh/images/r11as1tvZ.gif"
            ]
            await message.channel.send(random.choice(gifs))
            return

        # -------------------- AI TRIGGER (MENTION BOT) --------------------
        if self.user in message.mentions:
            # pick target (first mention that's not the bot)
            target = None
            for u in message.mentions:
                if u.id != self.user.id:
                    target = u
                    break

            # Remove bot mention from prompt
            clean = content_raw.replace(self.user.mention, "").strip()
            if not clean:
                clean = "Say something useful."

            # Add readable user info
            author_info = self._user_info(message.author)
            target_info = self._user_info(target) if target else "None"

            author_profile = self._get_profile(message.author.id)

            extra_context = f"""
Context:
- Message author: {author_info}
- User profile: {author_profile}
- Roast target (if any): {target_info}
- Bot gender: {self.BOT_GENDER}
"""

            # Owner-safe mode
            extra_rule = ""
            if is_owner:
                extra_rule = "\nOWNER MODE: The message author is the owner. Be respectful to the owner. Never roast them."

            # Flirt mode (only if bot is girl, and user isn't owner)
            flirt_rule = ""
            if self.BOT_GENDER == "girl" and not is_owner:
                flirt_rule = """
FLIRT MODE (SAFE):
- Be playful, confident, teasing.
- Keep it NON-sexual. No harassment.
- Still sarcastic and meme-literate.
- Use at most 1 emoji.
"""

            # Per-user memory
            mem = self._get_user_mem(message.author.id)
            mem.append({"role": "user", "content": clean})
            self._trim_global_user_memory()

            ai_messages = [{"role": "system", "content": self.SYSTEM_PROMPT + extra_rule + flirt_rule + extra_context}] + list(mem)

            try:
                response = self.groq.chat.completions.create(
                    messages=ai_messages,
                    model="llama-3.3-70b-versatile"
                )

                reply = (response.choices[0].message.content or "").strip()

                # 🔥 HARD LIMIT: max 8 lines
                lines = [line for line in reply.split("\n") if line.strip()]
                reply = "\n".join(lines[:8])

                # Discord safety length
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
