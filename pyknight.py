import discord
import os
import random
import threading
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import find_dotenv, load_dotenv
from groq import Groq
from discord import app_commands

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


# -------------------- LEADERBOARD PAGINATION --------------------

class LeaderboardView(discord.ui.View):
    def __init__(self, bot, ctx_message: discord.Message, pages: list[str], timeout: int = 60):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx_message = ctx_message
        self.pages = pages
        self.page = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx_message.author.id:
            await interaction.response.send_message(
                "Only the command user can control this leaderboard.",
                ephemeral=True
            )
            return False
        return True

    def _make_embed(self):
        embed = discord.Embed(
            title="🏆 PyKnight Leaderboard",
            description=self.pages[self.page],
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Page {self.page+1}/{len(self.pages)}")
        return embed

    async def _update(self, interaction):
        self.prev_btn.disabled = self.page <= 0
        self.next_btn.disabled = self.page >= len(self.pages)-1
        await interaction.response.edit_message(embed=self._make_embed(), view=self)

    @discord.ui.button(label="⬅️ Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await self._update(interaction)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.pages)-1:
            self.page += 1
        await self._update(interaction)


# -------------------- LOAD ENV --------------------

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)


# -------------------- BOT --------------------

class Bot(discord.Client):

    LEVEL_FILE = "levels.json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree = app_commands.CommandTree(self)

    # -------------------- LEVEL SYSTEM --------------------

    def xp_needed_for_next_level(self, level):
        return 5 + (level * 3)

    def attraction_rank(self, level):
        if level <= 2:
            return "🥶 Friendzone Squire"
        if level <= 5:
            return "😏 Rizz Apprentice"
        if level <= 9:
            return "🔥 Charm Knight"
        if level <= 14:
            return "💘 Heartbreaker"
        return "👑 Rizzlord"

    # -------------------- STORAGE --------------------

    def _load_levels(self):
        if not os.path.exists(self.LEVEL_FILE):
            return {}
        with open(self.LEVEL_FILE, "r") as f:
            return json.load(f)

    def _save_levels(self):
        with open(self.LEVEL_FILE, "w") as f:
            json.dump(self.levels, f, indent=2)

    def _get_user_stats(self, user_id):
        uid = str(user_id)
        if uid not in self.levels:
            self.levels[uid] = {"xp": 0, "level": 0, "aura": 0}
        return self.levels[uid]

    # -------------------- HELP COMMAND --------------------

    async def setup_hook(self):

        @self.tree.command(name="help", description="Show PyKnight commands")
        async def help_cmd(interaction: discord.Interaction):

            embed = discord.Embed(
                title="🛡️ PyKnight Command Panel",
                description="```fix\nUse commands like a civilized human.\n```"
            )

            embed.add_field(
                name="📊 Level System",
                value="```yaml\n!level\n!rank\n!top\n```",
                inline=False
            )

            embed.add_field(
                name="⚔️ Battles",
                value="```yaml\n!pykbattle @user\n```",
                inline=False
            )

            embed.add_field(
                name="🤖 AI Chat",
                value="```yaml\nMention the bot to talk\n```",
                inline=False
            )

            embed.set_footer(text="PyKnight • forged by Silence")

            await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------- READY --------------------

    async def on_ready(self):

        threading.Thread(target=run_health_server, daemon=True).start()

        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

        self.levels = self._load_levels()
        self.battle_cooldowns = {}

        await self.tree.sync()

        print(f"{self.user} is online.")

    # -------------------- LEVEL PROCESS --------------------

    async def _process_level(self, message):

        stats = self._get_user_stats(message.author.id)

        stats["xp"] += 1
        stats["aura"] += 1

        leveled = False
        old_level = stats["level"]

        while stats["xp"] >= self.xp_needed_for_next_level(stats["level"]):
            stats["xp"] -= self.xp_needed_for_next_level(stats["level"])
            stats["level"] += 1
            stats["aura"] += 10
            leveled = True

        if leveled:

            await message.channel.send(
                f"🎉 {message.author.mention} leveled up!\n"
                f"Level {old_level} ➜ {stats['level']}\n"
                f"Rank: {self.attraction_rank(stats['level'])}"
            )

        self._save_levels()

    # -------------------- LEADERBOARD --------------------

    def _get_top(self):

        users = []

        for uid, data in self.levels.items():
            users.append((uid, data["level"], data["aura"]))

        users.sort(key=lambda x: x[2], reverse=True)

        return users

    # -------------------- MESSAGE HANDLER --------------------

    async def on_message(self, message):

        if message.author.bot:
            return

        content = message.content.lower()

        await self._process_level(message)

        # -------------------- LEVEL COMMAND --------------------

        if content.startswith("!level") or content.startswith("!rank"):

            stats = self._get_user_stats(message.author.id)

            await message.reply(
                f"Level: {stats['level']}\n"
                f"XP: {stats['xp']}/{self.xp_needed_for_next_level(stats['level'])}\n"
                f"Aura: {stats['aura']}"
            )

        # -------------------- LEADERBOARD --------------------

        if content.startswith("!top"):

            top = self._get_top()

            medals = ["🥇", "🥈", "🥉"]

            pages = []
            per_page = 10

            for start in range(0, len(top), per_page):

                chunk = top[start:start+per_page]

                lines = []

                for i, (uid, level, aura) in enumerate(chunk, start=start+1):

                    member = message.guild.get_member(int(uid))

                    name = member.display_name if member else f"User {uid}"

                    prefix = medals[i-1] if i <= 3 else f"#{i}"

                    lines.append(f"{prefix} **{name}**\n└ Level {level} • Aura {aura}")

                pages.append("\n\n".join(lines))

            view = LeaderboardView(self, message, pages)

            await message.reply(embed=view._make_embed(), view=view)

        # -------------------- PVP BATTLE --------------------

        if content.startswith("!pykbattle"):

            if not message.mentions:
                await message.reply("⚔️ Example: `!pykbattle @user`")
                return

            opponent = message.mentions[0]

            if opponent.bot or opponent.id == message.author.id:
                await message.reply("Invalid opponent.")
                return

            user_stats = self._get_user_stats(message.author.id)
            opp_stats = self._get_user_stats(opponent.id)

            user_power = user_stats["aura"] + random.randint(1, 60)
            opp_power = opp_stats["aura"] + random.randint(1, 60)

            gain = random.randint(10, 30)

            if user_power > opp_power:

                user_stats["aura"] += gain
                opp_stats["aura"] = max(0, opp_stats["aura"] - gain)

                winner = message.author
                loser = opponent

            else:

                opp_stats["aura"] += gain
                user_stats["aura"] = max(0, user_stats["aura"] - gain)

                winner = opponent
                loser = message.author

            self._save_levels()

            embed = discord.Embed(
                title="⚔️ Aura Battle",
                description=f"{message.author.mention} vs {opponent.mention}",
                color=discord.Color.red()
            )

            embed.add_field(name="Winner", value=winner.mention)
            embed.add_field(name="Aura Transfer", value=f"{gain} aura from {loser.mention}")

            await message.channel.send(embed=embed)

        # -------------------- AI CHAT --------------------

        if self.user in message.mentions:

            prompt = message.content.replace(self.user.mention, "")

            response = self.groq.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile"
            )

            reply = response.choices[0].message.content[:1800]

            await message.reply(reply)


# -------------------- START BOT --------------------

intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents=intents)
bot.run(os.getenv("DISCORD_TOKEN"))
