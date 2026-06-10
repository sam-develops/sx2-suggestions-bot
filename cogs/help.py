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

        p = ctx.prefix

        embed = discord.Embed(
            title="🤖 Bot Commands",
            description=f"Here's everything I can do! Use `{p}` before each command.",
            color=COLOR_INFO
        )

        # ── Ticket commands ────────────────────────────────────
        embed.add_field(
            name="🎫 Tickets",
            value=(
                f"`{p}ticket` — Post the ticket panel here\n"
                "Then click **Open a Ticket** to open your private ticket."
            ),
            inline=False
        )

        # ── Suggestion commands ────────────────────────────────
        embed.add_field(
            name="💡 Suggestions",
            value=(
                f"`{p}suggest <idea>` — Submit a suggestion\n"
                f"Example: `{p}suggest Add a music bot`"
            ),
            inline=False
        )

        # ── Suggestion review (staff & admins) ─────────────────
        if ctx.author.guild_permissions.manage_guild or ctx.author.guild_permissions.administrator:
            embed.add_field(
                name="🛠️ Suggestion Review (Staff)",
                value=(
                    f"`{p}approve <#> [reason]` — Approve a suggestion\n"
                    f"`{p}deny <#> [reason]` — Deny a suggestion\n"
                    f"`{p}consider <#> [reason]` — Mark as under consideration\n"
                    f"Example: `{p}approve 4 Great idea — adding it!`"
                ),
                inline=False
            )

        # ── Feedback commands ──────────────────────────────────
        embed.add_field(
            name="💬 Feedback",
            value=(
                f"`{p}feedback <type> <message>` — Send feedback to staff\n"
                "**Types:** `general` | `bug` | `idea` | `compliment`\n"
                f"Example: `{p}feedback bug The bot crashed`"
            ),
            inline=False
        )

        # ── Admin Config commands (only shown to administrators) ──
        if ctx.author.guild_permissions.administrator:
            embed.add_field(
                name="⚙️ Admin Configuration (Admin-only)",
                value=(
                    f"`{p}show_config` — View current server settings\n"
                    f"`{p}set_prefix <prefix>` — Set server prefix\n"
                    f"`{p}set_suggestion_channel <#channel>` — Set suggestion channel\n"
                    f"`{p}set_feedback_channel <#channel>` — Set feedback channel\n"
                    f"`{p}set_resolved_channel <#channel>` — Set resolved ticket logs channel\n"
                    f"`{p}set_staff_role <@role>` — Set staff role for tickets\n"
                    f"`{p}set_ticket_admin_role <@role>` — Set role to receive ticket DMs\n"
                    f"`{p}set_ticket_category <id>` — Set main ticket category\n"
                    f"`{p}set_new_ticket_category <id>` — Set new ticket category\n"
                    f"`{p}set_working_ticket_category <id>` — Set active ticket category\n"
                    f"`{p}announce` — Open the interactive announcement builder"
                ),
                inline=False
            )

        # ── Help commands ──────────────────────────────────────
        embed.add_field(
            name="❓ Help",
            value=f"`{p}help` — Show this message",
            inline=False
        )

        embed.set_footer(text="Having trouble? Open a ticket for support!")

        await ctx.send(embed=embed)

    # ── GLOBAL ERROR HANDLER ──────────────────────────────────
    # This catches ANY error that happens with ANY command.
    # Instead of crashing silently, it tells the user what went wrong.
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        p = ctx.prefix

        # ── Command not found ──────────────────────────────────
        if isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                title="❓ Unknown Command",
                description=(
                    f"I don't recognize that command.\n\n"
                    f"Type `{p}help` to see all available commands."
                ),
                color=COLOR_WARNING
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Missing permissions ────────────────────────────────
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="🚫 No Permission",
                description="You don't have permission to use this command.",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=10)

        # ── Missing required argument ──────────────────────────
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="⚠️ Missing Information",
                description=(
                    f"You are missing a required argument for this command.\n\n"
                    f"**Required parameter:** `{error.param.name}`\n"
                    f"Type `{p}help` to see correct command usage."
                ),
                color=COLOR_WARNING
            )
            await ctx.send(embed=embed, delete_after=15)

        # ── Channel Not Found ──────────────────────────────────
        elif isinstance(error, commands.ChannelNotFound):
            embed = discord.Embed(
                title="🔍 Channel Not Found",
                description=(
                    f"I couldn't find the channel/category you specified: `{error.argument}`\n\n"
                    "**Possible reasons:**\n"
                    "• The channel or category ID/mention is incorrect.\n"
                    "• You passed a **text channel** (like `#tickets`) instead of a **Category folder** (like `TICKETS`).\n"
                    "• The channel is in a different server.\n"
                    "• I do not have permission to view that channel/category."
                ),
                color=COLOR_WARNING
            )
            await ctx.send(embed=embed, delete_after=15)

        # ── Role Not Found ─────────────────────────────────────
        elif isinstance(error, commands.RoleNotFound):
            embed = discord.Embed(
                title="🔍 Role Not Found",
                description=(
                    f"I couldn't find the role you specified: `{error.argument}`\n\n"
                    "**Possible reasons:**\n"
                    "• The role ID or mention is incorrect.\n"
                    "• The role does not exist in this server."
                ),
                color=COLOR_WARNING
            )
            await ctx.send(embed=embed, delete_after=15)

        # ── Bad Argument (Invalid conversion) ──────────────────
        elif isinstance(error, commands.BadArgument):
            embed = discord.Embed(
                title="⚠️ Invalid Parameter",
                description=(
                    f"One of the parameters you provided is invalid.\n\n"
                    f"**Details:** {error}\n\n"
                    f"Please make sure you tag/mention channels (`#channel`), roles (`@role`), or provide correct IDs."
                ),
                color=COLOR_WARNING
            )
            await ctx.send(embed=embed, delete_after=15)

        # ── Bot missing permissions ────────────────────────────
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                title="🔧 Bot Missing Permissions",
                description=(
                    "I don't have the permissions needed to perform that action.\n"
                    "Please ask an administrator to check my server role permissions."
                ),
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=15)

        # ── Command Invoke Error ──────────────────────────────
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            
            # Check for Discord Forbidden errors (e.g. DMs blocked, can't manage channels)
            if isinstance(original, discord.Forbidden):
                embed = discord.Embed(
                    title="🚫 Action Forbidden",
                    description=(
                        "I am forbidden by Discord from completing this action.\n\n"
                        "**Possibilities include:**\n"
                        "• I do not have permission to manage/create channels in this category.\n"
                        "• My role is placed below the target role/member in the server hierarchy.\n"
                        "• The user has their Direct Messages (DMs) disabled."
                    ),
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed)
            
            # Check for Supabase / Postgrest Database Errors
            elif "postgrest" in original.__class__.__module__.lower() or "supabase" in original.__class__.__module__.lower():
                embed = discord.Embed(
                    title="🗄️ Database Error",
                    description=(
                        "An error occurred while communicating with the database (Supabase).\n\n"
                        f"**Error Details:** `{original}`\n\n"
                        "Make sure your tables are correctly configured in the SQL Editor and RLS policies are enabled."
                    ),
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed)
            
            # Catch other unexpected exceptions
            else:
                embed = discord.Embed(
                    title="💥 Unexpected Command Error",
                    description=(
                        f"An unexpected error occurred while executing `{ctx.command}`.\n\n"
                        f"**Exception:** `{original.__class__.__name__}`\n"
                        f"**Message:** `{original}`\n\n"
                        "Please report this to a developer or server administrator."
                    ),
                    color=COLOR_ERROR
                )
                await ctx.send(embed=embed)

        # ── Fallback ──────────────────────────────────────────
        else:
            print(f"Unhandled error in command '{ctx.command}': {error}")


# ── SETUP FUNCTION ────────────────────────────────────────────
async def setup(bot):
    await bot.add_cog(Help(bot))
