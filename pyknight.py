import discord
import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import find_dotenv, load_dotenv
from groq import Groq

# -------------------- RENDER HEALTH CHECK SERVER --------------------

class HealthHandler(BaseHTTPRequestHandler):

    # stop console spam
    def log_message(self, format, *args):
        return

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")


def run_health_server():
    port = int(os.getenv("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    server.serve_forever()


# start health server BEFORE bot connects
threading.Thread(target=run_health_server, daemon=True).start()

# --------------------------------------------------------------------

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)


class Bot(discord.Client):

    async def on_ready(self):

        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

        self.OWNER_ID = 1368566182264836157
        self.PROTECTED_IDS = {self.OWNER_ID}

        self.SYSTEM_PROMPT = """
You are PyKnight.

Core Personality:
- Highly intelligent, calm, observant.
- Dry sarcasm. Meme-literate.
- Confident. Never loud.

IMPORTANT RULES:
- Never roast Silence.
- Owner is protected.
- Roast only non-protected users.

Tone:
- 1–8 lines max.
- Sarcastic but controlled.

Identity:
- If asked who created you → "Silence created me."
"""

        self.memory = []

        print(f"{self.user} is live now!")


    def _trim_memory(self, max_items=10):
        if len(self.memory) > max_items:
            self.memory = self.memory[-max_items:]


    def _user_info(self, user: discord.abc.User) -> str:
        return f"{user.display_name} (@{user.name}, id={user.id})"


    async def on_message(self, message):

        if message.author.bot:
            return

        content = (message.content or "").lower()
        is_owner = message.author.id in self.PROTECTED_IDS

        mentions_protected = any(u.id in self.PROTECTED_IDS for u in message.mentions)

        if ("roast" in content) and mentions_protected and not is_owner:
            await message.reply("Nah. I don’t roast my creator. 🗿")
            return

        if content.startswith("hello"):
            if is_owner:
                await message.channel.send(f"Yo boss {message.author.mention} 🗿")
            else:
                await message.channel.send(f"Hello {message.author.mention}. It's PyKnight.")
            return

        if "uwu" in content.split() or "owo" in content.split():
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


        # ---------------- AI TRIGGER ----------------

        if self.user in message.mentions:

            target = None
            for u in message.mentions:
                if u.id != self.user.id:
                    target = u
                    break

            clean = message.content.replace(self.user.mention, "").strip()
            if not clean:
                clean = "Say something useful."

            author_info = self._user_info(message.author)
            target_info = self._user_info(target) if target else "None"

            extra_context = f"""
Context:
Author: {author_info}
Target: {target_info}
"""

            self.memory.append({"role": "user", "content": clean})
            self._trim_memory()

            ai_messages = [{
                "role": "system",
                "content": self.SYSTEM_PROMPT + extra_context
            }] + self.memory

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

            self.memory.append({"role": "assistant", "content": reply})
            self._trim_memory()

            await message.reply(reply)


# ---------------- START BOT ----------------

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents=intents)
bot.run(os.getenv("DISCORD_TOKEN"))
