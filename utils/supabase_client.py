# ============================================================
# utils/supabase_client.py — Supabase Database Connection Manager
#
# This handles connecting to Supabase asynchronously,
# querying/caching server settings, and log updates.
# ============================================================

import os
from supabase import create_async_client, AsyncClient

class SupabaseManager:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.client: AsyncClient = None
        # Cache for settings to avoid querying Supabase on every event
        # Format: { guild_id: { setting_name: value } }
        self.settings_cache = {}

    async def connect(self):
        """Connects to Supabase using the URL and Key from .env."""
        if not self.url or not self.key:
            print("⚠️ [Supabase] URL or Key is missing from the .env file. Database commands will not work.")
            return False
        try:
            self.client = await create_async_client(self.url, self.key)
            print("✅ [Supabase] Connection initialized successfully!")
            return True
        except Exception as e:
            print(f"❌ [Supabase] Failed to initialize connection: {e}")
            return False

    async def get_settings(self, guild_id: int) -> dict:
        """
        Gets settings for a specific Discord server.
        If it's already in our cache, we use the cached values.
        Otherwise, we query Supabase. If no settings exist yet, we create them.
        """
        if not self.client:
            return {}

        if guild_id in self.settings_cache:
            return self.settings_cache[guild_id]

        try:
            # Query the guild_settings table
            response = await self.client.table("guild_settings").select("*").eq("guild_id", guild_id).execute()
            
            if response.data and len(response.data) > 0:
                settings = response.data[0]
                self.settings_cache[guild_id] = settings
                return settings
            else:
                # No settings found in DB, insert a default row for this server
                default_settings = {
                    "guild_id": guild_id,
                    "prefix": "!",
                    "suggestion_channel_id": None,
                    "feedback_channel_id": None,
                    "ticket_category_id": None,
                    "ticket_new_category_id": None,
                    "ticket_working_category_id": None,
                    "resolved_tickets_channel_id": None,
                    "staff_role_id": None,
                    "ticket_admin_notify_role_id": None
                }
                await self.client.table("guild_settings").insert(default_settings).execute()
                self.settings_cache[guild_id] = default_settings
                print(f"ℹ️ [Supabase] Created default settings entry for guild {guild_id}")
                return default_settings

        except Exception as e:
            print(f"❌ [Supabase] Error fetching settings for guild {guild_id}: {e}")
            return {}

    async def update_setting(self, guild_id: int, key: str, value) -> bool:
        """
        Updates a setting for a specific server in the database and updates the cache.
        """
        if not self.client:
            return False

        # Make sure settings exist in cache/DB first
        await self.get_settings(guild_id)

        try:
            await self.client.table("guild_settings").update({key: value}).eq("guild_id", guild_id).execute()
            # Update cache
            if guild_id in self.settings_cache:
                self.settings_cache[guild_id][key] = value
            return True
        except Exception as e:
            print(f"❌ [Supabase] Error updating setting '{key}' to '{value}' for guild {guild_id}: {e}")
            return False

    async def get_setting_value(self, guild_id: int, key: str, fallback_value=None):
        """
        Helper function to get a single setting value, falling back to a default value if missing/None.
        """
        settings = await self.get_settings(guild_id)
        val = settings.get(key)
        return val if val is not None else fallback_value
