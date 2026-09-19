import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# USERS ALLOWED TO USE THE BOT
# ============================================================
#
# Put the Discord USER IDs of the people who are allowed
# to use the permission commands here.
#
# Example:
#
# ALLOWED_USERS = {
#     123456789012345678,
#     987654321098765432,
# }
#
# To get a User ID:
# Discord Settings -> Advanced -> Developer Mode ON
# Then right-click a user -> Copy User ID
#

ALLOWED_USERS = {
    123456789012345678,  # REPLACE THIS WITH YOUR USER ID
}


# ============================================================
# BOT SETUP
# ============================================================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# PERMISSIONS
# ============================================================

PERMISSIONS = {
    "administrator": ("Administrator", "administrator"),
    "manage_guild": ("Manage Server", "manage_guild"),
    "manage_channels": ("Manage Channels", "manage_channels"),
    "manage_roles": ("Manage Roles", "manage_roles"),
    "manage_messages": ("Manage Messages", "manage_messages"),
    "manage_threads": ("Manage Threads", "manage_threads"),
    "manage_webhooks": ("Manage Webhooks", "manage_webhooks"),
    "view_audit_log": ("View Audit Log", "view_audit_log"),
    "kick_members": ("Kick Members", "kick_members"),
    "ban_members": ("Ban Members", "ban_members"),
    "moderate_members": ("Timeout Members", "moderate_members"),
    "mention_everyone": ("Mention Everyone", "mention_everyone"),
    "view_channel": ("View Channel", "view_channel"),
    "send_messages": ("Send Messages", "send_messages"),
    "read_message_history": ("Read Message History", "read_message_history"),
    "embed_links": ("Embed Links", "embed_links"),
    "attach_files": ("Attach Files", "attach_files"),
    "add_reactions": ("Add Reactions", "add_reactions"),
    "connect": ("Connect", "connect"),
    "speak": ("Speak", "speak"),
    "stream": ("Video / Stream", "stream"),
    "mute_members": ("Mute Members", "mute_members"),
    "deafen_members": ("Deafen Members", "deafen_members"),
    "move_members": ("Move Members", "move_members"),
}


