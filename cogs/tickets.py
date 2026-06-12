# ============================================================
# cogs/tickets.py — The Ticket System
#
# This file handles everything related to support tickets:
# - Sending the panel (button) users click to open a ticket
# - Creating a private channel for the ticket
# - Closing tickets
# ============================================================

import asyncio
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord.ext import commands

from config import (
    COLOR_INFO,
    COLOR_SUCCESS,
    RESOLVED_TICKETS_CHANNEL_ID,
    STAFF_ROLE_ID,
    TICKET_ADMIN_NOTIFY_ROLE_ID,
    TICKET_CATEGORY_ID,
    TICKET_NEW_CATEGORY_ID,
    TICKET_WORKING_CATEGORY_ID,
)


def _parse_ticket_meta(channel: discord.TextChannel) -> dict:
    """Read ticket metadata from channel topic."""
    meta = {}
    if not channel.topic:
        return meta

    for part in channel.topic.split("|"):
        cleaned = part.strip()
        if "=" not in cleaned:
            continue
        key, value = cleaned.split("=", 1)
        meta[key.strip()] = value.strip()
    return meta


def _build_ticket_topic(
    ticket_id: int, opener_id: int, status: str, created_ts: str
) -> str:
    """Store ticket data in topic so it survives bot restarts."""
    return f"ticket_id={ticket_id} | opener={opener_id} | status={status} | created={created_ts}"


_CONFIG_PLACEHOLDER = 123456789012345678


def _unwrap_config_id(raw_value):
    """
    Normalize IDs loaded from config.
    Common mistake: STAFF_ROLE_ID = (123,) → tuple breaks guild.get_role().
    """
    if isinstance(raw_value, (tuple, list)):
        if len(raw_value) != 1:
            return None
        raw_value = raw_value[0]
    if isinstance(raw_value, str):
        raw_value = raw_value.strip().replace("`", "")
        if not raw_value.isdigit():
            return None
        raw_value = int(raw_value)
    if isinstance(raw_value, bool):  # bool is subclass of int
        return None
    return raw_value if isinstance(raw_value, int) else None


def _safe_category_id(raw_value) -> int | None:
    """Treat placeholder IDs as 'not configured'."""
    v = _unwrap_config_id(raw_value)
    if v is None or v == _CONFIG_PLACEHOLDER:
        return None
    return v


def _category_from_guild_channel(
    channel: discord.abc.GuildChannel | None,
) -> discord.CategoryChannel | None:
    """Turn a resolved guild channel into the CategoryChannel tickets should live under."""
    if channel is None:
        return None
    if isinstance(channel, discord.CategoryChannel):
        return channel
    # If someone pasted a text/voice channel ID inside the category, use its parent folder.
    parent = getattr(channel, "category", None)
    if isinstance(parent, discord.CategoryChannel):
        return parent
    return None


def _pick_category_sync(
    guild: discord.Guild, category_id: int | None
) -> discord.CategoryChannel | None:
    """Resolve category from cache only (fast path)."""
    if not category_id:
        return None

    ch = guild.get_channel(category_id)
    cat = _category_from_guild_channel(ch)
    if cat:
        return cat

    for cat in guild.categories:
        if cat.id == category_id:
            return cat
    return None


async def _pick_category(
    guild: discord.Guild,
    client: discord.Client,
    preferred_id: int | None,
    fallback_id: int | None,
) -> discord.CategoryChannel | None:
    """
    Pick the first category that exists. Uses API fetch if the ID is valid but not cached
    (common cause of channels being created at guild root: category=None).
    """
    for cid in (preferred_id, fallback_id):
        if not cid:
            continue

        cat = _pick_category_sync(guild, cid)
        if cat:
            return cat

        try:
            fetched = await client.fetch_channel(cid)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            continue

        cat = _category_from_guild_channel(fetched)
        if cat:
            return cat

    return None


def _panel_counter_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent / "data" / "ticket_panel_counters.json"
    )


async def _get_guild_setting(bot, guild_id: int, key: str, fallback):
    if not hasattr(bot, "db_manager"):
        return fallback
    return await bot.db_manager.get_setting_value(guild_id, key, fallback)


