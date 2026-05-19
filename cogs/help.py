# ============================================================
# cogs/help.py — Help & Error Handling
#
# This cog does two things:
# 1. Provides a custom !help command that shows all commands
# 2. Catches errors when users type commands wrong and explains
#    what went wrong in plain English
# ============================================================

import discord
from discord.ext import commands

from config import COLOR_INFO, COLOR_ERROR, COLOR_WARNING


# ── HELP COG ──────────────────────────────────────────────────
class Help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Remove the default help command so we can make our own
        self.bot.remove_command("help")

    # ── !help command ─────────────────────────────────────────
    # Shows a list of all available commands
    @commands.command(name="help")
    async def help_command(self, ctx):
        """Shows a list of all bot commands."""

        embed = discord.Embed(
            title="🤖 Bot Commands",
            description="Here's everything I can do! Use `!` before each command.",
            color=COLOR_INFO
        )

        # ── Ticket commands ────────────────────────────────────
        embed.add_field(
            name="🎫 Tickets",
            value=(
                "`!ticket` — Post the ticket panel here (shows who ran it + panel / ticket numbers for tracking)\n"
                "Then click **Open a Ticket** to open your private ticket."
            ),
            inline=False
        )

        # ── Suggestion commands ────────────────────────────────
        embed.add_field(
            name="💡 Suggestions",
            value=(
                "`!suggest <idea>` — Submit a suggestion\n"
                "Example: `!suggest Add a music bot`"
            ),
            inline=False
        )

        # ── Feedback commands ──────────────────────────────────
        embed.add_field(
            name="💬 Feedback",
            value=(
                "`!feedback <type> <message>` — Send feedback to staff\n"
                "**Types:** `general` | `bug` | `idea` | `compliment`\n"
                "Example: `!feedback bug The bot crashed`"
            ),
            inline=False
        )

        # ── Help commands ──────────────────────────────────────
        embed.add_field(
            name="❓ Help",
            value="`!help` — Show this message",
            inline=False
        )

        embed.set_footer(text="Having trouble? Open a ticket for support!")

        await ctx.send(embed=embed)

    # ── GLOBAL ERROR HANDLER ──────────────────────────────────
    # This catches ANY error that happens with ANY command.
    # Instead of crashing silently, it tells the user what went wrong.
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        # ── Command not found ──────────────────────────────────
        # User typed something like !abc which doesn't exist
        if isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                title="❓ Unknown Command",
                description=(
                    f"I don't recognize that command.\n\n"
                    f"Type `!help` to see all available commands."
                ),
                color=COLOR_WARNING
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Missing permissions ────────────────────────────────
        # User tried to use an admin-only command
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="🚫 No Permission",
                description="You don't have permission to use this command.",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Missing required argument ──────────────────────────
        # User used a command but forgot to include required info
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="⚠️ Missing Information",
                description=(
                    f"You're missing a required part of that command.\n\n"
                    f"Type `!help` to see correct command usage."
                ),
                color=COLOR_WARNING
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Bot missing permissions ────────────────────────────
        # The bot itself doesn't have the right permissions in the server
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                title="🔧 Bot Missing Permissions",
                description=(
                    "I don't have the permissions needed to do that.\n"
                    "Please ask an admin to check my role permissions."
                ),
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── All other errors ───────────────────────────────────
        else:
            # Print the error to the console for debugging
            print(f"Unhandled error in command '{ctx.command}': {error}")


# ── SETUP FUNCTION ────────────────────────────────────────────
async def setup(bot):
    await bot.add_cog(Help(bot))
