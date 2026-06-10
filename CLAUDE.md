# SX2 Suggestions Bot — Development Summary & Handover

This document summarizes the changes, features, database schema, and operational setup for the **SX2 Suggestions Bot** (migrated from local JSON storage to Supabase).

---

## 🏗️ Architecture Overview

The bot is built using `discord.py` (v2.0+) and connects asynchronously to a **Supabase PostgreSQL** database. It is structured into Modular Cogs:

1. **`bot.py`**: The entry point. Connects to Discord and Supabase, loads extensions, starts the keep-alive server, and handles dynamic prefix resolution per-server.
2. **`cogs/settings.py`**: Configuration cog for Administrators to change prefix, channels, categories, and roles dynamically.
3. **`cogs/suggestions.py`**: Suggestion system — logs ideas, posts them with 👍/👎 voting, and provides a staff review workflow (approve/deny/consider) that recolours the message and DMs the author.
4. **`cogs/feedback.py`**: Feedback logging system (supports general, bug, idea, and compliment types).
5. **`cogs/tickets.py`**: Support ticket system using Discord Buttons and Views. Tracks ticket counts and states in the database.
6. **`cogs/help.py`**: Custom help menu and advanced global error handler.
7. **`utils/supabase_client.py`**: Handles database connection, caching guild settings, and querying tables.
8. **`keep_alive.py`**: Simple Flask web server to allow 24/7 uptime monitoring.

---

## 🗄️ Database Schema & Policies

Below is the database schema created in Supabase to support multi-server functionality.

### SQL Schema
```sql
-- 1. Server Configuration
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    prefix VARCHAR(10) DEFAULT '!',
    suggestion_channel_id BIGINT,
    feedback_channel_id BIGINT,
    resolved_tickets_channel_id BIGINT,
    ticket_category_id BIGINT,
    ticket_new_category_id BIGINT,
    ticket_working_category_id BIGINT,
    staff_role_id BIGINT,
    ticket_admin_notify_role_id BIGINT,
    panel_counter INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 2. Suggestions Log
CREATE TABLE IF NOT EXISTS suggestions (
    id BIGSERIAL PRIMARY KEY,
    suggestion_number BIGINT NOT NULL,        -- per-guild number shown as #N
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,                  -- the suggestion author
    message_id BIGINT,                        -- Discord message id (so reviews can edit it)
    content TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',     -- pending | approved | denied | considered
    reviewer_id BIGINT,                       -- staff member who reviewed
    review_reason TEXT,                       -- optional reason given on review
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 3. Feedback Log
CREATE TABLE IF NOT EXISTS feedback (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 4. Tickets Log
CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY,
    ticket_number BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL UNIQUE,
    opener_id BIGINT NOT NULL,
    status VARCHAR(20) DEFAULT 'open',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    closed_at TIMESTAMP WITH TIME ZONE
);
```

### Row-Level Security (RLS) Policies
To allow the bot to query and modify records using the public `anon` key, RLS policies must be applied:
```sql
-- guild_settings policies
CREATE POLICY "Allow anon select on guild_settings" ON guild_settings FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon insert on guild_settings" ON guild_settings FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow anon update on guild_settings" ON guild_settings FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- suggestions policies
CREATE POLICY "Allow anon select on suggestions" ON suggestions FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon insert on suggestions" ON suggestions FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow anon update on suggestions" ON suggestions FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- feedback policies
CREATE POLICY "Allow anon select on feedback" ON feedback FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon insert on feedback" ON feedback FOR INSERT TO anon WITH CHECK (true);

-- tickets policies
CREATE POLICY "Allow anon select on tickets" ON tickets FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon insert on tickets" ON tickets FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow anon update on tickets" ON tickets FOR UPDATE TO anon USING (true) WITH CHECK (true);
```

---

## ⌨️ Command Guide

Prefixes are dynamic (`{p}` below represents the server's configured prefix, defaulting to `!`).

### User Commands
* `{p}suggest <text>`: Submits a suggestion to the server's configured suggestions channel.
* `{p}feedback <general|bug|idea|compliment> <message>`: Submits logged feedback to the staff.
* `{p}ticket`: Spawns the persistent Support Ticket creation panel.
* `{p}help`: Displays a list of commands.

### Staff Suggestion-Review Commands
Usable by Administrators, members with **Manage Server**, or the configured staff role. `<#>` is the suggestion's per-server number (shown as `#N` on the suggestion embed).
* `{p}approve <#> [reason]`: Marks a suggestion Approved (green), stamps the decision on the original message, and DMs the author.
* `{p}deny <#> [reason]`: Marks a suggestion Denied (red) and notifies the author.
* `{p}consider <#> [reason]`: Marks a suggestion Under Consideration (orange) and notifies the author.

### Admin Configuration Commands
* `{p}show_config`: Displays current settings for the server.
* `{p}set_prefix <prefix>`: Sets the command prefix.
* `{p}set_suggestion_channel <#channel>`: Sets the suggestion log channel.
* `{p}set_feedback_channel <#channel>`: Sets the feedback log channel.
* `{p}set_resolved_channel <#channel>`: Sets the channel where resolved ticket transcripts are logged.
* `{p}set_staff_role <@role>`: Sets the role that gets permissions to view support ticket channels.
* `{p}set_ticket_admin_role <@role>`: Sets the role of staff members notified when a new ticket is opened.
* `{p}set_ticket_category <Category Name or ID>`: Sets the default fallback category for ticket channels.
* `{p}set_new_ticket_category <Category Name or ID>`: Sets the category for newly opened tickets.
* `{p}set_working_ticket_category <Category Name or ID>`: Sets the category for active tickets staff are working on.
* `{p}announce`: Launches the interactive visual Announcement builder panel.

---

## 🚀 Hosting Setup (Render + UptimeRobot)

1. **Render (Free Web Service)**:
   * **Language**: `Python`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python bot.py`
   * **Environment Variables**:
     * `TOKEN`: Discord Bot Token.
     * `SUPABASE_URL`: Supabase project URL.
     * `SUPABASE_KEY`: Supabase API client anon key.
2. **UptimeRobot (Pinger)**:
   * Setup an **HTTP(s) Monitor** targeting the Render Web Service URL (e.g. `https://name.onrender.com/`) at a **5-minute interval** to prevent the container from sleeping.