async def next_panel_sequence(bot, guild_id: int) -> int:
    """Persistent panel # per guild (uses Supabase, falls back to local counter)."""
    if bot.db_manager.client:
        try:
            # Check settings
            settings = await bot.db_manager.get_settings(guild_id)
            current = settings.get("panel_counter", 0) or 0
            new_val = current + 1
            await bot.db_manager.update_setting(guild_id, "panel_counter", new_val)
            return new_val
        except Exception as e:
            print(f"[tickets] Failed to increment panel counter in Supabase: {e}")

    # Fallback to local json
    path = _panel_counter_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    key = str(guild_id)
    n = int(data.get(key, 0)) + 1
    data[key] = n
    try:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass
    return n


async def _next_ticket_id(bot, guild: discord.Guild) -> int:
    """Generate the next numeric ticket ID. First queries Supabase, then falls back to channel scan."""
    if bot.db_manager.client:
        try:
            response = await bot.db_manager.client.table("tickets").select("ticket_number").eq("guild_id", guild.id).order("ticket_number", desc=True).limit(1).execute()
            if response.data and len(response.data) > 0:
                return int(response.data[0]["ticket_number"]) + 1
            return 1
        except Exception as e:
            print(f"[tickets] Failed to fetch next ticket ID from Supabase: {e}")

    max_ticket_id = 0
    for channel in guild.text_channels:
        meta = _parse_ticket_meta(channel)
        raw_id = meta.get("ticket_id")
        if raw_id and raw_id.isdigit():
            max_ticket_id = max(max_ticket_id, int(raw_id))
    return max_ticket_id + 1


async def _notify_roles_for_guild(bot, guild: discord.Guild) -> list[discord.Role]:
    """Roles to ping in-ticket (ticket admins first, then staff if different)."""
    roles: list[discord.Role] = []
    seen: set[int] = set()
    
    admin_notify_rid = await _get_guild_setting(bot, guild.id, "ticket_admin_notify_role_id", TICKET_ADMIN_NOTIFY_ROLE_ID)
    staff_rid = await _get_guild_setting(bot, guild.id, "staff_role_id", STAFF_ROLE_ID)
    
    for raw in (admin_notify_rid, staff_rid):
        rid = _safe_category_id(raw)
        if not rid:
            continue
        role = guild.get_role(rid)
        if role is None or role.id in seen:
            continue
        seen.add(role.id)
        roles.append(role)
    return roles


