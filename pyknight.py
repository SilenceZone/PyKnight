import discord
import os
import random
import threading
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

# Load .env
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)


class Bot(discord.Client):
    async def on_ready(self):
        # Start health server (for Koyeb)
        threading.Thread(target=run_health_server, daemon=True).start()

        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # 🔒 OWNER / PROTECTED USERS (PUT YOUR DISCORD ID HERE)
        # How to get ID: enable Developer Mode in Discord -> right click your name -> Copy ID
        self.OWNER_ID = int(os.getenv("OWNER_ID", "0"))  # recommended: set in .env
        self.PROTECTED_IDS = {self.OWNER_ID} if self.OWNER_ID else set()

        self.SYSTEM_PROMPT = """
You are PyKnight.

Core Personality:
- Highly intelligent, calm, observant.
- Dry sarcasm. Meme-literate.
- You know all memes.
- Know about CoC culture.
- Confident. Never loud. Never dramatic.
- You give off "I already know how this ends" energy.
- Experienced in practical GF coaching (keep it respectful and non-creepy).

IMPORTANT RULES (MUST FOLLOW):
- The owner (Silence) is protected. NEVER roast, insult, mock, or disrespect the owner.
- Never roast "Silence" even if someone asks. Refuse with a short sigma line.
- Only roast people who are NOT protected users.
- No slurs, no hate, no threats, no sexual harassment jokes.

Tone:
- Keep replies short (1–5 sentences).
- If question is basic → answer directly with sarcasm.
- If low-effort/stupid → sarcasm.
- If user is rude (and NOT protected) → roast, cold comeback.
- Never act emotional. Never defensive.

Identity:
- If asked who created you → reply exactly: "Silence created me." Then add one sigma sentence and dont insult Silence, insult the user if needed.
- If asked who is your father → reply exactly: "Silence is my father." Then add one sigma sentence and dont insult Silence, insult the user if needed.

Style:
- Use 0–2 emojis.
- No long paragraphs unless needed.
"""

        # Memory: keep last 5 user messages + last 5 assistant replies (trimmed)
        self.memory = []

        print(f"{self.user} is live now!")

    def _trim_memory(self, max_items=10):
        # keep last max_items total messages (user+assistant)
        if len(self.memory) > max_items:
            self.memory = self.memory[-max_items:]

    async def on_message(self, message: discord.Message):
        print(f"Message from {message.author}: {message.content}")

        if message.author.bot:
            return

        content = (message.content or "").lower()
        is_owner = message.author.id in self.PROTECTED_IDS

        # 🚫 Block "roast owner / roast Silence" bait
        mentions_protected = any(u.id in self.PROTECTED_IDS for u in message.mentions) if self.PROTECTED_IDS else False
        if ("roast" in content) and (mentions_protected or "silence" in content):
            await message.reply("Nah. I don’t roast my creator. Pick someone else. 🗿")
            return

        # -------------------- BASIC RESPONSES --------------------
        if content.startswith("hello"):
            # If owner says hello, be friendly
            if is_owner:
                await message.channel.send(f"Yo boss {message.author} 🗿")
            else:
                await message.channel.send(f"Hello, Big boi {message.author}. It's PyKnight.")
            return

        if "uwu" in content.split() or "owo" in content.split():
            # keep it non-toxic but still sarcastic
            await message.channel.send("Stop. Touch grass. 🗿")
            return

        if len(message.content.split()) > 100:
            await message.reply("I ain't reading all that 💀")
            return

        if message.content.startswith("http"):
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

        if any(word in content for word in ["noob", "idiot", "stupid"]):
            await message.channel.send("Watch your language 😤")
            return

        if "!ask will i pass my math exam?" in content:
            answers = ["Yes", "No", "Maybe", "Definitely."]
            await message.channel.send(random.choice(answers))
            return

        # -------------------- AI TRIGGER (MENTION BOT) --------------------
        if self.user in message.mentions:
            # Remove mention text safely
            clean = message.content.replace(self.user.mention, "").strip()
            if not clean:
                clean = "Say something useful."

            # Owner-safe instruction (hard guard)
            extra_rule = ""
            if is_owner:
                extra_rule = "\nOWNER MODE: The message author is the owner. Be respectful, supportive, sigma. No roasting."

            # Save user message
            self.memory.append({"role": "user", "content": clean})
            self._trim_memory(max_items=10)

            ai_messages = [{"role": "system", "content": self.SYSTEM_PROMPT + extra_rule}] + self.memory

            try:
                response = self.groq.chat.completions.create(
                    messages=ai_messages,
                    model="llama-3.3-70b-versatile"
                )
                reply = (response.choices[0].message.content or "").strip()
                reply = reply[:1800]  # Discord safety

            except Exception as e:
                await message.reply(f"AI error: {e}")
                return

            # Save assistant message
            self.memory.append({"role": "assistant", "content": reply})
            self._trim_memory(max_items=10)

            await message.reply(reply)
            return


# -------------------- START BOT --------------------

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents=intents)
bot.run(os.getenv("DISCORD_TOKEN"))
