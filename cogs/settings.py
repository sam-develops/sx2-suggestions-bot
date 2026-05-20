# ============================================================
# cogs/settings.py — Server Settings Cog
#
# This cog provides commands for administrators to configure
# the bot's channels, roles, and settings per-server in Supabase.
# ============================================================

import discord
from discord.ext import commands
from config import COLOR_SUCCESS, COLOR_ERROR, COLOR_INFO

class Settings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """All commands in this cog require Administrator permissions and must be in a guild."""
        if ctx.guild is None:
            return False
        return ctx.author.guild_permissions.administrator

    @commands.command(name="set_prefix")
    async def set_prefix(self, ctx, prefix: str):
        """Sets the command prefix for this server."""
        if len(prefix) > 10:
            embed = discord.Embed(description="❌ Prefix cannot be longer than 10 characters.", color=COLOR_ERROR)
            await ctx.send(embed=embed)
            return

        success = await self.bot.db_manager.update_setting(ctx.guild.id, "prefix", prefix)
        if success:
            embed = discord.Embed(description=f"✅ Command prefix updated to `{prefix}` for this server!", color=COLOR_SUCCESS)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Failed to update prefix in Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)

    @commands.command(name="set_suggestion_channel")
    async def set_suggestion_channel(self, ctx, channel: discord.TextChannel):
        """Sets the channel where suggestions will be posted."""
        success = await self.bot.db_manager.update_setting(ctx.guild.id, "suggestion_channel_id", channel.id)
        if success:
            embed = discord.Embed(description=f"✅ Suggestions channel updated to {channel.mention}!", color=COLOR_SUCCESS)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Failed to update settings in Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)

    @commands.command(name="set_feedback_channel")
    async def set_feedback_channel(self, ctx, channel: discord.TextChannel):
        """Sets the channel where feedback will be posted."""
        success = await self.bot.db_manager.update_setting(ctx.guild.id, "feedback_channel_id", channel.id)
        if success:
            embed = discord.Embed(description=f"✅ Feedback channel updated to {channel.mention}!", color=COLOR_SUCCESS)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Failed to update settings in Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)

    @commands.command(name="set_ticket_category")
    async def set_ticket_category(self, ctx, category: discord.CategoryChannel):
        """Sets the main fallback category for support tickets."""
        success = await self.bot.db_manager.update_setting(ctx.guild.id, "ticket_category_id", category.id)
        if success:
            embed = discord.Embed(description=f"✅ Fallback ticket category updated to **{category.name}**!", color=COLOR_SUCCESS)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Failed to update settings in Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)

    @commands.command(name="set_new_ticket_category")
    async def set_new_ticket_category(self, ctx, category: discord.CategoryChannel):
        """Sets the category for newly opened tickets."""
        success = await self.bot.db_manager.update_setting(ctx.guild.id, "ticket_new_category_id", category.id)
        if success:
            embed = discord.Embed(description=f"✅ New ticket category updated to **{category.name}**!", color=COLOR_SUCCESS)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Failed to update settings in Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)

    @commands.command(name="set_working_ticket_category")
    async def set_working_ticket_category(self, ctx, category: discord.CategoryChannel):
        """Sets the category for ticket channels that staff are actively working on."""
        success = await self.bot.db_manager.update_setting(ctx.guild.id, "ticket_working_category_id", category.id)
        if success:
            embed = discord.Embed(description=f"✅ Active/working ticket category updated to **{category.name}**!", color=COLOR_SUCCESS)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Failed to update settings in Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)

    @commands.command(name="set_resolved_channel")
    async def set_resolved_channel(self, ctx, channel: discord.TextChannel):
        """Sets the channel where logs of resolved tickets are posted."""
        success = await self.bot.db_manager.update_setting(ctx.guild.id, "resolved_tickets_channel_id", channel.id)
        if success:
            embed = discord.Embed(description=f"✅ Resolved tickets log channel updated to {channel.mention}!", color=COLOR_SUCCESS)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Failed to update settings in Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)

    @commands.command(name="set_staff_role")
    async def set_staff_role(self, ctx, role: discord.Role):
        """Sets the Staff role that can access ticket channels."""
        success = await self.bot.db_manager.update_setting(ctx.guild.id, "staff_role_id", role.id)
        if success:
            embed = discord.Embed(description=f"✅ Staff role updated to **{role.name}**!", color=COLOR_SUCCESS)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Failed to update settings in Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)

    @commands.command(name="set_ticket_admin_role")
    async def set_ticket_admin_role(self, ctx, role: discord.Role):
        """Sets the Ticket Admin role that receives DM notifications when a ticket is opened."""
        success = await self.bot.db_manager.update_setting(ctx.guild.id, "ticket_admin_notify_role_id", role.id)
        if success:
            embed = discord.Embed(description=f"✅ Ticket Admin notify role updated to **{role.name}**!", color=COLOR_SUCCESS)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description="❌ Failed to update settings in Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)

    @commands.command(name="show_config")
    async def show_config(self, ctx):
        """Displays the server's current configuration."""
        settings = await self.bot.db_manager.get_settings(ctx.guild.id)
        
        if not settings:
            embed = discord.Embed(description="❌ Failed to load settings from Supabase.", color=COLOR_ERROR)
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(title=f"⚙️ Configuration for {ctx.guild.name}", color=COLOR_INFO)

        # Build channels text
        sug_ch = ctx.guild.get_channel(settings.get("suggestion_channel_id"))
        feed_ch = ctx.guild.get_channel(settings.get("feedback_channel_id"))
        res_ch = ctx.guild.get_channel(settings.get("resolved_tickets_channel_id"))

        embed.add_field(
            name="📡 Channels",
            value=(
                f"• **Suggestions:** {sug_ch.mention if sug_ch else '`Not set` (Falls back to config.py)'}\n"
                f"• **Feedback:** {feed_ch.mention if feed_ch else '`Not set` (Falls back to config.py)'}\n"
                f"• **Resolved Tickets Logs:** {res_ch.mention if res_ch else '`Not set` (Falls back to config.py)'}"
            ),
            inline=False
        )

        # Build categories text
        cat_fallback = ctx.guild.get_channel(settings.get("ticket_category_id"))
        cat_new = ctx.guild.get_channel(settings.get("ticket_new_category_id"))
        cat_work = ctx.guild.get_channel(settings.get("ticket_working_category_id"))

        embed.add_field(
            name="📁 Ticket Categories",
            value=(
                f"• **New Tickets:** {cat_new.name if isinstance(cat_new, discord.CategoryChannel) else '`Not set` (Falls back to fallback category)'}\n"
                f"• **Active/Working Tickets:** {cat_work.name if isinstance(cat_work, discord.CategoryChannel) else '`Not set` (Falls back to fallback category)'}\n"
                f"• **Fallback/Main Category:** {cat_fallback.name if isinstance(cat_fallback, discord.CategoryChannel) else '`Not set` (Falls back to config.py)'}"
            ),
            inline=False
        )

        # Build roles text
        staff_role = ctx.guild.get_role(settings.get("staff_role_id"))
        admin_role = ctx.guild.get_role(settings.get("ticket_admin_notify_role_id"))

        embed.add_field(
            name="👥 Roles",
            value=(
                f"• **Staff Role:** {staff_role.mention if staff_role else '`Not set` (Falls back to config.py)'}\n"
                f"• **Ticket Admin Notification Role:** {admin_role.mention if admin_role else '`Not set` (Falls back to staff role)'}"
            ),
            inline=False
        )

        # Prefix
        embed.add_field(name="⌨️ Prefix", value=f"`{settings.get('prefix', '!')}`", inline=True)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Settings(bot))
