# ============================================================
# config.py — This file stores all your bot's settings.
# Think of it like a "settings panel" for your bot.
#
# ⚠️ IMPORTANT: Never share this file publicly!
#    Your TOKEN is like a password — keep it secret.
# ============================================================


import os

# ── BOT TOKEN ────────────────────────────────────────────────
# This is your bot's secret password to log into Discord.
# You get it from: https://discord.com/developers/applications
# → Your App → Bot → Token → Copy
TOKEN = os.getenv("TOKEN")


# ── COMMAND PREFIX ───────────────────────────────────────────
# This is the symbol users type before commands.
# Example: If PREFIX = "!", users type !suggest, !help, etc.
PREFIX = "!"


# ── SERVER / GUILD ID ────────────────────────────────────────
# Your Discord server's unique ID.
# How to get it: Right-click your server name → Copy Server ID
# (You need Developer Mode ON: User Settings → Advanced → Developer Mode)
GUILD_ID = 1495398725722570903  # ← Replace with your actual server ID


# ── CHANNEL IDs ──────────────────────────────────────────────
# These are the channels the bot will use.
# How to get a channel ID: Right-click the channel → Copy Channel ID

# The channel where suggestions will be posted
SUGGESTION_CHANNEL_ID = (
    1502985136520822914  # ← Replace with your suggestions channel ID
)

# The channel where feedback will be posted (can be same or different to suggestions)
FEEDBACK_CHANNEL_ID = 1502987118853619893  # ← Replace with your feedback channel ID

# The category under which new ticket channels will be created
# How to get category ID: Right-click the category → Copy ID
TICKET_CATEGORY_ID = 1502427703935242331  # ← Replace with your ticket category ID

# Optional: category for NEW tickets (first stage).
# If left as the default placeholder, the bot falls back to TICKET_CATEGORY_ID.
TICKET_NEW_CATEGORY_ID = 1502427760012951653

# Optional: category for WORKING/PENDING tickets (staff currently handling).
# If left as the default placeholder, tickets stay in the new-ticket category.
TICKET_WORKING_CATEGORY_ID = 1502427789142523944

# Channel where resolved ticket logs will be posted before ticket channel is deleted
RESOLVED_TICKETS_CHANNEL_ID = 1502427839209668678


# ── ROLE IDs ─────────────────────────────────────────────────
# Staff role: members with this role can see ticket channels (optional).
# How to get a role ID: Server Settings → Roles → Right-click role → Copy ID
# Must be a single integer — do NOT wrap in parentheses with a trailing comma
# or Python turns it into a tuple and roles/DMs will silently stop working.
STAFF_ROLE_ID = 1502438234062323883  # staff role — must be one integer, no ( ) wrapping

# Members with this role get a DM when someone opens a ticket (optional; falls back to STAFF_ROLE_ID if set).
# Discord cannot DM a role — the bot DMs each member who currently has this role.
TICKET_ADMIN_NOTIFY_ROLE_ID = 1495417530259341382  # ← Replace with ticket-team role ID


# ── COLORS ───────────────────────────────────────────────────
# These are hex color codes used in embed messages (the colored sidebar on messages).
# You can pick colors from: https://www.color-hex.com/
COLOR_SUCCESS = 0x2ECC71  # Green  — for success messages
COLOR_ERROR = 0xE74C3C  # Red    — for error messages
COLOR_INFO = 0x3498DB  # Blue   — for info messages
COLOR_WARNING = 0xF39C12  # Orange — for warnings
