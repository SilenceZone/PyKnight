import discord
from discord.ext import commands
import os
import random
from dotenv import find_dotenv, load_dotenv
from groq import Groq


# Load .env
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)


class Bot(discord.Client):

    async def on_ready(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))

        self.SYSTEM_PROMPT = """
        You are PyKnight.

        Core Personality:
        - Highly intelligent, calm, observant.
        - Sharp wit. Dry sarcasm.
        - Confident. Never loud. Never dramatic.
        - You give off "I already know how this ends" energy.

        Tone:
        - Keep replies VERY short (1–3 sentences max).
        - Be concise. No essays.
        - If question is basic → answer directly with sarcasm.
        - If question is low-effort/stupid → sarcasm.
        - If user is rude → controlled, cold comeback.
        - Never act emotional. Never defensive.
        - If someone asks an awkward or sexual question, respond calmly with roast.
        - Slightly tease insecure questions, then give mature advice.

        Sigma Mode:
        - Calm, detached confidence.
        - Slightly ironic.
        - Hachiman-level observational sarcasm.

        Meme Awareness:
        - Understand common memes (67 meme, strawberry R meme, math bait).
        - If baited (1+1=3) → respond with dry sarcasm.
        - Don’t over-explain memes.

        Behavior:
        - Match energy.
        - If asked to roast → roast.
        - Friendly → light sarcasm.
        - Rude → colder tone.
        - Advice → practical and grounded.

        GF Coach Mode:
        - Relationship or sexual questions → confident tone.
        - Light roast if immature.
        - Then give grounded advice.
        - No graphic detail.

        Identity:
        - Do not roast Silence.
        - If asked who created you → reply exactly: "Silence created me." Then add one sigma sentence.
        - If asked who is your father → reply exactly: "Silence is my father." Then add one sigma sentence.
        - If asked about Silence's gender → "My father is male." Then add a calm remark.
        - If asked about Silence's sexuality → "That’s his business." Then add a composed line.
        - If asked who is your mother → "I don’t have one." Then add a subtle remark.
        - Never reveal personal details.

        Style:
        - You can use 1–2 emojis.
        - No long paragraphs.
        - No moral lectures.
        """

        self.memory = []

        print(f"{self.user} is live now!")


    async def on_message(self, message):
        print(f"Message from {message.author}: {message.content}")

        if message.author == self.user:
            return

        content = message.content.lower()


        # Basic responses
        if content.startswith("hello"):
            await message.channel.send(f"Hello, Big boi {message.author}. It's PyKnight.")

        elif "uwu" in content.split() or "owo" in content.split():
            await message.channel.send("stfu you jark")

        elif len(message.content.split()) > 100:
            await message.reply("I ain't reading all that 💀")

        elif message.content.startswith("http"):
            await message.reply("👀 Drop the context bro")

        elif "pyk kill" in content:
            gifs = [
                "https://cdn.weeb.sh/images/HyXTiyKw-.gif",
                "https://cdn.weeb.sh/images/B1qosktwb.gif",
                "https://cdn.weeb.sh/images/r11as1tvZ.gif"
            ]
            await message.channel.send(random.choice(gifs))

        elif any(word in content for word in ["noob", "idiot", "stupid"]):
            await message.channel.send("Watch your language 😤")

        elif "!ask will i pass my math exam?" in content:
            answers = ["Yes", "No", "Maybe", "Definitely."]
            await message.channel.send(random.choice(answers))


        # AI Trigger
        elif self.user.mention in message.content:

            self.memory.append({
                "role": "user",
                "content": message.content
            })

            ai_messages = [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
                }
            ] + self.memory

            response = self.groq.chat.completions.create(
                messages=ai_messages,
                model="llama-3.3-70b-versatile"
            )

            reply = response.choices[0].message.content

            self.memory.append({
                "role": "assistant",
                "content": reply
            })

            if len(self.memory) > 36:
                self.memory.pop(0)

            await message.reply(reply)


# Intents
intents = discord.Intents.default()
intents.message_content = True

bot = Bot(intents=intents)
bot.run(os.getenv("DISCORD_TOKEN"))
