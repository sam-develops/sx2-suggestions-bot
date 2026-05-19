# ============================================================
# utils/embeds.py — Reusable Embed Builders
#
# Instead of building embeds from scratch every time,
# we define helper functions here that return ready-made embeds.
#
# Think of these like "templates" for messages.
# ============================================================

import discord
from config import COLOR_SUCCESS, COLOR_ERROR, COLOR_INFO, COLOR_WARNING


def success_embed(title: str, description: str) -> discord.Embed:
    """
    Returns a green 'success' embed.
    Use this when something worked correctly.

    Example:
        embed = success_embed("Done!", "Your ticket was created.")
    """
    return discord.Embed(title=f"✅ {title}", description=description, color=COLOR_SUCCESS)


def error_embed(title: str, description: str) -> discord.Embed:
    """
    Returns a red 'error' embed.
    Use this when something went wrong.

    Example:
        embed = error_embed("Failed", "You don't have permission.")
    """
    return discord.Embed(title=f"❌ {title}", description=description, color=COLOR_ERROR)


def info_embed(title: str, description: str) -> discord.Embed:
    """
    Returns a blue 'info' embed.
    Use this for general information messages.

    Example:
        embed = info_embed("Ticket System", "Click the button below to open a ticket.")
    """
    return discord.Embed(title=f"ℹ️ {title}", description=description, color=COLOR_INFO)


def warning_embed(title: str, description: str) -> discord.Embed:
    """
    Returns an orange 'warning' embed.
    Use this to warn the user about something.

    Example:
        embed = warning_embed("Missing Info", "You forgot to include a message.")
    """
    return discord.Embed(title=f"⚠️ {title}", description=description, color=COLOR_WARNING)
