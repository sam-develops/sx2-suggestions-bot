# ============================================================
# cogs/feedback.py — The Feedback System
#
# Different from suggestions — feedback is for telling the staff
# how you feel about the server, bot, or experience in general.
#
# Usage:
#   !feedback general The bot is really helpful!
#   !feedback bug The !suggest command didn't work for me
#   !feedback idea Can we get a giveaway channel?
# ============================================================

import discord
from discord.ext import commands

from config import FEEDBACK_CHANNEL_ID, COLOR_INFO, COLOR_ERROR, COLOR_SUCCESS, COLOR_WARNING


# ── FEEDBACK TYPES ────────────────────────────────────────────
# These are the categories a user can pick when submitting feedback.
# Each one has a label, an emoji, and a color for the embed.
FEEDBACK_TYPES = {
    "general": {
        "label": "General Feedback",
        "emoji": "💬",
        "color": COLOR_INFO        # Blue
    },
    "bug": {
        "label": "Bug Report",
        "emoji": "🐛",
        "color": COLOR_ERROR       # Red
    },
    "idea": {
        "label": "Idea / Feature Request",
        "emoji": "💡",
        "color": COLOR_WARNING     # Orange
    },
    "compliment": {
        "label": "Compliment",
        "emoji": "⭐",
        "color": COLOR_SUCCESS     # Green
    },
}


# ── FEEDBACK COG ──────────────────────────────────────────────
class Feedback(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ── !feedback command ─────────────────────────────────────
    # Usage: !feedback <type> <message>
    # Types: general, bug, idea, compliment
    #
    # Example:
    #   !feedback bug The ticket button didn't work
    #   !feedback idea Add a leaderboard for suggestions
    @commands.command(name="feedback")
    async def feedback(self, ctx, feedback_type: str = None, *, message: str = None):
        """
        Submit feedback to the server staff.

        Usage: !feedback <type> <message>
        Types: general | bug | idea | compliment

        Examples:
          !feedback general I love this server!
          !feedback bug The bot crashed when I used !suggest
          !feedback idea Add a poll command
          !feedback compliment Great staff team!
        """

        # ── Check: Did the user provide a type? ───────────────
        if feedback_type is None:
            embed = discord.Embed(
                title="💬 How to Use Feedback",
                description=(
                    "You need to choose a feedback type!\n\n"
                    "**Usage:**\n"
                    "`!feedback <type> <your message>`\n\n"
                    "**Available types:**\n"
                    "💬 `general` — General thoughts about the server\n"
                    "🐛 `bug` — Something is broken or not working\n"
                    "💡 `idea` — A feature or improvement idea\n"
                    "⭐ `compliment` — Something you love!\n\n"
                    "**Example:**\n"
                    "`!feedback bug The suggest command didn't work`"
                ),
                color=COLOR_INFO
            )
            await ctx.send(embed=embed, delete_after=20)
            return

        # ── Check: Is the type valid? ─────────────────────────
        # We make it lowercase so "Bug" and "bug" both work
        feedback_type = feedback_type.lower()

        if feedback_type not in FEEDBACK_TYPES:
            valid_types = ", ".join(f"`{t}`" for t in FEEDBACK_TYPES)
            embed = discord.Embed(
                title="❌ Invalid Feedback Type",
                description=(
                    f"**`{feedback_type}`** is not a valid type.\n\n"
                    f"**Valid types:** {valid_types}\n\n"
                    f"**Example:** `!feedback general I love this server!`"
                ),
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=15)
            return

        # ── Check: Did the user write a message? ──────────────
        if message is None or message.strip() == "":
            embed = discord.Embed(
                title="❌ Missing Message",
                description=(
                    "You forgot to write your feedback message!\n\n"
                    f"**Example:** `!feedback {feedback_type} Your message here`"
                ),
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=15)
            return

        # ── Find the feedback channel ──────────────────────────
        channel = ctx.guild.get_channel(FEEDBACK_CHANNEL_ID)

        if channel is None:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description="The feedback channel hasn't been set up yet. Please contact an admin.",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        # ── Get the feedback type details ──────────────────────
        ftype = FEEDBACK_TYPES[feedback_type]

        # ── Build the feedback embed ───────────────────────────
        embed = discord.Embed(
            title=f"{ftype['emoji']} {ftype['label']}",
            description=message,
            color=ftype["color"]
        )

        # Show who submitted it
        embed.set_author(
            name=f"{ctx.author.display_name} ({ctx.author})",
            icon_url=ctx.author.display_avatar.url
        )

        # Add extra details in the footer
        embed.set_footer(text=f"Submitted in #{ctx.channel.name}")
        embed.timestamp = ctx.message.created_at  # Timestamp of when it was sent

        # ── Send to the feedback channel ───────────────────────
        await channel.send(embed=embed)

        # ── Confirm to the user ────────────────────────────────
        confirm = discord.Embed(
            title=f"✅ Feedback Submitted!",
            description=(
                f"Thank you {ctx.author.mention}! Your **{ftype['label']}** has been sent to staff. 💙\n\n"
                f"**Your message:** {message}"
            ),
            color=COLOR_SUCCESS
        )
        await ctx.send(embed=confirm, delete_after=15)

        # Delete the original command message to keep chat clean
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass  # Bot doesn't have permission to delete — that's okay


    # ── Error handler for !feedback ───────────────────────────
    # Catches any uncaught errors from this command specifically
    @feedback.error
    async def feedback_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="❌ Missing Information",
                description=(
                    "You're missing part of the command!\n\n"
                    "**Usage:** `!feedback <type> <message>`\n"
                    "**Example:** `!feedback idea Add a poll command`"
                ),
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=15)


# ── SETUP FUNCTION ────────────────────────────────────────────
async def setup(bot):
    await bot.add_cog(Feedback(bot))
