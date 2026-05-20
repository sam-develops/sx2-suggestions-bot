# 🎫 SX2 Suggestions & Ticket Bot

A highly customizable, production-ready Discord bot built with `discord.py` and backed by **Supabase (PostgreSQL)**. It features an advanced ticket system using Discord UI components (Buttons/Views), an interactive suggestions logger, a structured feedback capture tool, and dynamic per-server configuration.

---

## ✨ Features

* **Multi-Server Settings**: Administrators can configure prefix, logs channels, category folders, and roles on the fly using database-backed configuration.
* **Support Ticket System**: Spawns an interactive panel with persistent Discord buttons. Supports moving tickets through states (`open` ➔ `working` ➔ `resolved`), generating transcripts, and logging resolved cases.
* **Suggestion System**: Records and increments sequential server suggestion logs.
* **Feedback Manager**: Standardizes user feedback categorized by type (`general`, `bug`, `idea`, `compliment`).
* **Robust Error Handler**: Active global exception handler providing detailed cards on permission blocks, parameter mismatches, and database issues.
* **24/7 Uptime Ready**: Built-in Flask server to keep the bot active indefinitely using Uptime pinger services.

---

## 🚀 Quick Setup

### 1. Supabase Database Initialization
Run the following SQL in your **Supabase Project SQL Editor** to create the tables:

```sql
-- 1. Server Configuration
CREATE TABLE guild_settings (
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
CREATE TABLE suggestions (
    id BIGSERIAL PRIMARY KEY,
    suggestion_number BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 3. Feedback Log
CREATE TABLE feedback (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- 4. Tickets Log
CREATE TABLE tickets (
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

#### Apply Row-Level Security (RLS) Policies
Run this query to enable the bot to write data securely using the client `anon` key:

```sql
-- guild_settings policies
CREATE POLICY "Allow anon select on guild_settings" ON guild_settings FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon insert on guild_settings" ON guild_settings FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow anon update on guild_settings" ON guild_settings FOR UPDATE TO anon USING (true) WITH CHECK (true);

-- suggestions policies
CREATE POLICY "Allow anon select on suggestions" ON suggestions FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon insert on suggestions" ON suggestions FOR INSERT TO anon WITH CHECK (true);

-- feedback policies
CREATE POLICY "Allow anon select on feedback" ON feedback FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon insert on feedback" ON feedback FOR INSERT TO anon WITH CHECK (true);

-- tickets policies
CREATE POLICY "Allow anon select on tickets" ON tickets FOR SELECT TO anon USING (true);
CREATE POLICY "Allow anon insert on tickets" ON tickets FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow anon update on tickets" ON tickets FOR UPDATE TO anon USING (true) WITH CHECK (true);
```

### 2. Configuration Setup
Create a `.env` file in the root directory:
```env
TOKEN=your_discord_bot_token
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_public_key
```

Edit the basic default settings (like fallback IDs and colors) in `config.py`.

---

## ⌨️ Bot Commands

Prefixes are dynamic (represented below as `!`). 

### 👥 User Commands

| Command | Usage | Description | Example |
| :--- | :--- | :--- | :--- |
| `suggest` | `!suggest <idea>` | Submits a suggestion to the suggestion channel. | `!suggest Add a music channel` |
| `feedback` | `!feedback <type> <text>` | Sends feedback (`general` \| `bug` \| `idea` \| `compliment`). | `!feedback bug The bot lag` |
| `ticket` | `!ticket` | Spawns the support ticket creation panel. | `!ticket` |
| `help` | `!help` | Displays the dynamic help menu. | `!help` |

### ⚙️ Admin Configuration Commands
*All configuration commands require **Administrator** permissions.*

| Command | Usage | Description |
| :--- | :--- | :--- |
| `show_config` | `!show_config` | Displays current server settings side-by-side with defaults. |
| `set_prefix` | `!set_prefix <prefix>` | Changes the command prefix (e.g. `?` or `bot.`). |
| `set_suggestion_channel` | `!set_suggestion_channel <#channel>` | Sets the channel where suggestions are posted. |
| `set_feedback_channel` | `!set_feedback_channel <#channel>` | Sets the channel where feedback logs are sent. |
| `set_resolved_channel` | `!set_resolved_channel <#channel>` | Sets the channel where resolved ticket transcripts are saved. |
| `set_staff_role` | `!set_staff_role <@role>` | Sets the Staff role that can view/manage ticket channels. |
| `set_ticket_admin_role` | `!set_ticket_admin_role <@role>` | Sets the Staff role notified in DMs when new tickets open. |
| `set_ticket_category` | `!set_ticket_category <CategoryName/ID>` | Sets the fallback category folder for ticket channels. |
| `set_new_ticket_category` | `!set_new_ticket_category <CategoryName/ID>` | Sets the category folder for newly opened tickets. |
| `set_working_ticket_category` | `!set_working_ticket_category <CategoryName/ID>` | Sets the category folder for active/working tickets. |

---

## 🌐 24/7 Hosting Guide

### 1. Render Deployment
1. Sign up for a free account on [Render.com](https://render.com/).
2. Create a new **Web Service** and link your GitHub repository.
3. Apply the following settings:
   * **Language**: `Python`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `python bot.py`
4. Add your `.env` variables (`TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY`) under the **Environment** tab.
5. Click **Deploy**.

### 2. Uptime Monitoring
To keep Render's free instance active:
1. Copy the public Web Service URL from the top of your Render dashboard (e.g., `https://my-discord-bot.onrender.com`).
2. Go to [UptimeRobot](https://uptimerobot.com/) and register a free account.
3. Add a **New Monitor** using:
   * **Monitor Type**: `HTTP(s)`
   * **URL/IP**: *Your Render URL*
   * **Interval**: `Every 5 minutes`
4. Create the monitor. UptimeRobot will ping the bot's webserver, keeping it awake 24/7.