PERMISSION_CHOICES = [
    app_commands.Choice(
        name=display_name,
        value=permission_key
    )
    for permission_key, (display_name, _) in PERMISSIONS.items()
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_permission_attribute(permission_key: str) -> str:
    return PERMISSIONS[permission_key][1]


def get_permission_display_name(permission_key: str) -> str:
    return PERMISSIONS[permission_key][0]


def is_allowed_user():
    """
    First layer of protection:
    Only users whose Discord User ID is in ALLOWED_USERS
    can use the permission commands.
    """

    async def predicate(interaction: discord.Interaction):
        return interaction.user.id in ALLOWED_USERS

    return app_commands.check(predicate)


def check_role_edit(
    interaction: discord.Interaction,
    role: discord.Role,
    permission_key: str,
    granting: bool
):
    """
    Checks whether the bot is allowed to modify a role.
    """

    guild = interaction.guild

    if guild is None:
        return False, "This command can only be used inside a server."

    bot_member = guild.me

    if bot_member is None:
        return False, "I could not find my bot member in this server."

    # Bot needs Manage Roles
    if not bot_member.guild_permissions.manage_roles:
        return False, "I need the **Manage Roles** permission."

    # Bot cannot edit roles above or equal to its highest role
    if role >= bot_member.top_role:
        return (
            False,
            f"I cannot edit {role.mention} because that role is "
            f"higher than or equal to my highest role."
        )

    # When granting a permission, Discord requires the bot itself
    # to have that permission, unless the bot has Administrator.
    if granting:

        if bot_member.guild_permissions.administrator:
            return True, None

        permission_attribute = get_permission_attribute(permission_key)

        if not getattr(
            bot_member.guild_permissions,
            permission_attribute,
            False
        ):
            display_name = get_permission_display_name(permission_key)

            return (
                False,
                f"I don't have the **{display_name}** permission "
                f"myself, so Discord won't let me grant it."
            )

    return True, None


async def set_channel_permission(
    channel: discord.TextChannel,
    target: discord.Member | discord.Role,
    permission_key: str,
    value: bool,
    reason: str
):
    """
    Changes only the selected permission while preserving
    all other existing channel permission overwrites.
    """

    permission_attribute = get_permission_attribute(permission_key)

    # Get the existing overwrite
    overwrite = channel.overwrites_for(target)

    # Change only the requested permission
    setattr(overwrite, permission_attribute, value)

    # Save the complete overwrite back to Discord
    await channel.set_permissions(
        target,
        overwrite=overwrite,
        reason=reason
    )


# ============================================================
# CHANNEL PERMISSION GIVE
# ============================================================

@bot.tree.command(
    name="channelpermgive",
    description="Give a permission to a user or role in a channel."
)
@app_commands.guild_only()
@is_allowed_user()
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(
    channel="The channel to change.",
    target="The user or role to give the permission to.",
    permission="The permission to give."
)
@app_commands.choices(permission=PERMISSION_CHOICES)
async def channelpermgive(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    target: discord.Member | discord.Role,
    permission: app_commands.Choice[str]
):

    await interaction.response.defer(ephemeral=True)

    try:
        await set_channel_permission(
            channel=channel,
            target=target,
            permission_key=permission.value,
            value=True,
            reason=f"Permission granted by {interaction.user}"
        )

        display_name = get_permission_display_name(permission.value)

        await interaction.followup.send(
            f"✅ Gave **{display_name}** permission to "
            f"{target.mention} in {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Discord denied the request. "
            "Make sure my bot has **Manage Channels** and "
            "that my role is high enough.",
            ephemeral=True
        )

    except discord.NotFound:
        await interaction.followup.send(
            "❌ The channel or target could not be found.",
            ephemeral=True
        )

    except discord.HTTPException as error:
        await interaction.followup.send(
            f"❌ Discord returned an error: `{error}`",
            ephemeral=True
        )


# ============================================================
# CHANNEL PERMISSION DENY
# ============================================================

@bot.tree.command(
    name="channelpermdeny",
    description="Deny a permission to a user or role in a channel."
)
@app_commands.guild_only()
@is_allowed_user()
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(
    channel="The channel to change.",
    target="The user or role to deny the permission to.",
    permission="The permission to deny."
)
@app_commands.choices(permission=PERMISSION_CHOICES)
async def channelpermdeny(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    target: discord.Member | discord.Role,
    permission: app_commands.Choice[str]
):

    await interaction.response.defer(ephemeral=True)

    try:
        await set_channel_permission(
            channel=channel,
            target=target,
            permission_key=permission.value,
            value=False,
            reason=f"Permission denied by {interaction.user}"
        )

        display_name = get_permission_display_name(permission.value)

        await interaction.followup.send(
            f"🚫 Denied **{display_name}** permission to "
            f"{target.mention} in {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Discord denied the request. "
            "Make sure my bot has **Manage Channels** and "
            "that my role is high enough.",
            ephemeral=True
        )

    except discord.NotFound:
        await interaction.followup.send(
            "❌ The channel or target could not be found.",
            ephemeral=True
        )

    except discord.HTTPException as error:
        await interaction.followup.send(
            f"❌ Discord returned an error: `{error}`",
            ephemeral=True
        )


# ============================================================
# ROLE PERMISSION GIVE
# ============================================================

@bot.tree.command(
    name="rolepermgive",
    description="Give a server permission to a role."
)
@app_commands.guild_only()
@is_allowed_user()
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(
    role="The role to edit.",
    permission="The permission to give."
)
@app_commands.choices(permission=PERMISSION_CHOICES)
async def rolepermgive(
    interaction: discord.Interaction,
    role: discord.Role,
    permission: app_commands.Choice[str]
):

    await interaction.response.defer(ephemeral=True)

    allowed, error_message = check_role_edit(
        interaction,
        role,
        permission.value,
        granting=True
    )

    if not allowed:
        await interaction.followup.send(
            f"❌ {error_message}",
            ephemeral=True
        )
        return

    try:
        permission_attribute = get_permission_attribute(permission.value)

        # Get the existing role permissions
        permissions = role.permissions

        # Change only the selected permission
        setattr(
            permissions,
            permission_attribute,
            True
        )

        # Save the permissions
        await role.edit(
            permissions=permissions,
            reason=f"Permission granted by {interaction.user}"
        )

        display_name = get_permission_display_name(permission.value)

        await interaction.followup.send(
            f"✅ Gave **{display_name}** permission to {role.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Discord denied the request. "
            "Make sure my bot has **Manage Roles** and its role "
            "is above the role being edited.",
            ephemeral=True
        )

    except discord.NotFound:
        await interaction.followup.send(
            "❌ That role could not be found.",
            ephemeral=True
        )

    except discord.HTTPException as error:
        await interaction.followup.send(
            f"❌ Discord returned an error: `{error}`",
            ephemeral=True
        )


# ============================================================
# ROLE PERMISSION DENY
# ============================================================

@bot.tree.command(
    name="rolepermdeny",
    description="Remove a server permission from a role."
)
@app_commands.guild_only()
@is_allowed_user()
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(
    role="The role to edit.",
    permission="The permission to remove."
)
@app_commands.choices(permission=PERMISSION_CHOICES)
async def rolepermdeny(
    interaction: discord.Interaction,
    role: discord.Role,
    permission: app_commands.Choice[str]
):

    await interaction.response.defer(ephemeral=True)

    allowed, error_message = check_role_edit(
        interaction,
        role,
        permission.value,
        granting=False
    )

    if not allowed:
        await interaction.followup.send(
            f"❌ {error_message}",
            ephemeral=True
        )
        return

    try:
        permission_attribute = get_permission_attribute(permission.value)

        # Get existing role permissions
        permissions = role.permissions

        # Remove only the selected permission
        setattr(
            permissions,
            permission_attribute,
            False
        )

        # Save the permissions
        await role.edit(
            permissions=permissions,
            reason=f"Permission denied by {interaction.user}"
        )

        display_name = get_permission_display_name(permission.value)

        await interaction.followup.send(
            f"🚫 Removed **{display_name}** permission from "
            f"{role.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Discord denied the request. "
            "Make sure my bot has **Manage Roles** and its role "
            "is above the role being edited.",
            ephemeral=True
        )

    except discord.NotFound:
        await interaction.followup.send(
            "❌ That role could not be found.",
            ephemeral=True
        )

    except discord.HTTPException as error:
        await interaction.followup.send(
            f"❌ Discord returned an error: `{error}`",
            ephemeral=True
        )


# ============================================================
# ROLE PERMISSION RESET
# ============================================================

@bot.tree.command(
    name="rolepermreset",
    description="Reset a role permission to denied."
)
@app_commands.guild_only()
@is_allowed_user()
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(
    role="The role to edit.",
    permission="The permission to reset."
)
@app_commands.choices(permission=PERMISSION_CHOICES)
async def rolepermreset(
    interaction: discord.Interaction,
    role: discord.Role,
    permission: app_commands.Choice[str]
):

    await interaction.response.defer(ephemeral=True)

    allowed, error_message = check_role_edit(
        interaction,
        role,
        permission.value,
        granting=False
    )

    if not allowed:
        await interaction.followup.send(
            f"❌ {error_message}",
            ephemeral=True
        )
        return

    try:
        permission_attribute = get_permission_attribute(permission.value)

        # Server-level role permissions only have enabled/disabled.
        # Therefore reset sets the permission to False.
        permissions = role.permissions

        setattr(
            permissions,
            permission_attribute,
            False
        )

        await role.edit(
            permissions=permissions,
            reason=f"Permission reset by {interaction.user}"
        )

        display_name = get_permission_display_name(permission.value)

        await interaction.followup.send(
            f"🔄 Reset **{display_name}** permission for "
            f"{role.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Discord denied the request. "
            "Make sure my bot has **Manage Roles** and its role "
            "is above the role being edited.",
            ephemeral=True
        )

    except discord.NotFound:
        await interaction.followup.send(
            "❌ That role could not be found.",
            ephemeral=True
        )

    except discord.HTTPException as error:
        await interaction.followup.send(
            f"❌ Discord returned an error: `{error}`",
            ephemeral=True
        )


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    print(f"Logged in as: {bot.user}")
    print(f"Bot ID: {bot.user.id}")

    try:
        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} slash command(s)."
        )

    except Exception as error:

        print(
            f"Failed to sync slash commands: {error}"
        )


# ============================================================
# SLASH COMMAND ERROR HANDLER
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    if isinstance(
        error,
        app_commands.errors.MissingPermissions
    ):

        message = (
            "❌ You need the **Manage Roles** permission "
            "to use this command."
        )

    elif isinstance(
        error,
        app_commands.errors.CheckFailure
    ):

        if interaction.user.id not in ALLOWED_USERS:

            message = (
                "❌ You are not authorized to use "
                "this bot."
            )

        else:

            message = (
                "❌ You need the **Manage Roles** permission "
                "to use this command."
            )

    elif isinstance(
        error,
        app_commands.errors.TransformerError
    ):

        message = (
            "❌ I couldn't understand one of "
            "the command arguments."
        )

    else:

        print(
            f"Slash command error: {error}"
        )

        message = (
            f"❌ An error occurred: `{error}`"
        )

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                message,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    except Exception:
        pass


# ============================================================
# BOT TOKEN
# ============================================================

TOKEN = "PUT_YOUR_NEW_BOT_TOKEN_HERE"


if TOKEN == "PUT_YOUR_NEW_BOT_TOKEN_HERE":

    print(
        "ERROR: Put your new bot token in the TOKEN variable."
    )

else:

    bot.run(TOKEN)
