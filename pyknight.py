import discord
from discord.ext import commands
import os
from dotenv import find_dotenv, load_dotenv

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

class bot(discord.Client):
    async def on_ready(self):
        print(f'{self.user} Is live now! ')

    async def on_message(self, message):
        print(f'Message from {message.author}: {message.content}')
        if message.author == self.user: # THIS WILL PREVENT REPLAYING TO SELF MESSAGE LOOP
            return ...
        
        user_id = message.author.id
        
        if message.content.startswith("Hello"): #IF USER MESSAGE START WITH HELLO 
            await message.channel.send(f'Hello,Big boi {message.author} Its PyKnight! ') #IT WILL PRINT Hello,Big boi {USERNAME} Its PyKnight!
        elif "uwu" in message.content.lower().split() or "owo" in message.content.lower().split(): # IF IN THE USER MESSAGE HAVE OWO AND UWU
            await message.channel.send(f'stfu you jerk') # THIS WILL PRINT stfu you jerk
        elif message.content == message.content.upper(): # IT WILL TAKE THE USER-INPUT AND MAKE IT UPERCASE AND COMPARE
            await message.channel.send("STOP SCREAMING :triumph: ") #IF USER-INPUT AND UPPER MATCH 
            await message.reply("I ain't reading all that 💀") #IT WILL PRINT STOP SCREAMING
        

intents = discord.Intents.default()
intents.message_content = True

bot = bot(intents=intents)

bot.run(os.getenv("DISCORD_TOKEN"))