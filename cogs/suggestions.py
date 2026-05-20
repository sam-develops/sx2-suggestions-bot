# ============================================================
# cogs/suggestions.py — The Suggestion System
#
# This lets users submit suggestions using the !suggest command.
# The bot posts the suggestion in a special channel where others
# can vote with 👍 or 👎 reactions. It logs all suggestions in Supabase.
# ============================================================

import discord
from discord.ext import commands
from config import SUGGESTION_CHANNEL_ID, COLOR_INFO, COLOR_ERROR, COLOR_SUCCESS

class Suggestions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="suggest")
    async def suggest(self, ctx, *, suggestion: str):
        """
        Submit a suggestion to the suggestions channel.
        Usage: !suggest <your idea>
        """
        # ── Find the suggestions channel dynamically ──────────
        # Fetch the channel ID from Supabase (fallback to config.py)
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

        # ── Build the suggestion embed ─────────────────────────
        embed = discord.Embed(
            title="💡 New Suggestion",
            description=suggestion,
            color=COLOR_INFO
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url
        )
        embed.set_footer(text="React with 👍 or 👎 to vote!")
        embed.timestamp = ctx.message.created_at

        # ── Send the suggestion to the suggestions channel ─────
        suggestion_message = await channel.send(embed=embed)

        # ── Add voting reactions automatically ─────────────────
        await suggestion_message.add_reaction("👍")
        await suggestion_message.add_reaction("👎")

        # ── Log the suggestion in Supabase ─────────────────────
        if self.bot.db_manager.client:
            try:
                await self.bot.db_manager.client.table("suggestions").insert({
                    "guild_id": ctx.guild.id,
                    "message_id": suggestion_message.id,
                    "author_id": ctx.author.id,
                    "content": suggestion,
                    "status": "pending"
                }).execute()
            except Exception as e:
                print(f"❌ [Suggestions] Failed to log to Supabase: {e}")

        # ── Confirm to the user that it was submitted ──────────
        confirm_embed = discord.Embed(
            description=f"✅ Your suggestion has been posted in {channel.mention}!",
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

async def setup(bot):
    await bot.add_cog(Suggestions(bot))
