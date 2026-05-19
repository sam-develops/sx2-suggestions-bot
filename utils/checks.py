# ============================================================
# utils/checks.py — Permission Checks
#
# These are reusable "decorators" — they go above commands
# to make sure only the right people can use them.
#
# Think of them like security guards for your commands.
# ============================================================

from discord.ext import commands
from config import STAFF_ROLE_ID


def _staff_role_id():
    """Normalize STAFF_ROLE_ID (avoid tuple bug from config trailing comma)."""
    raw = STAFF_ROLE_ID
    if isinstance(raw, (tuple, list)) and len(raw) == 1:
        raw = raw[0]
    return raw if isinstance(raw, int) and raw != 123456789012345678 else None


def is_staff():
    """
    A check that only allows users with the Staff role to use a command.

    How to use it on a command:
        @is_staff()
        @commands.command(name="example")
        async def example(self, ctx):
            ...
    """
    async def predicate(ctx):
        rid = _staff_role_id()
        if rid is None:
            return False
        staff_role = ctx.guild.get_role(rid)

        # If the role doesn't exist, deny access
        if staff_role is None:
            return False

        # Check if the user has the staff role
        return staff_role in ctx.author.roles

    return commands.check(predicate)


def is_admin():
    """
    A check that only allows server administrators to use a command.
    This is a shortcut for @commands.has_permissions(administrator=True).

    How to use it on a command:
        @is_admin()
        @commands.command(name="example")
        async def example(self, ctx):
            ...
    """
    return commands.has_permissions(administrator=True)
