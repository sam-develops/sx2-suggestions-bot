# ============================================================
# cogs/suggestions.py — The Suggestion System
#
# Users submit ideas with !suggest. The bot posts the suggestion in a
# special channel where members vote with 👍 / 👎, and logs it in Supabase.
#
# Staff then move each suggestion through a review workflow:
#   !approve  <number> [reason]   → mark as Approved
#   !deny     <number> [reason]   → mark as Denied
#   !consider <number> [reason]   → mark as Under Consideration
#
# Reviewing a suggestion recolours the original message, stamps who
# decided and why, and DMs the author so they know the outcome.
# ============================================================

from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import (
    SUGGESTION_CHANNEL_ID,
    STAFF_ROLE_ID,
    COLOR_INFO,
    COLOR_ERROR,
    COLOR_SUCCESS,
    COLOR_WARNING,
)


# ── REVIEW STATUS STYLES ──────────────────────────────────────
# Each reviewable status maps to how it is shown to users.
STATUS_STYLES = {
    "approved": {"label": "Approved", "emoji": "✅", "color": COLOR_SUCCESS},
    "denied": {"label": "Denied", "emoji": "❌", "color": COLOR_ERROR},
    "considered": {"label": "Under Consideration", "emoji": "🤔", "color": COLOR_WARNING},
}

# Prefix used on the embed field we add/replace when a suggestion is reviewed.
_STATUS_FIELD_NAME = "📋 Status"


async def _next_suggestion_number(bot, guild_id: int) -> int:
    """Per-server suggestion number (#1, #2, ...). Mirrors the ticket counter."""
    if bot.db_manager.client:
        try:
            response = (
                await bot.db_manager.client.table("suggestions")
                .select("suggestion_number")
                .eq("guild_id", guild_id)
                .order("suggestion_number", desc=True)
                .limit(1)
                .execute()
            )
            if response.data and len(response.data) > 0:
                return int(response.data[0]["suggestion_number"]) + 1
            return 1
        except Exception as e:
            print(f"❌ [Suggestions] Failed to fetch next suggestion number: {e}")
    return 1


