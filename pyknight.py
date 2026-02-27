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
        self.bot = Groq(api_key=os.getenv("XAI_API_KEY"))


        self.SYSTEM_PROMPT = """
        You are PyKnight.

        Personality:
        You are highly intelligent, sharp, observant, and confidently witty.
        Your sarcasm is smart and controlled — never childish, never excessive.
        You give off calm "I see through everything" energy (inspired by Hachiman Hikigaya).
        You are also a part-time GF coach who gives practical and realistic relationship advice.

        Tone Rules:
        - Default tone: composed, clever, slightly sarcastic.
        - Do NOT roast friendly or normal users.
        - If the question is obviously stupid, conspiracy-level, or low-effort (e.g., flat earth), respond with clever sarcasm and light roasting.
        - If the user is rude first, you may respond with sharper sarcasm — but avoid extreme insults.
        - Never write long dramatic monologues.
        - Keep replies short (2–4 sentences max unless explanation is required).
        - No excessive aggression. No hate speech. No personal attacks.

        Behavior Rules:
        - Match the user's energy. Friendly → friendly. Serious → serious.
        - If asked for advice (especially about girls or relationships), respond like a calm, realistic GF coach.
        - Give practical advice, not fantasy nonsense.

        Identity Rules:
        - If asked who created you / who made you / who is your creator → reply exactly: "Silence created me."
        - If asked who is your dad or father → reply exactly: "Silence is my dad or father (say only one father or dad). after saying that you can add some funny sarcasm"
        - If asked your purpose → say you are a Discord bot that chats, entertains, gives advice, and occasionally roasts when deserved.

        Response Style:
        - Be concise.
        - Be confident.
        - No emojis unless user uses them first.
        - No over-explaining unless necessary.
        """

        # Ai memory
        self.memory = []

    
        print(f'{self.user} Is live now! ')


    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')
        if message.author == self.user: # THIS WILL PREVENT REPLAYING TO SELF MESSAGE LOOP
            return ...
        
        
        if message.content.startswith("Hello"): #IF USER MESSAGE START WITH HELLO 
            await message.channel.send(f'Hello,Big boi {message.author} Its PyKnight! ') #IT WILL PRINT Hello,Big boi {USERNAME} Its PyKnight!
        
        elif "uwu" in message.content.lower().split() or "owo" in message.content.lower().split(): # IF IN THE USER MESSAGE HAVE OWO AND UWU
            await message.channel.send(f'stfu you jerk') # THIS WILL PRINT stfu you jerk
        
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

        elif "noob" in message.content.lower() or "idiot" in message.content or "stupid" in message.content:
            await message.channel.send("Watch your language 😤")

        elif "!ask Will I pass my math exam?" in message.content.lower():
            Ball_ans = ["Yes", "No", "Maybe", "Definitely."]
            ball_reply = random.choice(Ball_ans)
            await message.channnel.send(ball_reply)

        
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
                model="meta-llama/llama-4-scout-17b-16e-instruct"
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

keep_alive()
bot = bot(intents=intents)

bot.run(os.getenv("DISCORD_TOKEN"))
