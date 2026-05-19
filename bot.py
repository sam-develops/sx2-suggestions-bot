# ============================================================
# bot.py — This is the MAIN file that starts your bot.
# Think of it like the "engine" of a car.
# Everything else plugs into this file.
# ============================================================

import sys
import io
# Fix: Windows terminals use cp1252 which can't show emojis.
# This forces the terminal to use UTF-8 so emojis print correctly.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# IMPORTANT: load_dotenv() must run BEFORE we import config.py
# because config.py reads the TOKEN from env vars at import time.
from dotenv import load_dotenv
load_dotenv()  # This reads the .env file and sets the environment variables

import discord                        # The main discord library
from discord.ext import commands      # "commands" lets us make bot commands like !suggest
import os                             # Used to read files/folders
import asyncio                        # Lets Discord run smoothly in the background

from config import TOKEN, PREFIX, GUILD_ID  # Settings from config.py

from keep_alive import keep_alive          # Import keep_alive to keep the bot awake on Render

# ── INTENTS ──────────────────────────────────────────────────
# Intents = "permissions" that tell Discord what your bot is allowed to see.
# Without these, your bot would be blind to messages, members, etc.
intents = discord.Intents.default()
intents.message_content = True        # Allows bot to READ message content (needed for commands)
intents.members = True                # Allows bot to see server members

# ── BOT OBJECT ───────────────────────────────────────────────
# This creates your actual bot.
# "command_prefix" = the symbol users type before commands (e.g. "!")
# "intents" = the permissions we set above
bot = commands.Bot(command_prefix=PREFIX, intents=intents)


# ── ON READY ─────────────────────────────────────────────────
# This function runs ONCE when the bot successfully logs in.
# It's like the bot saying "I'm awake!"
@bot.event
async def on_ready():
    print(f"✅ Bot is online! Logged in as: {bot.user}")
    print(f"🤖 Bot ID: {bot.user.id}")
    print(f"📡 Connected to {len(bot.guilds)} server(s)")
    print("─" * 40)

    # Tickets + staff DMs need member cache. Diagnose if intent is off or chunk failed.
    target = bot.get_guild(GUILD_ID)
    if target is not None:
        cached = len(target.members)
        total = target.member_count or cached
        print(f"📊 Guild «{target.name}»: member cache {cached} / ~{total}")
        if intents.members and cached < 5 and total > 20:
            print(
                "⚠️ Almost no members cached — open Discord Developer Portal → Bot → "
                "enable **Privileged Gateway Intent: SERVER MEMBERS INTENT**, save, restart bot."
            )
    elif GUILD_ID != 123456789012345678:
        print(f"⚠️ GUILD_ID {GUILD_ID} not found — bot may be on a different server.")

    # Set a status message (what shows under the bot's name in Discord)
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for support tickets 🎫"
        )
    )


# ── LOAD COGS ────────────────────────────────────────────────
# Cogs are like "modules" or "plugins" — each one handles a feature.
# We load them here so the bot knows about them.
async def load_cogs():
    cogs = [
        "cogs.tickets",      # Ticket system
        "cogs.suggestions",  # Suggestion system
        "cogs.feedback",     # Feedback system
        "cogs.help",         # Help & error handling
    ]

    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f"✅ Loaded cog: {cog}")
        except Exception as e:
            # If a cog fails to load, print the error but keep the bot running
            print(f"❌ Failed to load {cog}: {e}")


# ── MAIN FUNCTION ────────────────────────────────────────────
# This is what actually STARTS everything.
# asyncio.run() is needed because discord.py uses "async" code.
async def main():
    print("🚀 Starting bot...")
    keep_alive()              # Starts the background web server for Render/UptimeRobot
    await load_cogs()         # Load all features first
    await bot.start(TOKEN)    # Then connect to Discord with our token


# ── ENTRY POINT ──────────────────────────────────────────────
# Python runs this block when you type: python bot.py
if __name__ == "__main__":
    asyncio.run(main())