class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── Staff permission check ────────────────────────────────
    async def _is_staff(self, ctx) -> bool:
        """Staff = Administrator / Manage Server, or the configured staff role."""
        perms = ctx.author.guild_permissions
        if perms.administrator or perms.manage_guild:
            return True

        staff_role_id = await self.bot.db_manager.get_setting_value(
            ctx.guild.id, "staff_role_id", STAFF_ROLE_ID
        )
        if isinstance(staff_role_id, int) and staff_role_id:
            return any(role.id == staff_role_id for role in ctx.author.roles)
        return False

    # ── !suggest command ──────────────────────────────────────
    @commands.command(name="suggest")
    async def suggest(self, ctx, *, suggestion: str):
        """
        Submit a suggestion to the suggestions channel.
        Usage: !suggest <your idea>
        """
        # ── Find the suggestions channel dynamically ──────────
        channel_id = await self.bot.db_manager.get_setting_value(
            ctx.guild.id, "suggestion_channel_id", SUGGESTION_CHANNEL_ID
        )
        channel = ctx.guild.get_channel(channel_id)

        if channel is None:
            embed = discord.Embed(
                description="❌ Suggestion channel not found. Please ask an admin to configure it using `!set_suggestion_channel`.",
                color=COLOR_ERROR
            )
            await ctx.send(embed=embed, delete_after=10)
            return

        # ── Reserve the next per-server suggestion number ──────
        number = await _next_suggestion_number(self.bot, ctx.guild.id)

        # ── Build the suggestion embed ─────────────────────────
        embed = discord.Embed(
            title=f"💡 Suggestion #{number}",
            description=suggestion,
            color=COLOR_INFO
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url
        )
        embed.set_footer(text=f"Suggestion #{number} • React 👍 / 👎 to vote")
        embed.timestamp = ctx.message.created_at

        # ── Send the suggestion + voting reactions ─────────────
        suggestion_message = await channel.send(embed=embed)
        await suggestion_message.add_reaction("👍")
        await suggestion_message.add_reaction("👎")

        # ── Log the suggestion in Supabase ─────────────────────
        if self.bot.db_manager.client:
            try:
                await self.bot.db_manager.client.table("suggestions").insert({
                    "suggestion_number": number,
                    "guild_id": ctx.guild.id,
                    "user_id": ctx.author.id,
                    "message_id": suggestion_message.id,
                    "content": suggestion,
                    "status": "pending"
                }).execute()
            except Exception as e:
                print(f"❌ [Suggestions] Failed to log to Supabase: {e}")

        # ── Confirm to the user that it was submitted ──────────
        confirm_embed = discord.Embed(
            description=f"✅ Your suggestion **#{number}** has been posted in {channel.mention}!",
            color=COLOR_SUCCESS
        )
        await ctx.send(embed=confirm_embed, delete_after=10)

        # Delete the original command message to keep the channel tidy
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

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

    # ── Review commands (staff only) ──────────────────────────
    @commands.command(name="approve")
    async def approve(self, ctx, number: int, *, reason: str = None):
        """Approve a suggestion. Usage: !approve <number> [reason]"""
        await self._review(ctx, number, "approved", reason)

    @commands.command(name="deny")
    async def deny(self, ctx, number: int, *, reason: str = None):
        """Deny a suggestion. Usage: !deny <number> [reason]"""
        await self._review(ctx, number, "denied", reason)

    @commands.command(name="consider")
    async def consider(self, ctx, number: int, *, reason: str = None):
        """Mark a suggestion as under consideration. Usage: !consider <number> [reason]"""
        await self._review(ctx, number, "considered", reason)

    # ── Core review logic ─────────────────────────────────────
    async def _review(self, ctx, number: int, new_status: str, reason: str | None):
        if ctx.guild is None:
            return

        style = STATUS_STYLES[new_status]

        # ── Permission gate ───────────────────────────────────
        if not await self._is_staff(ctx):
            await ctx.send(
                embed=discord.Embed(
                    title="🚫 Staff Only",
                    description="Only staff can review suggestions. Ask an admin to set a staff role with `!set_staff_role`.",
                    color=COLOR_ERROR,
                ),
                delete_after=12,
            )
            return

        db = self.bot.db_manager
        if not db.client:
            await ctx.send(
                embed=discord.Embed(
                    description="❌ Database isn't connected, so I can't review suggestions right now.",
                    color=COLOR_ERROR,
                ),
                delete_after=12,
            )
            return

        # ── Look up the suggestion ────────────────────────────
        try:
            response = (
                await db.client.table("suggestions")
                .select("*")
                .eq("guild_id", ctx.guild.id)
                .eq("suggestion_number", number)
                .limit(1)
                .execute()
            )
        except Exception as e:
            print(f"❌ [Suggestions] Lookup failed for #{number}: {e}")
            await ctx.send(
                embed=discord.Embed(
                    description="❌ Couldn't reach the database to look up that suggestion.",
                    color=COLOR_ERROR,
                ),
                delete_after=12,
            )
            return

        if not response.data:
            await ctx.send(
                embed=discord.Embed(
                    description=f"🔍 No suggestion **#{number}** found in this server.",
                    color=COLOR_WARNING,
                ),
                delete_after=12,
            )
            return

        row = response.data[0]
        previous = (row.get("status") or "pending")

        # ── Update the record ─────────────────────────────────
        try:
            await db.client.table("suggestions").update({
                "status": new_status,
                "reviewer_id": ctx.author.id,
                "review_reason": reason,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", row["id"]).execute()
        except Exception as e:
            print(f"❌ [Suggestions] Failed to update status for #{number}: {e}")
            await ctx.send(
                embed=discord.Embed(
                    description="❌ I couldn't save the new status to the database.",
                    color=COLOR_ERROR,
                ),
                delete_after=12,
            )
            return

        # ── Edit the original message + DM the author ─────────
        message_edited = await self._update_suggestion_message(ctx, row, number, new_status, reason)
        author_dmed = await self._dm_author(ctx, row, number, new_status, reason)

        # ── Confirm to the reviewing staff member ─────────────
        notes = []
        if not message_edited:
            notes.append("⚠️ Couldn't edit the original suggestion message (it may have been deleted).")
        notes.append(
            "📨 Author was notified by DM." if author_dmed
            else "📭 Couldn't DM the author (they may have DMs disabled)."
        )
        if previous in STATUS_STYLES and previous != new_status:
            notes.append(f"↩️ Changed from **{STATUS_STYLES[previous]['label']}**.")

        confirm = discord.Embed(
            title=f"{style['emoji']} Suggestion #{number} — {style['label']}",
            description=(reason or "_No reason given._") + "\n\n" + "\n".join(notes),
            color=style["color"],
        )
        confirm.set_footer(text=f"Reviewed by {ctx.author.display_name}")
        await ctx.send(embed=confirm)

        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.HTTPException):
            pass

    # ── Helpers ───────────────────────────────────────────────
    async def _update_suggestion_message(self, ctx, row, number, new_status, reason) -> bool:
        """Recolour the original suggestion embed and stamp the decision on it."""
        style = STATUS_STYLES[new_status]

        channel_id = await self.bot.db_manager.get_setting_value(
            ctx.guild.id, "suggestion_channel_id", SUGGESTION_CHANNEL_ID
        )
        channel = ctx.guild.get_channel(channel_id)
        message_id = row.get("message_id")
        if channel is None or not message_id:
            return False

        try:
            message = await channel.fetch_message(int(message_id))
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return False

        embed = message.embeds[0] if message.embeds else discord.Embed(description=row.get("content"))
        embed.color = style["color"]

        # Replace any existing status field so re-reviews don't stack up.
        for i in reversed(range(len(embed.fields))):
            if (embed.fields[i].name or "").startswith(_STATUS_FIELD_NAME):
                embed.remove_field(i)

        value = f"{style['emoji']} **{style['label']}** by {ctx.author.mention}"
        if reason:
            value += f"\n💬 {reason}"
        embed.add_field(name=_STATUS_FIELD_NAME, value=value, inline=False)
        embed.set_footer(text=f"Suggestion #{number} • {style['label']}")

        try:
            await message.edit(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    async def _dm_author(self, ctx, row, number, new_status, reason) -> bool:
        """Let the suggestion author know the outcome via DM."""
        style = STATUS_STYLES[new_status]
        user_id = row.get("user_id")
        if not user_id:
            return False

        user = ctx.guild.get_member(int(user_id))
        if user is None:
            try:
                user = await self.bot.fetch_user(int(user_id))
            except (discord.NotFound, discord.HTTPException):
                return False

        content = row.get("content") or ""
        if len(content) > 1000:
            content = content[:1000] + "…"

        embed = discord.Embed(
            title=f"{style['emoji']} Your suggestion was {style['label'].lower()}",
            description=f"**Suggestion #{number}**\n>>> {content}",
            color=style["color"],
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Reviewed by", value=str(ctx.author), inline=True)
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"From {ctx.guild.name}")

        try:
            await user.send(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            return False

    # ── Shared error handler for the review commands ──────────
    @approve.error
    @deny.error
    @consider.error
    async def _review_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Missing Suggestion Number",
                    description=(
                        "Tell me which suggestion to review.\n\n"
                        f"**Usage:** `{ctx.prefix}{ctx.invoked_with} <number> [reason]`\n"
                        f"**Example:** `{ctx.prefix}{ctx.invoked_with} 4 Great idea, adding it!`"
                    ),
                    color=COLOR_WARNING,
                ),
                delete_after=15,
            )
        elif isinstance(error, commands.BadArgument):
            await ctx.send(
                embed=discord.Embed(
                    title="⚠️ Invalid Number",
                    description="The suggestion number must be a whole number, e.g. `4`.",
                    color=COLOR_WARNING,
                ),
                delete_after=12,
            )


async def setup(bot):
    await bot.add_cog(Suggestions(bot))
