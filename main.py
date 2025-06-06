import os
import asyncio

from dotenv import load_dotenv
from discord.ext.commands import Bot
import discord
from datetime import datetime

bot = Bot(command_prefix='test!',intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

async def main():
    for cog in os.listdir("cogs"):
        if cog.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{cog[:-3]}")
                print(f"Loaded cog {cog}")
            except Exception as e:
                print(f"Failed to load cog {cog}: {e}")
    
    load_dotenv(".env")
    await bot.start(os.getenv("TOKEN"))

if __name__ == "__main__":
    asyncio.run(main())