async def _dm_ticket_admins(
    bot,
    guild: discord.Guild,
    channel: discord.TextChannel,
    opener: discord.abc.User,
    ticket_id: int,
) -> tuple[int, int]:
    """
    DM members who have the notify role. Returns (sent_count, fail_count).
    Uses role.members directly — no full guild chunk needed.
    The old guild.chunk(cache=True) call was the source of the 1-2 minute delay.
    Server Members Intent must be ON in the Developer Portal (you've confirmed it is).
    """
    admin_notify_rid = await _get_guild_setting(bot, guild.id, "ticket_admin_notify_role_id", TICKET_ADMIN_NOTIFY_ROLE_ID)
    staff_rid = await _get_guild_setting(bot, guild.id, "staff_role_id", STAFF_ROLE_ID)

    notify_rid = _safe_category_id(admin_notify_rid)
    if notify_rid is None:
        notify_rid = _safe_category_id(staff_rid)
    if notify_rid is None:
        print(
            "[tickets] DM skip: no TICKET_ADMIN_NOTIFY_ROLE_ID / STAFF_ROLE_ID configured"
        )
        return 0, 0

    role = guild.get_role(notify_rid)
    if role is None:
        print(f"[tickets] DM skip: role id {notify_rid} not found in this server")
        return 0, 0

    embed = discord.Embed(
        title=f"🎫 New ticket #{ticket_id}",
        description=f"{opener.mention} opened a ticket and may need help.",
        color=COLOR_INFO,
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Channel", value=channel.jump_url, inline=False)

    # role.members works directly when Server Members Intent is enabled — no chunk needed.
    candidates = [m for m in role.members if not m.bot]
    print(f"[tickets] DM candidates for role «{role.name}»: {len(candidates)}")

    sent, failed = 0, 0
    for member in candidates:
        try:
            await member.send(embed=embed)
            sent += 1
        except discord.Forbidden as exc:
            failed += 1
            print(f"[tickets] DM Forbidden for {member} ({member.id}): {exc}")
        except discord.HTTPException as exc:
            failed += 1
            print(f"[tickets] DM HTTP error for {member} ({member.id}): {exc}")
    return sent, failed


async def _send_staff_role_ping_line(
    bot,
    channel: discord.TextChannel,
    guild: discord.Guild,
    user: discord.abc.User,
    ticket_id: int,
) -> bool:
    """
    Ping configured roles inside the ticket channel. Works even when member cache/DMs fail.
    Bot needs permission to mention those roles (mentionable role OR bot **Mention @everyone** perm).
    """
    roles = await _notify_roles_for_guild(bot, guild)
    if not roles:
        return False
    mentions = " ".join(r.mention for r in roles)
    content = f"{mentions} — **New ticket #{ticket_id}** from {user.mention}"
    try:
        await channel.send(
            content=content,
            allowed_mentions=discord.AllowedMentions(roles=roles, users=[user]),
        )
        return True
    except discord.Forbidden:
        print(
            "[tickets] Role ping failed (Forbidden): give the bot **Send Messages** and "
            "**Mention @everyone, @here and All Roles** (or make ticket roles mentionable)."
        )
        traceback.print_exc()
        return False
    except discord.HTTPException as exc:
        print(f"[tickets] Role ping HTTP error: {exc}")
        traceback.print_exc()
        return False


class TicketControlsView(discord.ui.View):
    """Buttons shown inside each ticket channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🛠 Mark as Working",
        style=discord.ButtonStyle.secondary,
        custom_id="ticket_mark_working",
    )
    async def mark_working(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        guild = interaction.guild
        channel = interaction.channel
        if guild is None or not isinstance(channel, discord.TextChannel):
            return

        await interaction.response.defer(ephemeral=True)

        meta = _parse_ticket_meta(channel)
        ticket_id = meta.get("ticket_id", "N/A")
        opener = meta.get("opener", "unknown")
        created = meta.get("created", datetime.now(timezone.utc).isoformat())

        tid_num = int(ticket_id) if str(ticket_id).isdigit() else 0
        op_num = int(opener) if str(opener).isdigit() else 0
        new_topic = _build_ticket_topic(tid_num, op_num, "working", created)

        # Prefer the dedicated WORKING category only (fallback to TICKET_CATEGORY caused no-op when both matched).
        db = interaction.client.db_manager
        cat_work_id = await db.get_setting_value(guild.id, "ticket_working_category_id", TICKET_WORKING_CATEGORY_ID)
        cat_fallback_id = await db.get_setting_value(guild.id, "ticket_category_id", TICKET_CATEGORY_ID)

        working_category = await _pick_category(
            guild,
            interaction.client,
            _safe_category_id(cat_work_id),
            None,
        )
        if working_category is None:
            working_category = await _pick_category(
                guild,
                interaction.client,
                _safe_category_id(cat_fallback_id),
                None,
            )

        move_note = ""
        try:
            if working_category is None:
                move_note = (
                    "\n\n⚠️ No working category configured — set `TICKET_WORKING_CATEGORY_ID` (or `TICKET_CATEGORY_ID`) "
                    "to a **category** ID, then try again."
                )
                await channel.edit(
                    topic=new_topic,
                    reason=f"Ticket #{ticket_id} marked working (topic only)",
                )
            elif channel.category_id != working_category.id:
                await channel.edit(
                    category=working_category,
                    sync_permissions=False,
                    topic=new_topic,
                    reason=f"Ticket #{ticket_id} moved to working by {interaction.user}",
                )
                move_note = f"\n\n📁 Moved under **{working_category.name}**."
            else:
                await channel.edit(
                    topic=new_topic, reason=f"Ticket #{ticket_id} marked working"
                )
                move_note = f"\n\n📁 Already under **{working_category.name}**."
            
            # Log working status in Supabase
            if db.client:
                try:
                    await db.client.table("tickets").update({"status": "working"}).eq("channel_id", channel.id).execute()
                except Exception as e:
                    print(f"❌ [Tickets] Failed to update status to 'working' in Supabase: {e}")
        except discord.Forbidden:
            move_note = (
                "\n\n❌ **Missing permission** to move or edit this channel. Give my role **Manage Channels** "
                "(and access to the working category), then try again."
            )
        except discord.HTTPException as exc:
            move_note = f"\n\n❌ Discord rejected the update: `{exc}`"

        await interaction.followup.send(
            f"🛠 Ticket **#{ticket_id}** is marked **WORKING**.{move_note}",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @discord.ui.button(
        label="✅ Resolve Ticket",
        style=discord.ButtonStyle.success,
        custom_id="ticket_resolve",
    )
    async def resolve_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        guild = interaction.guild
        channel = interaction.channel
        if guild is None or not isinstance(channel, discord.TextChannel):
            return

        meta = _parse_ticket_meta(channel)
        ticket_id = meta.get("ticket_id", "N/A")
        opener_id = meta.get("opener")
        created = meta.get("created", "Unknown")

        opener_mention = "Unknown User"
        if opener_id and opener_id.isdigit():
            opener_mention = f"<@{opener_id}>"

        db = interaction.client.db_manager
        res_ch_id = await db.get_setting_value(guild.id, "resolved_tickets_channel_id", RESOLVED_TICKETS_CHANNEL_ID)
        log_channel_id = _safe_category_id(res_ch_id)
        log_channel = guild.get_channel(log_channel_id) if log_channel_id else None

        if isinstance(log_channel, discord.TextChannel):
            log_embed = discord.Embed(
                title=f"✅ Ticket Resolved #{ticket_id}",
                color=COLOR_SUCCESS,
                timestamp=datetime.now(timezone.utc),
                description=(
                    f"**Opened by:** {opener_mention}\n"
                    f"**Closed by:** {interaction.user.mention}\n"
                    f"**Ticket channel:** `{channel.name}`\n"
                    f"**Created at:** `{created}`"
                ),
            )
            log_embed.add_field(name="Channel ID", value=f"`{channel.id}`", inline=True)
            log_embed.add_field(name="Guild", value=f"`{guild.name}`", inline=True)
            await log_channel.send(embed=log_embed)

        # Update status in Supabase
        if db.client:
            try:
                await db.client.table("tickets").update({
                    "status": "resolved",
                    "closed_at": datetime.now(timezone.utc).isoformat()
                }).eq("channel_id", channel.id).execute()
            except Exception as e:
                print(f"❌ [Tickets] Failed to update status to 'resolved' in Supabase: {e}")

        await interaction.response.send_message(
            f"✅ Ticket **#{ticket_id}** resolved. Closing channel in 5 seconds...",
            allowed_mentions=discord.AllowedMentions.none(),
        )

        await asyncio.sleep(5)
        await channel.delete(
            reason=f"Ticket #{ticket_id} resolved by {interaction.user}"
        )


# ── OPEN TICKET BUTTON ────────────────────────────────────────
# This button appears in the ticket panel message.
# Users click it to create their own private ticket channel.
# ── TICKET REASON MODAL ───────────────────────────────────────
# This modal pops up when a user clicks the "Open a Ticket" button.
# It collects the subject and issue description before creating the channel.
class TicketReasonModal(discord.ui.Modal):

    def __init__(self, category: discord.CategoryChannel):
        super().__init__(title="Open a Support Ticket")
        self.category = category

        self.subject_input = discord.ui.TextInput(
            label="Subject / Topic",
            placeholder="e.g. Help with roles, bug report, billing query",
            max_length=100,
            required=True,
        )
        self.desc_input = discord.ui.TextInput(
            label="Description of your issue",
            style=discord.TextStyle.paragraph,
            placeholder="Please detail your request here so staff can assist you quickly...",
            max_length=1000,
            required=True,
        )

        self.add_item(self.subject_input)
        self.add_item(self.desc_input)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        if guild is None:
            return

        # Defer so Discord interaction doesn't expire during text channel creation
        await interaction.response.defer(ephemeral=True)

        subject = self.subject_input.value
        description = self.desc_input.value

        db = interaction.client.db_manager

        # ── Set permissions for the new ticket channel ────────
        # By default nobody can see it, except the user and staff
        # IMPORTANT: @everyone is denied view_channel — the bot MUST be allowed explicitly or it
        # cannot post the welcome message or buttons (unless the bot has Administrator).
        ticket_member_perms = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            embed_links=True,
            attach_files=True,
        )
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False
            ),  # Hide from everyone
            user: ticket_member_perms,
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_channels=True,
                manage_messages=True,
                embed_links=True,
                attach_files=True,
            ),
        }

        # Staff + ticket-admin roles must see the channel (not only staff ID — admins may use a separate role).
        for role in await _notify_roles_for_guild(interaction.client, guild):
            overwrites.setdefault(role, ticket_member_perms)

        # ── Create the ticket channel ─────────────────────────
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower()}",
            category=self.category,
            overwrites=overwrites,
            reason=f"Ticket opened by {user}",
        )

        # Belt-and-suspenders: if Discord still left the channel uncategorized, force the folder.
        if channel.category_id != self.category.id:
            await channel.edit(
                category=self.category, reason="Place ticket under configured category"
            )

        ticket_id = await _next_ticket_id(interaction.client, guild)
        created_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        await channel.edit(
            topic=_build_ticket_topic(ticket_id, user.id, "new", created_ts),
            reason=f"Ticket #{ticket_id} metadata initialized",
        )

        # Log the ticket in Supabase
        if db.client:
            try:
                await db.client.table("tickets").insert({
                    "ticket_number": ticket_id,
                    "guild_id": guild.id,
                    "channel_id": channel.id,
                    "opener_id": user.id,
                    "status": "open"
                }).execute()
            except Exception as e:
                print(f"❌ [Tickets] Failed to log new ticket to Supabase: {e}")

        # ── 1) GREETING FIRST (instant, so user sees activity right away) ──
        try:
            await channel.send(
                content=f"{user.mention} 👋 **Ticket #{ticket_id}** — describe your issue in this channel.",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        except discord.HTTPException as exc:
            print(f"[tickets] Plain greeting send failed: {exc}")
            traceback.print_exc()
            await interaction.followup.send(
                "❌ I created the ticket channel but **could not send the greeting**. "
                "Check bot permissions on the ticket category (**Send Messages**, **Embed Links**). "
                f"Details printed in the bot console.",
                ephemeral=True,
            )
            return

        # ── 2) ROLE PING SECOND (also instant — uses cached roles) ──
        ping_ok = await _send_staff_role_ping_line(interaction.client, channel, guild, user, ticket_id)

        # ── 3) Confirm to the user RIGHT NOW (don't wait for DMs) ──
        await interaction.followup.send(
            f"✅ Your ticket has been created: {channel.mention}",
            ephemeral=True,
        )

        # ── 4) Send info embed + DM staff in the BACKGROUND ──
        async def _send_info_embed_and_dm():
            """Send the info embed + DM staff. Runs after the user already has confirmation."""
            try:
                sent_dm, failed_dm = await _dm_ticket_admins(
                    interaction.client, guild, channel, user, ticket_id
                )
            except Exception as exc:
                print(f"[tickets] Background DM task failed: {exc}")
                traceback.print_exc()
                sent_dm, failed_dm = 0, 0

            notify_rid = await db.get_setting_value(guild.id, "ticket_admin_notify_role_id", TICKET_ADMIN_NOTIFY_ROLE_ID)
            staff_rid = await db.get_setting_value(guild.id, "staff_role_id", STAFF_ROLE_ID)

            if sent_dm:
                notify_field = (
                    f"✅ **{sent_dm}** staff member(s) were sent a **direct message**."
                    + (
                        f"\n_{failed_dm} could not receive DMs (Privacy: allow DMs from server members)._"
                        if failed_dm
                        else ""
                    )
                )
            elif ping_ok:
                notify_field = (
                    "✅ Staff were **pinged with @roles** in this channel (see message above). "
                    "Use this if DMs are blocked."
                )
            elif _safe_category_id(notify_rid) or _safe_category_id(staff_rid):
                notify_field = (
                    "⚠️ No DM and **role ping failed** — give the bot **Send Messages** + "
                    "**Mention @everyone, @here and All Roles**, or make ticket roles **mentionable**. "
                    "Also enable **Server Members Intent** in the Developer Portal for DMs."
                )
            else:
                notify_field = "⚠️ Set staff roles in your configuration command `!show_config`."

            embed = discord.Embed(
                title=f"🎫 Support Ticket #{ticket_id}",
                description=(
                    "**Next steps**\n"
                    "• Explain your issue clearly\n"
                    "• Add errors or screenshots if you can\n"
                    "• Staff will reply here when available"
                ),
                color=COLOR_INFO,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
            embed.add_field(
                name="Opened by",
                value=f"{user.mention}\n`{user}` · `{user.id}`",
                inline=False,
            )
            
            # Modal results fields
            embed.add_field(name="📋 Subject / Topic", value=subject, inline=False)
            embed.add_field(name="📝 Issue Description", value=description, inline=False)

            embed.add_field(name="Ticket #", value=f"`#{ticket_id}`", inline=True)
            embed.add_field(name="Status", value="`NEW`", inline=True)
            embed.add_field(name="Staff alerts", value=notify_field, inline=False)
            embed.set_footer(text="Staff: Working / Resolved buttons below.")

            try:
                await channel.send(embed=embed, view=TicketControlsView())
            except discord.HTTPException as exc:
                print(f"[tickets] Embed/button send failed: {exc}")
                traceback.print_exc()

        # Fire-and-forget background task
        asyncio.create_task(_send_info_embed_and_dm())


# ── OPEN TICKET BUTTON ────────────────────────────────────────
# This button appears in the ticket panel message.
# Users click it to trigger the TicketReasonModal.
class OpenTicketButton(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="🎫 Open a Ticket",
        style=discord.ButtonStyle.primary,  # Blue button
        custom_id="open_ticket",
    )
    async def open_ticket(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        guild = interaction.guild
        user = interaction.user
        if guild is None:
            return

        # ── Find the ticket category ──────────────────────────
        db = interaction.client.db_manager
        cat_new_id = await db.get_setting_value(guild.id, "ticket_new_category_id", TICKET_NEW_CATEGORY_ID)
        cat_fallback_id = await db.get_setting_value(guild.id, "ticket_category_id", TICKET_CATEGORY_ID)

        # Tickets will be created inside this category folder
        category = await _pick_category(
            guild,
            interaction.client,
            _safe_category_id(cat_new_id),
            _safe_category_id(cat_fallback_id),
        )

        if category is None:
            await interaction.response.send_message(
                "❌ **Ticket category not found.** Ask an admin to set it up using `!set_new_ticket_category` or `!set_ticket_category`.",
                ephemeral=True,
            )
            return

        # ── Check if user already has an open ticket ──────────
        # We look for a channel that starts with "ticket-" and has their name
        existing = discord.utils.get(
            guild.text_channels, name=f"ticket-{user.name.lower()}"
        )
        if existing:
            await interaction.response.send_message(
                f"❌ You already have an open ticket: {existing.mention}",
                ephemeral=True,  # Only the user can see this message
            )
            return

        # Trigger the reason modal to collect context before creating channel
        modal = TicketReasonModal(category)
        await interaction.response.send_modal(modal)


# ── TICKETS COG ───────────────────────────────────────────────
# A "Cog" is like a plugin. It groups related commands together.
class Tickets(commands.Cog):

    def __init__(self, bot):
        self.bot = bot  # Save the bot so we can use it later

    async def cog_load(self):
        # Persistent buttons (timeout=None + custom_id) must be registered for interactions after restarts.
        self.bot.add_view(OpenTicketButton())
        self.bot.add_view(TicketControlsView())
        print("[cogs.tickets] Registered persistent buttons and ticket control views.")

    # ── !ticket command ───────────────────────────────────────
    # Post the ticket panel in the current channel (any member can run it).
    # Example usage: !ticket
    @commands.command(name="ticket")
    async def send_ticket_panel(self, ctx):
        """Sends the ticket panel with the Open Ticket button."""

        if ctx.guild is None:
            await ctx.send("❌ Use `!ticket` in a server channel.")
            return

        author = ctx.author
        panel_no = await next_panel_sequence(self.bot, ctx.guild.id)
        next_ticket_no = await _next_ticket_id(self.bot, ctx.guild)

        embed = discord.Embed(
            title="🎫 Support Tickets",
            description=(
                "Need help? Click the button below to open a **private** support ticket.\n\n"
                "Our staff team will assist you as soon as possible."
            ),
            color=COLOR_SUCCESS,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(
            name=f"{author.display_name}", icon_url=author.display_avatar.url
        )
        embed.add_field(
            name="Posted with command",
            value=f"`!ticket` by {author.mention}\n`{author.name}` · user ID `{author.id}`",
            inline=False,
        )
        embed.add_field(
            name="Panel # (tracking)",
            value=f"`#{panel_no}` — tell staff this **panel number** if they ask.",
            inline=True,
        )
        embed.add_field(
            name="Next ticket # (at post time)",
            value=(
                f"**`#{next_ticket_no}`** — number assigned when someone clicks **Open**. "
                "If other tickets were opened after this panel was posted, the real ID may be higher."
            ),
            inline=False,
        )
        embed.set_footer(
            text=f"Panel #{panel_no} • Tickets are private to you and staff."
        )

        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

        panel_msg = await ctx.send(embed=embed, view=OpenTicketButton())
        embed.add_field(
            name="Panel message ID",
            value=f"`{panel_msg.id}` — for logs / Discord search.",
            inline=False,
        )
        embed.set_footer(
            text=f"Panel #{panel_no} • msg `{panel_msg.id}` • !ticket by {author.name}"
        )
        try:
            await panel_msg.edit(embed=embed)
        except discord.HTTPException:
            pass


# ── SETUP FUNCTION ────────────────────────────────────────────
# Discord requires this function at the bottom of every cog file.
# It "registers" the cog with the bot.
async def setup(bot):
    await bot.add_cog(Tickets(bot))
