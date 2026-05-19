# ============================================================
# views/ticket_view.py — Persistent Button Views
#
# "Views" are the interactive buttons you see in Discord messages.
# This file holds the button logic for the ticket system.
#
# WHY is this a separate file?
# Because buttons need to survive even if the bot restarts.
# We register them here so the bot remembers them on startup.
# ============================================================

import discord
import asyncio

from config import TICKET_CATEGORY_ID, STAFF_ROLE_ID, COLOR_INFO


# ── CLOSE TICKET BUTTON ───────────────────────────────────────
# This button appears inside every ticket channel.
# When clicked, it closes (deletes) the ticket channel.
class CloseTicketView(discord.ui.View):

    def __init__(self):
        # timeout=None = the button never expires, even after bot restarts
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🔒 Close Ticket",
        style=discord.ButtonStyle.danger,   # Red button colour
        custom_id="persistent_close_ticket" # Must be unique across all buttons
    )
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Closes the ticket channel when a staff member clicks this button."""

        # Let the user know the ticket is being closed
        await interaction.response.send_message(
            "🔒 This ticket will be closed in **5 seconds**...",
            ephemeral=False  # Everyone in the ticket can see this
        )

        await asyncio.sleep(5)  # Wait 5 seconds so the user can read it

        # Delete the channel — this permanently removes the ticket
        await interaction.channel.delete(reason="Ticket closed via button")


# ── OPEN TICKET BUTTON ────────────────────────────────────────
# This button appears in the ticket panel (the message staff posts).
# Any user can click it to open a new ticket.
class OpenTicketView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Open a Ticket",
        style=discord.ButtonStyle.primary,  # Blue button colour
        custom_id="persistent_open_ticket"  # Must be unique
    )
    async def open_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Creates a private ticket channel when a user clicks this button."""

        guild = interaction.guild
        user = interaction.user

        # ── Find the ticket category ──────────────────────────
        # New ticket channels will be placed inside this category
        category = guild.get_channel(TICKET_CATEGORY_ID)

        # ── Check if the user already has a ticket open ───────
        existing_ticket = discord.utils.get(
            guild.text_channels,
            name=f"ticket-{user.name.lower()}"
        )

        if existing_ticket:
            # Tell only the user (ephemeral = only they can see it)
            await interaction.response.send_message(
                f"⚠️ You already have an open ticket! Go here: {existing_ticket.mention}",
                ephemeral=True
            )
            return

        # ── Set who can see the new ticket channel ────────────
        # By default: nobody. Then we add the user and staff.
        overwrites = {
            # Everyone else is blocked from viewing
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            # The user who opened the ticket can view and send messages
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            # The bot itself needs access too
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        # Give the Staff role access if it exists
        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        # ── Create the private ticket channel ─────────────────
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower()}",
            category=category,
            overwrites=overwrites,
            topic=f"Support ticket for {user}",  # Shows in channel info
            reason=f"Ticket opened by {user}"
        )

        # ── Send the welcome message inside the ticket ─────────
        embed = discord.Embed(
            title="🎫 Support Ticket Opened",
            description=(
                f"Welcome {user.mention}! 👋\n\n"
                "A staff member will assist you shortly.\n\n"
                "**Please describe your issue:**\n"
                "• What is the problem?\n"
                "• Which command is not working?\n"
                "• Any other details?"
            ),
            color=COLOR_INFO
        )
        embed.set_footer(text="Staff: Click the button below to close this ticket when resolved.")

        # Send the embed + close button inside the new ticket channel
        await channel.send(content=user.mention, embed=embed, view=CloseTicketView())

        # ── Confirm to the user that the ticket was created ────
        await interaction.response.send_message(
            f"✅ Your ticket has been created: {channel.mention}",
            ephemeral=True  # Only the user sees this confirmation
        )
