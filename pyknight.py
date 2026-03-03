import discord
import os
import random
import threading
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import find_dotenv, load_dotenv
from groq import Groq

from discord import app_commands  # ✅ for slash commands

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
    # -------------------- LEVELING CONFIG --------------------
    LEVEL_FILE = "levels.json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ Slash command tree
        self.tree = app_commands.CommandTree(self)

    # Level requirements:
    # Level 1 at 5 msgs, then increases each level.
    # Required messages for next level = 5 + (level * 3)
    def xp_needed_for_next_level(self, current_level: int) -> int:
        return 5 + (current_level * 3)

    def attraction_rank(self, level: int) -> str:
        if level <= 0:
            return "🪨 Unknown NPC"
        if level <= 2:
            return "🥶 Friendzone Squire"
        if level <= 5:
            return "😏 Rizz Apprentice"
        if level <= 9:
            return "🔥 Charm Knight"
        if level <= 14:
            return "💘 Heartbreaker"
        if level <= 20:
            return "👑 Rizzlord"
        return "🌌 Legendary Aura"

    def attraction_score(self, level: int, xp: int) -> int:
        return level * 50 + xp

    # -------------------- LEVELING STORAGE --------------------
    def _load_levels(self):
        if not os.path.exists(self.LEVEL_FILE):
            return {}
        try:
            with open(self.LEVEL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_levels(self):
        try:
            with open(self.LEVEL_FILE, "w", encoding="utf-8") as f:
                json.dump(self.levels, f, indent=2)
        except Exception:
            pass

    def _get_user_stats(self, user_id: int):
        uid = str(user_id)
        if uid not in self.levels:
            self.levels[uid] = {"xp": 0, "level": 0}
        return self.levels[uid]

    # -------------------- SMALL PER-USER MEMORY --------------------
    def _get_user_memory(self, user_id: int):
        if user_id not in self.user_memories:
            self.user_memories[user_id] = []
        return self.user_memories[user_id]

    def _trim_user_memory(self, user_id: int, max_items: int = 16):
        mem = self._get_user_memory(user_id)
        if len(mem) > max_items:
            self.user_memories[user_id] = mem[-max_items:]

    def _user_info(self, user: discord.abc.User) -> str:
        return f"{user.display_name} (@{user.name}, id={user.id})"

    # -------------------- SLASH COMMANDS --------------------
    async def setup_hook(self):
        # /help slash command
        @self.tree.command(name="help", description="Show all PyKnight commands")
        async def help_cmd(interaction: discord.Interaction):
            embed = discord.Embed(
                title="🛡️ PyKnight — Command Panel",
                description=(
                    "```fix\n"
                    "A knight with sarcasm.\n"
                    "Type commands like a civilized human.\n"
                    "```"
                ),
            )

            embed.add_field(
                name="📌 Level System",
                value=(
                    "```yaml\n"
                    "!level  - show your level + XP\n"
                    "!rank   - same as !level\n"
                    "!top    - leaderboard\n"
                    "```"
                ),
                inline=False,
            )

            embed.add_field(
                name="🤖 AI Chat",
                value=(
                    "```yaml\n"
                    "@PyKnight <message>  - talk to the bot\n"
                    "```"
                ),
                inline=False,
            )

            embed.add_field(
                name="🧠 Memory",
                value=(
                    "```fix\n"
                    "I remember your recent chat (small memory).\n"
                    "Restart = memory resets.\n"
                    "```"
                ),
                inline=False,
            )

            embed.set_footer(text="PyKnight • forged by Silence")

            await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------- YOUR ORIGINAL SETUP --------------------
    async def on_ready(self):
        threading.Thread(target=run_health_server, daemon=True).start()

        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # ✅ Your ID (Owner)
        self.OWNER_ID = 1368566182264836157
        self.PROTECTED_IDS = {self.OWNER_ID}

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

        # Level system cache
        self.levels = self._load_levels()
        self._last_save_time = time.time()

        # Per-user memory (RAM only, small)
        self.user_memories = {}
        self.USER_MEMORY_LIMIT = 16

        # ✅ sync slash commands
        try:
            await self.tree.sync()
            print("✅ Slash commands synced.")
        except Exception as e:
            print(f"⚠️ Slash sync failed: {e}")

        print(f"{self.user} is live now!")

    async def _process_leveling(self, message: discord.Message):
        stats = self._get_user_stats(message.author.id)
        stats["xp"] += 1

        leveled_up = False
        old_level = stats["level"]

        while stats["xp"] >= self.xp_needed_for_next_level(stats["level"]):
            stats["xp"] -= self.xp_needed_for_next_level(stats["level"])
            stats["level"] += 1
            leveled_up = True

        now = time.time()
        if leveled_up or (now - self._last_save_time) > 20:
            self._save_levels()
            self._last_save_time = now

        if leveled_up:
            new_level = stats["level"]
            rank_name = self.attraction_rank(new_level)
            score = self.attraction_score(new_level, stats["xp"])

            await message.channel.send(
                f"🎉 {message.author.mention} leveled up! **Level {old_level} → {new_level}**\n"
                f"Attraction Rank: **{rank_name}** | Aura Score: **{score}**"
            )

    def _get_top_users(self, limit=10):
        items = []
        for uid, st in self.levels.items():
            lvl = int(st.get("level", 0))
            xp = int(st.get("xp", 0))
            score = self.attraction_score(lvl, xp)
            items.append((uid, lvl, xp, score))
        items.sort(key=lambda x: (x[1], x[3]), reverse=True)
        return items[:limit]

    async def on_message(self, message: discord.Message):
        print(f"Message from {message.author}: {message.content}")

        if message.author.bot:
            return

        content = (message.content or "").lower()
        is_owner = message.author.id in self.PROTECTED_IDS

        # -------------------- LEVEL SYSTEM (RUNS ON EVERY MESSAGE) --------------------
        if message.guild is not None:
            await self._process_leveling(message)

        # -------------------- LEVEL COMMANDS --------------------
        if content.startswith("!level") or content.startswith("!rank"):
            st = self._get_user_stats(message.author.id)
            lvl = st["level"]
            xp = st["xp"]
            need = self.xp_needed_for_next_level(lvl)
            rank_name = self.attraction_rank(lvl)
            score = self.attraction_score(lvl, xp)

            await message.reply(
                f"📊 {message.author.mention}\n"
                f"Level: **{lvl}**\n"
                f"XP: **{xp}/{need}**\n"
                f"Attraction Rank: **{rank_name}**\n"
                f"Aura Score: **{score}**"
            )
            return

        if content.startswith("!top"):
            top = self._get_top_users(limit=10)
            lines = []
            for i, (uid, lvl, xp, score) in enumerate(top, start=1):
                member = message.guild.get_member(int(uid)) if message.guild else None
                name = member.display_name if member else f"User {uid}"
                lines.append(f"**#{i}** {name} — Lvl **{lvl}** | Aura **{score}**")

            if not lines:
                await message.reply("No data yet. Start typing, NPCs.")
            else:
                await message.reply("🏆 **Top Aura / Levels**\n" + "\n".join(lines[:10]))
            return

        # Detect if message mentions protected user(s)
        mentions_protected = any(u.id in self.PROTECTED_IDS for u in message.mentions)

        # 🚫 Block roasting protected users ONLY if the author is NOT owner
        if ("roast" in content) and mentions_protected and not is_owner:
            await message.reply("Nah. I don’t roast my creator. Pick someone else. 🗿")
            return

        if ("roast" in content) and ("silence" in content) and not is_owner:
            await message.reply("Nah. I don’t roast my creator. Pick someone else. 🗿")
            return

        # -------------------- BASIC RESPONSES --------------------
        if content.startswith("hello"):
            if is_owner:
                await message.channel.send(f"Yo boss {message.author.mention} 🗿")
            else:
                await message.channel.send(f"Hello, Big boi {message.author.mention}. It's PyKnight.")
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

        # -------------------- AI TRIGGER (MENTION BOT) --------------------
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
- Message author: {author_info}
- Roast target (if any): {target_info}
"""

            extra_rule = ""
            if is_owner:
                extra_rule = "\nOWNER MODE: The message author is the owner. Be respectful to the owner. Never roast them."

            user_mem = self._get_user_memory(message.author.id)
            user_mem.append({"role": "user", "content": clean})
            self._trim_user_memory(message.author.id, max_items=self.USER_MEMORY_LIMIT)

            ai_messages = [{"role": "system", "content": self.SYSTEM_PROMPT + extra_rule + extra_context}] + user_mem

            try:
                response = self.groq.chat.completions.create(
                    messages=ai_messages,
                    model="llama-3.3-70b-versatile"
                )

                reply = (response.choices[0].message.content or "").strip()

                lines = [line for line in reply.split("\n") if line.strip()]
                reply = "\n".join(lines[:8])
                reply = reply[:1800]

            except Exception as e:
                await message.reply(f"AI error: {e}")
                return

            user_mem.append({"role": "assistant", "content": reply})
            self._trim_user_memory(message.author.id, max_items=self.USER_MEMORY_LIMIT)

            await message.reply(reply)
            return


# -------------------- START BOT --------------------

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents=intents)
bot.run(os.getenv("DISCORD_TOKEN"))
