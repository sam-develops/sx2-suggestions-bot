# ============================================================
# cogs/suggestions.py — The Suggestion System
#
# This lets users submit suggestions using the !suggest command.
# The bot posts the suggestion in a special channel where others
# can vote with 👍 or 👎 reactions.
# ============================================================

import discord
from discord.ext import commands

from config import SUGGESTION_CHANNEL_ID, COLOR_INFO, COLOR_ERROR, COLOR_SUCCESS


# ── SUGGESTIONS COG ───────────────────────────────────────────
class Suggestions(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ── !suggest command ──────────────────────────────────────
    # Usage: !suggest Your idea here
    # Example: !suggest Add a music bot to the server
    @commands.command(name="suggest")
    async def suggest(self, ctx, *, suggestion: str):
        """
        Submit a suggestion to the suggestions channel.
        Usage: !suggest <your idea>
        """

        # ── Find the suggestions channel ──────────────────────
        # We look up the channel using its ID from config.py
        channel = ctx.guild.get_channel(SUGGESTION_CHANNEL_ID)

        if channel is None:
            # If the channel wasn't found, tell the user
            await ctx.send(
                "❌ Suggestion channel not found. Please ask an admin to set it up.",
                delete_after=10  # Auto-delete after 10 seconds
            )
            return

        # ── Build the suggestion embed ─────────────────────────
        # An "embed" is a fancy formatted message with colors and fields
        embed = discord.Embed(
            title="💡 New Suggestion",
            description=suggestion,      # The actual suggestion text
            color=COLOR_INFO
        )

        # Show who made the suggestion
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url
        )

        # Add a footer with the suggestion status
        embed.set_footer(text="React with 👍 or 👎 to vote!")
        embed.timestamp = ctx.message.created_at  # Show when it was submitted

        # ── Send the suggestion to the suggestions channel ─────
        suggestion_message = await channel.send(embed=embed)

        # ── Add voting reactions automatically ─────────────────
        # This adds the 👍 and 👎 so people don't have to type them
        await suggestion_message.add_reaction("👍")
        await suggestion_message.add_reaction("👎")

        # ── Confirm to the user that it was submitted ──────────
        confirm_embed = discord.Embed(
            description=f"✅ Your suggestion has been posted in {channel.mention}!",
            color=COLOR_SUCCESS
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

        # Delete the original command message to keep the channel tidy
        await ctx.message.delete()

    # ── Error handling for !suggest ───────────────────────────
    # This runs if the user types !suggest without a message
    @suggest.error
    async def suggest_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Missing Suggestion",
                description=(
                    "You forgot to write your suggestion!\n\n"
                    "**Correct usage:**\n"
                    "`!suggest <your idea>`\n\n"
                    "**Example:**\n"
                    "`!suggest Add a music bot to the server`"
                ),
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=15)


# ── SETUP FUNCTION ────────────────────────────────────────────
async def setup(bot):
    await bot.add_cog(Suggestions(bot))
