# ============================================================
# cogs/announce.py — Interactive Announcement Cog
#
# This cog allows administrators to create and publish highly
# professional, embedded server announcements with headings,
# custom theme colors, pings, bullet points, and banner images.
# ============================================================

import discord
from discord.ext import commands
import traceback

THEMES = {
    "info": {
        "name": "🔵 Info (Blue)",
        "color": discord.Color.blue(),
        "emoji": "📢"
    },
    "success": {
        "name": "🟢 Success (Green)",
        "color": discord.Color.green(),
        "emoji": "✅"
    },
    "warning": {
        "name": "🟡 Warning (Orange)",
        "color": discord.Color.orange(),
        "emoji": "⚠️"
    },
    "danger": {
        "name": "🔴 Alert (Red)",
        "color": discord.Color.red(),
        "emoji": "🚨"
    },
    "event": {
        "name": "🟣 Event (Purple)",
        "color": discord.Color.purple(),
        "emoji": "🎉"
    }
}


class AnnouncementModal(discord.ui.Modal):
    """Modal to edit the text contents of the announcement."""

    def __init__(self, builder_view):
        super().__init__(title="Edit Announcement Content")
        self.builder_view = builder_view

        # Populate with existing state values
        self.title_input = discord.ui.TextInput(
            label="Announcement Title",
            placeholder="e.g. Server Update",
            default=builder_view.title_val,
            max_length=100,
            required=True
        )
        self.subtitle_input = discord.ui.TextInput(
            label="Subtitle / Introduction",
            placeholder="e.g. Version 2.0 is now live!",
            default=builder_view.subtitle_val or "",
            max_length=150,
            required=False
        )
        self.body_input = discord.ui.TextInput(
            label="Announcement Body",
            style=discord.TextStyle.paragraph,
            placeholder="Write the main description here...",
            default=builder_view.body_val,
            max_length=2000,
            required=True
        )
        self.points_input = discord.ui.TextInput(
            label="Key Points / Reasons (one per line)",
            style=discord.TextStyle.paragraph,
            placeholder="Added new music player\nFixed a few ticket system bugs\nUpgraded database performance",
            default=builder_view.points_val or "",
            max_length=1000,
            required=False
        )
        self.image_input = discord.ui.TextInput(
            label="Banner Image URL",
            placeholder="https://example.com/banner.png (Optional)",
            default=builder_view.image_url or "",
            max_length=500,
            required=False
        )

        self.add_item(self.title_input)
        self.add_item(self.subtitle_input)
        self.add_item(self.body_input)
        self.add_item(self.points_input)
        self.add_item(self.image_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Update parent builder state
        self.builder_view.title_val = self.title_input.value
        self.builder_view.subtitle_val = self.subtitle_input.value if self.subtitle_input.value.strip() else None
        self.builder_view.body_val = self.body_input.value
        self.builder_view.points_val = self.points_input.value if self.points_input.value.strip() else None

        img_val = self.image_input.value.strip()
        self.builder_view.image_url = img_val if img_val else None

        # Redraw the control panel and preview embeds
        await self.builder_view.update_view(interaction)


class AnnouncementBuilderView(discord.ui.View):
    """The interactive control panel for building announcements."""

    def __init__(self, author: discord.Member, guild: discord.Guild, bot, staff_role: discord.Role = None):
        super().__init__(timeout=600)  # 10 minute timeout
        self.author = author
        self.guild = guild
        self.bot = bot
        self.staff_role = staff_role
        self.message = None

        # Setup state
        self.target_channel = None
        self.theme_key = "info"
        self.ping_option = "none"

        # Content state with generic placeholder defaults
        self.title_val = "📢 Server Announcement"
        self.subtitle_val = "This is a subtitle or short description."
        self.body_val = "This is the main body of the announcement. Click the **✍️ Edit Content** button below to customize these texts!"
        self.points_val = "🔹 Emojis make it look professional\n🔹 Bullet points are clean and readable\n🔹 Real-time preview lets you check before sending"
        self.image_url = None

        # --- Construct Selects & Buttons dynamically ---

        # Row 0: Target Channel Select
        self.channel_select = discord.ui.ChannelSelect(
            placeholder="📢 Select Target Channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            row=0
        )
        self.channel_select.callback = self.channel_select_callback
        self.add_item(self.channel_select)

        # Row 1: Theme/Color Select
        self.theme_select = discord.ui.Select(
            placeholder="🎨 Select Theme / Color...",
            options=[
                discord.SelectOption(label="Info (Blue)", value="info", emoji="🔵", default=True),
                discord.SelectOption(label="Success (Green)", value="success", emoji="🟢"),
                discord.SelectOption(label="Warning (Orange)", value="warning", emoji="🟡"),
                discord.SelectOption(label="Alert (Red)", value="danger", emoji="🔴"),
                discord.SelectOption(label="Event (Purple)", value="event", emoji="🟣"),
            ],
            row=1
        )
        self.theme_select.callback = self.theme_select_callback
        self.add_item(self.theme_select)

        # Row 2: Ping Select (Staff role is included if configured in guild)
        ping_options = [
            discord.SelectOption(label="No Ping", value="none", emoji="🔕", default=True),
            discord.SelectOption(label="@everyone", value="everyone", emoji="📢"),
            discord.SelectOption(label="@here", value="here", emoji="💬"),
        ]
        if staff_role:
            ping_options.append(
                discord.SelectOption(label=f"Ping @{staff_role.name}", value="staff", emoji="🛡️")
            )

        self.ping_select = discord.ui.Select(
            placeholder="🔔 Select Ping Option...",
            options=ping_options,
            row=2
        )
        self.ping_select.callback = self.ping_select_callback
        self.add_item(self.ping_select)

        # Row 3: Command Buttons
        self.edit_btn = discord.ui.Button(
            label="✍️ Edit Content",
            style=discord.ButtonStyle.primary,
            custom_id="edit_announcement_content",
            row=3
        )
        self.edit_btn.callback = self.edit_callback
        self.add_item(self.edit_btn)

        self.publish_btn = discord.ui.Button(
            label="🚀 Send Announcement",
            style=discord.ButtonStyle.success,
            custom_id="publish_announcement",
            disabled=True,
            row=3
        )
        self.publish_btn.callback = self.publish_callback
        self.add_item(self.publish_btn)

        self.cancel_btn = discord.ui.Button(
            label="❌ Cancel",
            style=discord.ButtonStyle.danger,
            custom_id="cancel_announcement",
            row=3
        )
        self.cancel_btn.callback = self.cancel_callback
        self.add_item(self.cancel_btn)

    async def channel_select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You are not the author of this builder.", ephemeral=True)
            return

        self.target_channel = self.channel_select.values[0]
        self.channel_select.placeholder = f"📢 Target: #{self.target_channel.name}"
        await self.update_view(interaction)

    async def theme_select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You are not the author of this builder.", ephemeral=True)
            return

        self.theme_key = self.theme_select.values[0]
        for option in self.theme_select.options:
            option.default = (option.value == self.theme_key)
        await self.update_view(interaction)

    async def ping_select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You are not the author of this builder.", ephemeral=True)
            return

        self.ping_option = self.ping_select.values[0]
        for option in self.ping_select.options:
            option.default = (option.value == self.ping_option)
        await self.update_view(interaction)

    async def edit_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You are not the author of this builder.", ephemeral=True)
            return

        modal = AnnouncementModal(self)
        await interaction.response.send_modal(modal)

    async def publish_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You are not the author of this builder.", ephemeral=True)
            return

        if not self.target_channel:
            await interaction.response.send_message("❌ Please select a target channel first.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        announcement_embed = self.build_preview_embed()

        content_ping = ""
        if self.ping_option == "everyone":
            content_ping = "@everyone"
        elif self.ping_option == "here":
            content_ping = "@here"
        elif self.ping_option == "staff" and self.staff_role:
            content_ping = self.staff_role.mention

        try:
            if content_ping:
                await self.target_channel.send(content=content_ping, embed=announcement_embed)
            else:
                await self.target_channel.send(embed=announcement_embed)

            await interaction.followup.send(f"✅ Announcement successfully published to {self.target_channel.mention}!", ephemeral=True)

            # Cleanup
            await self.message.delete()
            self.stop()
        except Exception as e:
            traceback.print_exc()
            await interaction.followup.send(f"❌ Failed to send announcement: {e}", ephemeral=True)

    async def cancel_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("❌ You are not the author of this builder.", ephemeral=True)
            return

        await interaction.response.defer()
        await self.message.delete()
        self.stop()

    async def on_timeout(self):
        try:
            if self.message:
                await self.message.delete()
        except discord.HTTPException:
            pass

    def build_preview_embed(self) -> discord.Embed:
        theme = THEMES[self.theme_key]

        # Ensure title prefix emoji
        title_text = self.title_val
        # Check if title already starts with the theme's emoji
        if not title_text.startswith(theme["emoji"]):
            # Check if it starts with any common announcement emoji, if not prepend theme emoji
            if not any(title_text.startswith(e) for e in ["📢", "✅", "⚠️", "🚨", "🎉", "🔥", "🔔", "✨", "📌"]):
                title_text = f"{theme['emoji']} {title_text}"

        embed = discord.Embed(
            title=title_text,
            color=theme['color'],
            timestamp=discord.utils.utcnow()
        )

        # Build description
        desc_parts = []
        if self.subtitle_val:
            desc_parts.append(f"***{self.subtitle_val}***\n")

        desc_parts.append(self.body_val)
        embed.description = "\n".join(desc_parts)

        # Format bullet points if provided
        if self.points_val:
            formatted_lines = []
            for line in self.points_val.split("\n"):
                line = line.strip()
                if not line:
                    continue
                # Prepend default list emoji if no bullet-like symbol is present
                if not (line.startswith("🔹") or line.startswith("🔸") or line.startswith("•") or
                        line.startswith("-") or line.startswith("*") or line.startswith("✅") or
                        line.startswith("📌") or line.startswith("❌") or line.startswith("▪️") or
                        line.startswith("▫️")):
                    line = f"🔹 {line}"
                formatted_lines.append(line)

            if formatted_lines:
                embed.add_field(
                    name="📋 Key Details",
                    value="\n".join(formatted_lines),
                    inline=False
                )

        # Banner image
        if self.image_url and (self.image_url.startswith("http://") or self.image_url.startswith("https://")):
            embed.set_image(url=self.image_url)

        embed.set_footer(
            text=f"SX2 Announcements | Sent by {self.author.display_name}",
            icon_url=self.author.display_avatar.url
        )

        return embed

    def build_control_embed(self) -> discord.Embed:
        channel_name = f"<#{self.target_channel.id}>" if self.target_channel else "❌ *Not Selected*"
        ping_label = "🔕 None"
        if self.ping_option == "everyone":
            ping_label = "📢 @everyone"
        elif self.ping_option == "here":
            ping_label = "💬 @here"
        elif self.ping_option == "staff" and self.staff_role:
            ping_label = f"🛡️ Staff Role ({self.staff_role.mention})"

        theme_name = THEMES[self.theme_key]["name"]

        embed = discord.Embed(
            title="🔧 SX2 Announcement Builder",
            description=(
                "Customize your server announcement using the controls below. "
                "The message below this card shows a **live preview** of the final embed.\n\n"
                f"📂 **Target Channel:** {channel_name}\n"
                f"🎨 **Theme Color:** {theme_name}\n"
                f"🔔 **Ping Mention:** {ping_label}\n"
            ),
            color=discord.Color.dark_grey()
        )

        embed.add_field(
            name="💡 How to Use",
            value=(
                "1. Choose a **Target Channel** using the dropdown.\n"
                "2. Click **✍️ Edit Content** to change Title, Subtitle, Body, etc.\n"
                "3. Set your **Theme** and **Ping** options.\n"
                "4. When it looks perfect, click **🚀 Send Announcement**!"
            ),
            inline=False
        )

        return embed

    async def update_view(self, interaction: discord.Interaction):
        control_embed = self.build_control_embed()
        preview_embed = self.build_preview_embed()

        # Disable/enable Publish button based on channel selection
        self.publish_btn.disabled = (self.target_channel is None)

        await interaction.response.edit_message(
            embeds=[control_embed, preview_embed],
            view=self
        )


class Announce(commands.Cog):
    """Cog for managing highly customizable, interactive announcements."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        """All commands in this cog require Administrator permissions and must be in a guild."""
        if ctx.guild is None:
            return False
        return ctx.author.guild_permissions.administrator

    @commands.command(name="announce")
    async def announce(self, ctx):
        """Spawns the interactive announcement builder."""
        # 1. Fetch Staff Role ID from Supabase settings table if configured
        db = self.bot.db_manager
        staff_role_id = await db.get_setting_value(ctx.guild.id, "staff_role_id")
        staff_role = ctx.guild.get_role(staff_role_id) if staff_role_id else None

        # 2. Instantiate view
        view = AnnouncementBuilderView(ctx.author, ctx.guild, self.bot, staff_role)

        # 3. Build embeds
        control_embed = view.build_control_embed()
        preview_embed = view.build_preview_embed()

        # Send control + preview message
        view.message = await ctx.send(embeds=[control_embed, preview_embed], view=view)


async def setup(bot):
    await bot.add_cog(Announce(bot))
