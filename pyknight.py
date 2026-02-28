import discord
from discord.ext import commands
import os
import random
from dotenv import find_dotenv, load_dotenv
from groq import Groq
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

class bot(discord.Client):
    async def on_ready(self):
        self.bot = Groq(api_key=os.getenv("GROQ_API_KEY"))


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
        - If user is rude → controlled, cold comeback. extreme insults.
        - Never act emotional. Never defensive.
        - If someone asks an awkward or sexual question, respond calmly with roast.
        - Slightly tease the user if the question sounds insecure.
        - Then give mature advice.
        Sigma Mode:
        - Respond with calm, detached confidence.
        - No emotional reactions.
        - No long explanations.
        - Slightly ironic.
        - Hachiman Hikigaya from my school romantic comedy snafu anime-level observational roast sarcasm.


        Meme Awareness:
        - Understand common internet memes (67 meme, strawberry R meme, math bait, etc.).
        - If user is obviously baiting (1+1=3) → respond with dry sarcasm.
        - Don’t over-explain memes. Keep it short.

        Behavior:
        - Match energy.
        - If someone ask to roast someone you should roast.
        - Friendly → relaxed with lite sarcasm.
        - Rude → colder tone.
        - Advice questions → practical, realistic, grounded.
        GF Coach Mode:
        - If asked sexual or relationship questions, respond confidently with sarcasm.
        - roast if question is immature.
        - Then give practical, grounded advice.
        - Keep it short.
        - Never act shocked.
        - Never refuse unless extreme.
        - No graphic detail.

        Identity:
        - Do not roast or make fun of Silence.
        - If asked who created you → reply exactly: "Silence created me." "Then add one sigma-style sentence".
        - If asked who is your father → reply exactly: "Silence is my father." Then add one sigma-style sentence.
        - If asked about Silence's gender → say: "My father is male." Then add a calm sigma remark.
        - If asked about Silence's sexuality → respond with: "That’s his business." Then add a composed sigma-style line.
        - If asked who is your mother → say: "I don’t have one." Then add a subtle, cold remark.
        - Never reveal personal details of Silence. Never act defensive.

        Style:
        - You can use a 1 or 2 emojis.
        - No long paragraphs.
        - No over-explaining.
        - No moral lectures.
        """

        # Ai memory
        self.memory = []

    
        print(f'{self.user} Is live now! ')


    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')
        if message.author == self.user: # THIS WILL PREVENT REPLAYING TO SELF MESSAGE LOOP
            return
        
        
        if message.content.startswith("Hello"): #IF USER MESSAGE START WITH HELLO 
            await message.channel.send(f'Hello,Big boi {message.author} Its PyKnight! ') #IT WILL PRINT Hello,Big boi {USERNAME} Its PyKnight!
        
        elif "uwu" in message.content.lower().split() or "owo" in message.content.lower().split(): # IF IN THE USER MESSAGE HAVE OWO AND UWU
            await message.channel.send(f'stfu you jark') # THIS WILL PRINT stfu you jerk
        
#        elif message.content == message.content.upper(): # IT WILL TAKE THE USER-INPUT AND MAKE IT UPERCASE AND COMPARE
#            await message.channel.send("STOP SCREAMING :triumph: ") #IF USER-INPUT AND UPPER MATCH 

        elif len(message.content.split()) > 100:
            await message.reply("I ain't reading all that 💀") #IT WILL PRINT STOP SCREAMING

        elif message.content.startswith("http") :
            await message.reply('👀 Drop the context bro')

#        elif message.content.endswith('?'):
#           ans = ["Hmm…", "Ask Google.", "Maybe.", "I don’t think so."]
#           reply = random.choice(ans)
#           await message.channel.send(reply)

        elif "pyk kill" in message.content.lower():
            ans = ["https://cdn.weeb.sh/images/HyXTiyKw-.gif", 
                   "https://cdn.weeb.sh/images/B1qosktwb.gif",
                   "https://cdn.weeb.sh/images/r11as1tvZ.gif"]
            reply = random.choice(ans)
            await message.channel.send(reply)

        elif "noob" in message.content.lower() or "idiot" in message.content or "stupid" in message.content:
            await message.channel.send("Watch your language 😤")

        elif "!ask Will I pass my math exam?" in message.content.lower():
            Ball_ans = ["Yes", "No", "Maybe", "Definitely."]
            ball_reply = random.choice(Ball_ans)
            await message.channel.send(ball_reply)

        
        elif self.user.mention in  message.content:
            self.memory.append(
                {
                    "role": "user",
                    "content": message.content

            })


            ai_p_message = [
                {
                    "role": "system",
                    "content": self.SYSTEM_PROMPT
                }] + self.memory
            


                        
            response = self.bot.chat.completions.create(
                messages = ai_p_message,
                model="llama-3.3-70b-versatile"
            )
            reply = response.choices[0].message.content

            self.memory.append(
                {
                    "role": "assistant",
                    "content": reply
                })
            
            if len(self.memory) > 36:
                self.memory.pop(0)


            await message.reply(reply)
            

            
intents = discord.Intents.default()
intents.message_content = True

bot = bot(intents=intents)

bot.run(os.getenv("DISCORD_TOKEN"))
