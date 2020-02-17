import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import os

import pymongo
from pymongo import MongoClient

prefix = "."
client = commands.Bot(command_prefix=prefix)
client.remove_command("help")

token = str(os.environ.get("guild_manager_token"))
app_string = str(os.environ.get("cluster_app_string"))
default_avatar_url = "https://cdn.discordapp.com/attachments/664230839399481364/677534213418778660/default_image.png"

cluster = MongoClient(app_string)
db = cluster["guild_data"]

#========Lists=========
param_desc = {
    "name": {
        "usage": f'`{prefix}edit-guild name "Старое название" Новое название`',
        "example": f'`{prefix}edit-guild name "Моя гильдия" Лучшая гильдия`'
    },
    "description": {
        "usage": f'`{prefix}edit-guild description "Гильдия" Новое описание`',
        "example": f'`{prefix}edit-guild description "Моя гильдия" Для тех, кто любит общаться`'
    },
    "avatar": {
        "usage": f'`{prefix}edit-guild avatar "Гильдия" Ссылка`',
        "example": f'`{prefix}edit-guild avatar "Моя гильдия" {default_avatar_url}`'
    },
    "leader": {
        "usage": f'`{prefix}edit-guild leader "Гильдия" @Пользователь`',
        "example": f'`{prefix}edit-guild leader "Моя гильдия" @Пользователь`'
    },
    "role": {
        "usage": f'`{prefix}edit-guild role "Гильдия" @Роль (или delete)`',
        "example": f'`{prefix}edit-guild role "Моя гильдия" delete`'
    },
    "privacy": {
        "usage": f'`{prefix}edit-guild privacy "Гильдия" on / off`',
        "example": f'`{prefix}edit-guild privacy "Моя гильдия" on`'
    }
}

owner_ids = [301295716066787332]

def c_split(text, lll=" "):
    out=[]
    wid=len(lll)
    text_l=len(text)
    start=0
    end=-1
    for i in range(text_l-wid+1):
        if text[i:i+wid]==lll:
            end=i
            if start<end:
                out.append(text[start:end])
            start=i+wid
    if end!=text_l-wid:
        out.append(text[start:text_l])
    return out

def carve_int(string):
    nums = [str(i) for i in range(10)]
    out = ""
    found = False
    for letter in string:
        if letter in nums:
            found = True
            out += letter
        elif found:
            break
    if out == "":
        out = None
    else:
        out = int(out)
    return out

def get_subguild(collection_part, subguild_name):
    out = None
    subguilds = collection_part["subguilds"]
    for subguild in subguilds:
        if subguild["name"] == subguild_name:
            out = subguild
            break
    return out

def perms_for(role):
    owned = {
    "create_instant_invite": role.permissions.create_instant_invite,
    "kick_members": role.permissions.kick_members,
    "ban_members": role.permissions.ban_members,
    "administrator": role.permissions.administrator,
    "manage_channels": role.permissions.manage_channels,
    "manage_roles": role.permissions.manage_roles,
    "manage_guild": role.permissions.manage_guild,
    "view_audit_log": role.permissions.view_audit_log,
    "change_nickname": role.permissions.change_nickname,
    "manage_nicknames": role.permissions.manage_nicknames,
    "manage_webhooks": role.permissions.manage_webhooks,
    "manage_messages": role.permissions.manage_messages,
    "manage_emojis": role.permissions.manage_emojis,
    "mention_everyone": role.permissions.mention_everyone
    }
    return owned

def has_permissions(member, perm_array):
    to_have = len(perm_array)
    if member.id == member.guild.owner_id:
        return True
    else:
        found_num = 0
        found = []
        for role in member.roles:
            owned = perms_for(role)
            if owned["administrator"]:
                found_num = to_have
            else:
                for perm in perm_array:
                    if not perm in found and owned[perm]:
                        found.append(perm)
                        found_num += 1
            if found_num >= to_have:
                break
                    
        return True if found_num >= to_have else False

def has_any_permission(member, perm_array):
    if member.id == member.guild.owner_id:
        return True
    else:
        has = False
        for perm in perm_array:
            for role in member.roles:
                role_perms = perms_for(role)
                if role_perms["administrator"] or role_perms[perm]:
                    has = True
                    break
            if has:
                break
        return has

def has_roles(member, role_array):
    has_them = True
    if not has_permissions(member, ["administrator"]):
        for role in role_array:
            if not role in member.roles:
                has_them = False
                break
    return has_them

def image_link(string):
    return string.startswith("https://")

def f_username(user):
    line = f"{user}"
    fsymbs = ">`*_~|"
    out = ""
    for s in line:
        if s in fsymbs:
            out += f"\\{s}"
        else:
            out += s
    return out

def get_member(guild, ID):
    return discord.utils.get(guild.members, id=ID)

async def read_message(channel, user, t_out):
    try:
        msg = await client.wait_for("message", check=lambda message: user.id==message.author.id and channel.id==message.channel.id, timeout=t_out)
    except asyncio.TimeoutError:
        reply=discord.Embed(
            title="🕑 Вы слишком долго не писали",
            description=f"Таймаут: {t_out}",
            color=discord.Color.blurple()
        )
        await channel.send(content=user.mention, embed=reply)
        return "Timeout"
    else:
        return msg

async def give_join_role(member, role_id):
    if role_id != None:
        role = discord.utils.get(member.guild.roles, id = role_id)
        if role != None and role not in member.roles:
            try:
                await member.add_roles(role)
            except Exception:
                pass
    return

async def remove_join_role(member, role_id):
    if role_id != None:
        role = discord.utils.get(member.guild.roles, id = role_id)
        if role != None and role in member.roles:
            try:
                await member.remove_roles(role)
            except Exception:
                pass
    return

async def knock_dm(user, extra_channel, log_emb):
    try:
        await user.send(embed = log_emb)
    except Exception:
        await extra_channel.send(content = f"{user.mention}, не могу отправить лично Вам", embed = log_emb)

class detect:
    @staticmethod
    def member(guild, search):
        ID = carve_int(search)
        if ID == None:
            ID = 0
        member = discord.utils.get(guild.members, id=ID)
        return member
    
    @staticmethod
    def channel(guild, search):
        ID = carve_int(search)
        if ID == None:
            ID = 0
        channel = discord.utils.get(guild.channels, id=ID)
        return channel
    
    @staticmethod
    def role(guild, search):
        ID = carve_int(search)
        if ID == None:
            ID = 0
        role = discord.utils.get(guild.roles, id=ID)
        return role

@client.event
async def on_ready():
    print(
        ">> Bot is ready\n"
        f">> Prefix is {prefix}\n"
        f">> Bot user: {client.user}"
    )

@client.event
async def on_member_remove(member):
    collection = db["subguilds"]
    collection.find_one_and_update(
        {"_id": member.guild.id, "subguilds.leader_id": member.id},
        {"$pull": {"subguilds": {"leader_id": member.id}}}
    )
    collection.find_one_and_update(
        {"_id": member.guild.id, f"subguilds.members.{member.id}.id": member.id},
        {
            "$unset": {f"subguilds.$.members.{member.id}": ""},
            "$pull": {f"subguilds.$.requests": member.id}
        }
    )

#=========Commands==========
@client.command()
async def logout(ctx):
    if ctx.author.id in owner_ids:
        await ctx.send("Logging out...")
        await client.logout()

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command()
async def help(ctx):
    p = prefix
    user_cmd_desc = (
        f"**{p}join-guild [**Гильдия**]** - *зайти в гильдию*\n"
        f"**{p}leave-guild** - *выйти из текущей гильдии*\n"
        f"**{p}guilds** - *топ гильдий сервера*\n"
        f"**{p}guild-info [**Гильдия**]** - *посмотреть подробности гильдии*\n"
        f"**{p}guild-top [**Страница топа**] [**Гильдия**]** - *топ участников гильдии*\n"
        f"**{p}user-guild @Пользователь** (не обязательно) - *посмотреть свою / чужую гильдию*\n"
    )
    owners_cmd_desc = (
        f"**{p}create-guild [**Название**]** - *создаёт гильдию*\n"
        f'**{p}edit-guild [**Параметр**] "**Гильдия**" [**Новое значение**]** - *подробнее: {p}edit-guild*\n'
        f"**{p}delete-guild [**Гильдия**]** - *удаляет гильдию*\n"
        f"**{p}requests Страница Гильдия** - *список заявок на вступление в гильдию*\n"
        f"**{p}accept Номер_заяки Гильдия** - *принять заявку*\n"
        f"**{p}decline Номер_заяки Гильдия** - *отклонить заявку*\n"
        f"‣—‣ {p}accept/decline all Гильдия - *принять/отклонить все заявки*\n"
    )
    adm_cmd_desc = (
        f"**{p}settings** - *текущие настройки*\n"
        f"**{p}cmd-channels #канал-1 #канал-2 ...** - *настроить каналы реагирования*\n"
        f"‣—‣ {p}cmd-channels delete - *сбросить*\n"
        f"**{p}reset-guilds messages | mentions** - *обнуляет либо упоминания, либо сообщения всех гильдий сервера*\n"
        f"**{p}ping-count [**Пользователь**]** - *настраивает пользователя, пинги которого будут подсчитываться*\n"
        f'**{p}count-roles "**Название гильдии**" @Роль1 @Роль2 ...** - *подсчёт членов гильдии с каждой ролью*\n'
    )
    help_emb = discord.Embed(
        title = f"📰 Список команд",
        color = discord.Color.from_rgb(150, 150, 150)
    )
    
    help_emb.add_field(name = "**Всем пользователям**", value = user_cmd_desc, inline=False)
    help_emb.add_field(name = "**Главам гильдий**", value = owners_cmd_desc, inline=False)
    if has_permissions(ctx.author, ["administrator"]):
        help_emb.add_field(name = "**Администраторам**", value = adm_cmd_desc, inline=False)
    await ctx.send(embed = help_emb)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command()
async def settings(ctx):
    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "💢 Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        collection = db["cmd_channels"]
        result = collection.find_one({"_id": ctx.guild.id})
        wl_channels = None
        if result != None:
            wl_channels = result["channels"]
        
        if wl_channels == None:
            chan_desc = "> Все каналы"
        else:
            chan_desc = ""
            for ID in wl_channels:
                chan_desc += f"> {client.get_channel(ID).mention}\n"
        
        collection = db["subguilds"]
        result = collection.find_one(
            {"_id": ctx.guild.id, "mentioner_id": {"$exists": True}},
            projection={"mentioner_id": True}
        )
        pinger_id = None
        if result != None:
            pinger_id = result["mentioner_id"]
        
        if pinger_id == None:
            ping_desc = "выключено"
        else:
            ping_desc = f"{client.get_user(pinger_id)}"
        
        reply = discord.Embed(
            title = "⚙ Текущие настройки сервера",
            description = (
                f"**Каналы для команд бота:**\n"
                f"{chan_desc}\n"
                f"**Вести подсчёт упоминаний от:**\n"
                f"{ping_desc}\n\n"
                f"-> Настроить каналы для команд: `{prefix}cmd-channels #канал-1 #канал-2 ...`\n"
                f"---> Сбросить: `{prefix}cmd-channels delete`\n"
                f"-> Настроить подсчёт упоминаний: `{prefix}ping-count @Участник`\n"
                f"---> Сбросить: `{prefix}ping-count delete`\n"
                f"-> Посмотреть топ гильдий: `{prefix}top`\n"
            ),
            color = discord.Color.blurple()
        )
        reply.set_thumbnail(url = f"{ctx.guild.icon_url}")
        await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["cmd-channels", "cmdchannels", "cc"])
async def cmd_channels(ctx, *raw_ch):
    collection = db["cmd_channels"]

    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "💢 Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    elif "delete" in raw_ch[0].lower():
        collection.find_one_and_update(
            {"_id": ctx.guild.id},
            {
                "$set": {"channels": None}
            }
        )
        reply = discord.Embed(
            title = "♻ Каналы сброшены",
            description = "Теперь я реагирую на команды во всех каналах",
            color = discord.Color.dark_green()
        )
        await ctx.send(embed = reply)

    else:
        channels = [detect.channel(ctx.guild, s) for s in raw_ch]
        if None in channels:
            reply = discord.Embed(
                title = f"💢 Ошибка",
                description = (
                    f"В качестве каналов укажите их **#ссылки** или **ID**"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            channel_ids = [c.id for c in channels]

            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {
                    "$set": {"channels": channel_ids}
                },
                upsert=True
            )
            desc = ""
            for channel in channels:
                desc += f"> {channel.mention}\n"
            reply = discord.Embed(
                title = "🛠 Каналы настроены",
                description = (
                    f"Теперь бот реагирует на команды только в каналах:\n"
                    f"{desc}"
                ),
                color = discord.Color.blurple()
            )
            await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["create-guild", "createguild", "cg"])
async def create_guild(ctx, *, guild_name):
    collection = db["subguilds"]

    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "💢 Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        result = collection.find_one({"_id": ctx.guild.id, "subguilds.name": guild_name}, projection={"_id": True})
        if result != None:
            reply = discord.Embed(
                title = "⚠ Ошибка",
                description = f"Гильдия с названием **{guild_name}** уже есть на этом сервере",
                color = discord.Color.dark_gold()
            )
            await ctx.send(embed = reply)
        
        else:
            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {
                    "$addToSet": {
                        "subguilds": {
                            "name": guild_name,
                            "description": "Без описания",
                            "avatar_url": default_avatar_url,
                            "leader_id": ctx.author.id,
                            "role_id": None,
                            "private": False,
                            "requests": [],
                            "mentions": 0,
                            "members": {}
                        }
                    }
                },
                upsert=True
            )

            reply = discord.Embed(
                title = f"✅ Гильдия **{guild_name}** создана",
                description = (
                    f"Отредактировать гильдию: `{prefix}edit-guild`\n"
                    f"Профиль гильдии: `{prefix}guild-info {guild_name}`\n"
                    f"Зайти в гильдию `{prefix}join-guild {guild_name}`"
                ),
                color = discord.Color.green()
            )
            reply.set_thumbnail(url = default_avatar_url)
            await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["edit-guild", "editguild", "eg"])
async def edit_guild(ctx, parameter, *, text_data = None):
    collection = db["subguilds"]
    parameter = parameter.lower()
    parameters = {
        "name": "name",
        "description": "description",
        "avatar": "avatar_url",
        "leader": "leader_id",
        "role": "role_id",
        "privacy": "private"
    }
    guild_name = ""

    if parameter not in parameters:
        reply = discord.Embed(
            title = "📑 Доступные параметры настроек",
            description = (
                "> `name`\n"
                "> `description`\n"
                "> `avatar`\n"
                "> `leader`\n"
                "> `role`\n"
                "> `privacy`\n"
                f'**Использование:** `{prefix}{ctx.command.name} Параметр "Название гильдии" [Новое значение]`\n'
                f'**Пример:** `{prefix}{ctx.command.name} name "Моя гильдия" Хранители`\n'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        if text_data == None:
            reply = discord.Embed(
                title = f"🛠 Использование {prefix}edit-guild {parameter}",
                description = (
                    f"**Использование:** {param_desc[parameter]['usage']}\n"
                    f"**Пример:** {param_desc[parameter]['example']}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif not text_data.startswith('"'):
            i = 0
            while i < len(text_data) and text_data[i] != " ":
                guild_name += text_data[i]
                i += 1
        else:
            i = 1
            while i < len(text_data) and text_data[i] != '"':
                guild_name += text_data[i]
                i += 1
        text = text_data[+i+1:].lstrip()

        result = collection.find_one(
            filter={"_id": ctx.guild.id, "subguilds.name": guild_name},
            projection={"subguilds.members": False}
        )
        if result == None:
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"Гильдии с названием **{guild_name}** нет на сервере",
                color = discord.Color.from_rgb(40, 40, 40)
            )
            await ctx.send(embed = reply)
        
        else:
            subguild = get_subguild(result, guild_name)
            leader_id = subguild["leader_id"]

            if ctx.author.id != leader_id and not has_permissions(ctx.author, ["administrator"]):
                reply = discord.Embed(
                    title = "❌ Недостаточно прав",
                    description = f"Вы не являетесь главой гильдии **{guild_name}** или администратором.",
                    color = discord.Color.dark_red()
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                correct_arg = True
                value = text
                if parameter == "leader":
                    value = detect.member(ctx.guild, text)
                    if value == None:
                        correct_arg = False

                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Вы ввели {text}, подразумевая участника, но он не был найден",
                            color = discord.Color.from_rgb(40, 40, 40)
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)
                    else:
                        value = value.id
                elif parameter == "role":
                    value = detect.role(ctx.guild, text)
                    if text.lower() == "delete":
                        value = None
                    elif value == None:
                        correct_arg = False

                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Вы ввели {text}, подразумевая роль, но она не была найдена",
                            color = discord.Color.from_rgb(40, 40, 40)
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)
                    else:
                        value = value.id
                elif parameter == "avatar":
                    correct_arg = image_link(text)
                    if not correct_arg:
                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Не удаётся найти картинку по ссылке {text}",
                            color = discord.Color.from_rgb(40, 40, 40)
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                elif parameter == "privacy":
                    on = ["on", "вкл", "1"]
                    off = ["off", "выкл", "0"]
                    if text.lower() in on:
                        value = True
                    elif text.lower() in off:
                        value = False
                    else:
                        correct_arg = False

                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Входной аргумент {text} должен быть `on` или `off`",
                            color = discord.Color.from_rgb(40, 40, 40)
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)
                
                if correct_arg:
                    subguild[parameters[parameter]] = value

                    collection.find_one_and_update(
                        {"_id": ctx.guild.id, "subguilds.name": guild_name},
                        {"$set": {f"subguilds.$.{parameters[parameter]}": value}},
                        upsert=True
                    )

                    reply = discord.Embed(
                        title = "✅ Настроено",
                        description = f"**->** Профиль гильдии: `{prefix}guild-info {subguild['name']}`",
                        color = discord.Color.green()
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

@commands.cooldown(1, 30, commands.BucketType.member)
@client.command(aliases = ["delete-guild", "deleteguild", "dg"])
async def delete_guild(ctx, *, guild_name):
    collection = db["subguilds"]
    result = collection.find_one(
        {"_id": ctx.guild.id, "subguilds.name": guild_name},
        projection={"subguilds.name": True, "subguilds.leader_id": True}
    )
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{prefix}guilds`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        await ctx.send(embed = reply)
    else:
        subguild = get_subguild(result, guild_name)
        del result

        if ctx.author.id != subguild["leader_id"] and not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = f"Вы не являетесь главой гильдии **{guild_name}** или администратором",
                color = discord.Color.dark_red()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            collection.find_one_and_update(
                {"_id": ctx.guild.id, "subguilds.name": guild_name},
                {
                    "$pull": {
                        "subguilds": {"name": guild_name}
                    }
                }
            )
            
            reply = discord.Embed(
                title = "🗑 Удаление завершено",
                description = f"Вы удалили гильдию **{guild_name}**",
                color = discord.Color.from_rgb(40, 40, 40)
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["req"])
async def requests(ctx, page, *, guild_name):
    collection = db["subguilds"]
    interval = 20

    result = collection.find_one(
        {"_id": ctx.guild.id, "subguilds.name": guild_name},
        projection={
            "subguilds.leader_id": True,
            "subguilds.requests": True,
            "subguilds.name": True,
            "subguilds.private": True
        }
    )
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"На сервере нет гильдии с названием **{guild_name}**"
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        subguild = get_subguild(result, guild_name)
        del result

        if ctx.author.id != subguild["leader_id"] and not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = (
                    "Вы не являетесь администратором сервера или владельцем этой гильдии"
                ),
                color = discord.Color.dark_red()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif not subguild["private"]:
            reply = discord.Embed(
                title = "🛠 Гильдия не приватна",
                description = f"Это гильдия с открытым доступом"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif carve_int(page) == None:
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"{page} должно быть целым числом"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            page = carve_int(page)

            bad_ids = []
            req_list = []
            for ID in subguild["requests"]:
                member = get_member(ctx.guild, ID)
                if member == None:
                    bad_ids.append(ID)
                else:
                    req_list.append(member)

            length = len(req_list)

            first_num = (page - 1) * interval
            total_pages = (length - 1) // interval + 1
            if first_num >= length:
                reply = discord.Embed(
                    title = "🔎 Страница не найдена",
                    description = f"**Всего страниц:** {total_pages}"
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                desc = ""
                last_num = min(first_num + interval, length)
                for i in range(first_num, last_num):
                    if req_list != None:
                        desc += f"**{i + 1})** {f_username(req_list[i])}\n"
                reply = discord.Embed(
                    title = "Запросы на вступление",
                    description = (
                        f"**В гильдию:** {guild_name}\n"
                        f"**Сервер:** {ctx.guild.name}\n"
                        f"**Принять запрос:** `{prefix}accept Номер_запроса {guild_name}`\n"
                        f"**Отклонить запрос:** `{prefix}decline Номер_запроса {guild_name}`\n\n"
                        f"{desc}"
                    ),
                    color = discord.Color.blurple()
                )
                reply.set_footer(text = f"Стр. {page}/{total_pages}")
                await ctx.send(embed = reply)
            
            #======Remove invalid members======
            if bad_ids != []:
                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {"$pull": {"subguilds.$.requests": {"$in": bad_ids}}}
                )

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["ac"])
async def accept(ctx, num, *, guild_name):
    collection = db["subguilds"]

    result = collection.find_one(
        {"_id": ctx.guild.id, "subguilds.name": guild_name},
        projection={
            "subguilds.leader_id": True,
            "subguilds.requests": True,
            "subguilds.name": True,
            "subguilds.private": True
        }
    )
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"На сервере нет гильдии с названием **{guild_name}**"
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        subguild = get_subguild(result, guild_name)
        del result

        id_list = []
        to_pull = []
        for ID in subguild["requests"]:
            member = get_member(ctx.guild, ID)
            if member == None:
                to_pull.append(ID)
            else:
                id_list.append(ID)
        length = len(id_list)

        if ctx.author.id != subguild["leader_id"] and not has_permissions(ctx.author, ["administrator"]):
            correct_args = False

            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = (
                    "Вы не являетесь администратором сервера или владельцем этой гильдии"
                ),
                color = discord.Color.dark_red()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif not subguild["private"]:
            correct_args = False

            reply = discord.Embed(
                title = "🛠 Гильдия не приватна",
                description = f"Это гильдия с открытым доступом"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif num.lower() == "all":
            correct_args = True
            num = "all"
        
        elif carve_int(num) == None:
            correct_args = False
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"{num} должно быть целым числом"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif carve_int(num) > length:
            correct_args = False
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"{num} превышает число запросов"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            correct_args = True
            num = carve_int(num)
        
        if correct_args:

            if num == "all":
                new_data = {}
                new_data.update([(f"subguilds.$.members.{ID}", {"id": ID, "messages": 0}) for ID in id_list])

                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {
                        "$pull": {"subguilds.$.requests": {"$in": subguild["requests"]}},
                        "$set": new_data
                    }
                )
                desc = "Все заявки приняты"
            else:
                user_id = id_list[num-1]
                to_pull.append(user_id)

                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {
                        "$pull": {"subguilds.$.requests": {"$in": to_pull}},
                        "$set": {f"subguilds.$.members.{user_id}": {"id": user_id, "messages": 0}}
                    }
                )
                member = get_member(ctx.guild, user_id)
                desc = f"Заявка {f_username(member)} принята"
            
            reply = discord.Embed(
                title = "🛠 Выполнено",
                description = desc
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["dec"])
async def decline(ctx, num, *, guild_name):
    collection = db["subguilds"]

    result = collection.find_one(
        {"_id": ctx.guild.id, "subguilds.name": guild_name},
        projection={
            "subguilds.leader_id": True,
            "subguilds.requests": True,
            "subguilds.name": True,
            "subguilds.private": True
        }
    )
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"На сервере нет гильдии с названием **{guild_name}**"
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        subguild = get_subguild(result, guild_name)
        del result

        id_list = []
        to_pull = []
        for ID in subguild["requests"]:
            member = get_member(ctx.guild, ID)
            if member == None:
                to_pull.append(ID)
            else:
                id_list.append(ID)
        length = len(id_list)

        if ctx.author.id != subguild["leader_id"] and not has_permissions(ctx.author, ["administrator"]):
            correct_args = False

            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = (
                    "Вы не являетесь администратором сервера или владельцем этой гильдии"
                ),
                color = discord.Color.dark_red()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif not subguild["private"]:
            correct_args = False

            reply = discord.Embed(
                title = "🛠 Гильдия не приватна",
                description = f"Это гильдия с открытым доступом"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif num.lower() == "all":
            correct_args = True
            num = "all"
        
        elif carve_int(num) == None:
            correct_args = False
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"{num} должно быть целым числом"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif carve_int(num) > length:
            correct_args = False
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"{num} превышает число запросов"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            correct_args = True
            num = carve_int(num)
        
        if correct_args:
            if num == "all":
                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {"$pull": {"subguilds.$.requests": {"$in": subguild["requests"]}}}
                )
                desc = f"Все заявки отклонены"
            else:
                user_id = id_list[num-1]
                to_pull.append(user_id)

                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {
                        "$pull": {"subguilds.$.requests": {"$in": to_pull}}
                    }
                )
                member = get_member(ctx.guild, user_id)
                desc = f"Заявка {f_username(member)} отклонена"
            
            reply = discord.Embed(
                title = "🛠 Выполнено",
                description = desc
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["ping-count", "pingcount", "pc"])
async def ping_count(ctx, u_search):
    collection = db["subguilds"]
    user = detect.member(ctx.guild, u_search)

    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "❌ Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
    
    elif u_search.lower() == "delete":
        collection.find_one_and_update(
            {"_id": ctx.guild.id},
            {
                "$set": {
                    "mentioner_id": None
                }
            }
        )
        reply = discord.Embed(
            title = "✅ Настроено",
            description = "Больше не ведётся подсчёт упоминаний",
            color = discord.Color.green()
        )

    elif user == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"Вы ввели {u_search}, подразумевая участника, но он не был найден",
            color = discord.Color.darker_grey()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")

    else:
        collection.find_one_and_update(
            {"_id": ctx.guild.id},
            {
                "$set": {
                    "mentioner_id": user.id
                }
            },
            upsert=True
        )
        reply = discord.Embed(
            title = "✅ Настроено",
            description = f"Теперь в гильдиях ведётся подсчёт пингов от **{user}**",
            color = discord.Color.green()
        )
    await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["reset-guilds", "resetguilds", "rg"])
async def reset_guilds(ctx, parameter):
    collection = db["subguilds"]
    params = ["messages", "mentions"]
    parameter = parameter.lower()

    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "❌ Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
    
    elif parameter not in params:
        reply = discord.Embed(
            title = "💢 Неверный параметр",
            description = (
                "Доступные параметры:\n"
                "> `messages`\n"
                "> `mentions`\n"
                f"Например `{prefix}reset-guilds messages`"
            ),
            color = discord.Color.dark_grey()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")

    elif parameter == "mentions":
        collection.find_one_and_update(
            {"_id": ctx.guild.id},
            {
                "$set": {"subguilds.$[].mentions": 0}
            }
        )
        reply = discord.Embed(
            title = "♻ Завершено",
            description = "Сброс упоминаний закончен",
            color = discord.Color.green()
        )
    elif parameter == "messages":
        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection = {"subguilds.members": True}
        )
        if result != None:
            new_data = {}
            for sg in result["subguilds"]:
                new_data.update([(f"subguilds.$[].members.{m}.messages", 0) for m in sg["members"]])
            del result

            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {
                    "$set": new_data
                }
            )
        reply = discord.Embed(
            title = "♻ Завершено",
            description = "Сброс сообщений закончен",
            color = discord.Color.green()
        )
    
    await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["count-roles", "countroles", "cr"])
async def count_roles(ctx, *, text):
    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "❌ Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        if text[0] != '"':
            raw_roles = c_split(text)
            guild_name = raw_roles[0]
            raw_roles = raw_roles[1:len(raw_roles)]
        else:
            guild_name = ""
            i = 1
            while i < len(text) and text[i] != '"':
                guild_name += text[i]
                i += 1
            text = text[+i+1:]
            raw_roles = c_split(text)

        roles = [detect.role(ctx.guild, s) for s in raw_roles]
        if None in roles:
            reply = discord.Embed(
                title = f"💢 Ошибка",
                description = (
                    f"В качестве ролей укажите их **@Упоминания** или **ID**"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            collection = db["subguilds"]

            result = collection.find_one(
                {"_id": ctx.guild.id, "subguilds.name": guild_name},
                projection={"subguilds.name": True, "subguilds.members": True}
            )
            if result == None:
                reply = discord.Embed(
                    title = "💢 Упс",
                    description = f"На сервере нет гильдии с названием **{guild_name}**",
                    color = discord.Color.dark_grey()
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                subguild = get_subguild(result, guild_name)
                del result

                pairs = [[r, 0] for r in roles]
                for key in subguild["members"]:
                    memb = subguild["members"][key]
                    member = discord.utils.get(ctx.guild.members, id = memb["id"])
                    if member != None:
                        for i in range(len(pairs)):
                            role = pairs[i][0]
                            if role in member.roles:
                                pairs[i][1] += 1
                del subguild

                pairs.sort(key=lambda i: i[1])
                desc = ""
                for pair in pairs:
                    desc += f"<@&{pair[0].id}> • {pair[1]} 👥\n"

                reply = discord.Embed(
                    title = guild_name,
                    description = (
                        f"**Статистика ролей:**\n"
                        f"{desc}"
                    ),
                    color = discord.Color.gold()
                )
                await ctx.send(embed = reply)

@commands.cooldown(1, 30, commands.BucketType.member)
@client.command(aliases = ["join-guild", "joinguild", "jg"])
async def join_guild(ctx, *, guild_name):
    collection = db["subguilds"]

    result = collection.find_one(
        {
            "_id": ctx.guild.id,
            "subguilds.name": guild_name
        },
        projection={
            "subguilds.requests": False
        }
    )
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{prefix}guilds`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        await ctx.send(embed = reply)
    else:
        subguild = get_subguild(result, guild_name)
        guild_role_id = subguild["role_id"]
        private = subguild["private"]
        leader = client.get_user(subguild["leader_id"])
        del subguild

        result = result["subguilds"]
        user_guild = None
        for subguild in result:
            if f"{ctx.author.id}" in subguild["members"]:
                user_guild = subguild["name"]
                break
        del result

        if guild_name == user_guild:
            reply = discord.Embed(
                title = "❌ Ошибка",
                description = f"Вы уже являетесь членом гильдии **{guild_name}**",
                color = discord.Color.dark_red()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif user_guild != None:
            reply = discord.Embed(
                title = "🛠 О смене гильдий",
                description = (
                    f"В данный момент Вы являетесь членом гильдии **{user_guild}**.\n"
                    f"Для того, чтобы войти в другую гильдию, Вам нужно выйти из текущей, однако, **не забывайте**:\n"
                    f"**->** Счётчик сообщений участника обнуляется при выходе.\n"
                    f"Команда для выхода: `{prefix}leave-guild`"
                ),
                color = discord.Color.from_rgb(40, 40, 40)
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            if private and ctx.author.id != leader.id:
                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {"$addToSet": {"subguilds.$.requests": ctx.author.id}},
                    upsert=True
                )
                reply = discord.Embed(
                    title = "⏳ Ваш запрос отправлен главе",
                    description = (
                        f"Это закрытая гильдия. Вы станете её участником, как только её глава примет вашу заявку"
                    ),
                    color = discord.Color.dark_gold()
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

                log = discord.Embed(
                    description = (
                        "Запрос на вступление\n"
                        f"**В гильдию:** {guild_name}\n"
                        f"**С сервера:** {ctx.guild.name}\n"
                        f"**Все запросы:** `{prefix}requests Страница {guild_name}`\n"
                        f"**Важно:** используйте команды на соответствующем сервере"
                    )
                )
                log.set_author(name = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await knock_dm(leader, ctx.channel, log)

            else:

                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {
                        "$set": {
                            f"subguilds.$.members.{ctx.author.id}": {
                                "id": ctx.author.id,
                                "messages": 0
                            }
                        }
                    }
                )
                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.requests": {
                        "$elemMatch": {"$eq": ctx.author.id}
                    }},
                    {"$pull": {"subguilds.$.requests": ctx.author.id}}
                )

                await give_join_role(ctx.author, guild_role_id)

                reply = discord.Embed(
                    title = "✅ Добро пожаловать",
                    description = (
                        f"Вы вступили в гильдию **{guild_name}**\n"
                        f"-> Профиль гильдии: `{prefix}guild-info {guild_name}`"
                    ),
                    color = discord.Color.green()
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

@commands.cooldown(1, 30, commands.BucketType.member)
@client.command(aliases = ["leave-guild", "leaveguild", "lg"])
async def leave_guild(ctx):
    collection = db["subguilds"]

    result = collection.find_one(
        {
            "_id": ctx.guild.id,
            f"subguilds.members.{ctx.author.id}.id": ctx.author.id
        },
        projection={"subguilds.name": True, "subguilds.members": True, "subguilds.role_id": True}
    )
    if result == None:
        reply = discord.Embed(
            title = "❌ Ошибка",
            description = f"Вас нет ни в одной гильдии",
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        result = result["subguilds"]
        for subguild in result:
            if f"{ctx.author.id}" in subguild["members"]:
                guild_name = subguild["name"]
                guild_role_id = subguild["role_id"]
                break
        del result

        no = ["no", "0", "нет"]
        yes = ["yes", "1", "да"]

        warn_emb = discord.Embed(
            title = "🛠 Подтверждение",
            description = (
                f"**->** Ваш счётчик сообщений обнулится, как только Вы покинете гильдию **{guild_name}**.\nПродолжить?\n"
                f"Напишите `да` или `нет`"
            )
        )
        warn_emb.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        warn = await ctx.send(embed = warn_emb)

        msg = await read_message(ctx.channel, ctx.author, 60)
        await warn.delete()

        if msg != "Timeout":
            user_reply = msg.content.lower()
            if user_reply in no:
                await ctx.send("Действие отменено")
            elif user_reply in yes:
                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {
                        "$unset": {
                            f"subguilds.$.members.{ctx.author.id}": ""
                        }
                    }
                )
                await remove_join_role(ctx.author, guild_role_id)
                reply = discord.Embed(
                    title = "🚪 Выход",
                    description = f"Вы вышли из гильдии **{guild_name}**"
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["top"])
async def guilds(ctx, filtration = "messages"):
    collection = db["subguilds"]
    filters = {
        "messages": "`💬`",
        "mentions": "📯"
    }
    filtration = filtration.lower()

    result = collection.find_one({"_id": ctx.guild.id})
    if not filtration in filters:
        reply = discord.Embed(
            title = "💢 Ошибка",
            description = (
                f"Нет фильтра `{filtration}`\n"
                f"Доступные фильтры:\n"
                "> messages\n"
                "> mentions\n"
                f"Или просто `{prefix}guilds`"
            )
        )
        await ctx.send(embed = reply)
    
    elif result == None:
        lb = discord.Embed(
            title = f"Гильдии сервера {ctx.guild.name}",
            description = "Отсутствуют",
            color = discord.Color.blue()
        )
        lb.set_thumbnail(url = f"{ctx.guild.icon_url}")
        await ctx.send(embed = lb)
    else:
        subguilds = result["subguilds"]

        stats = []
        for subguild in subguilds:
            if filtration == "messages":
                total_mes = 0
                for str_id in subguild["members"]:
                    memb = subguild["members"][str_id]
                    total_mes += memb["messages"]
            else:
                total_mes = subguild["mentions"]

            pair = (f"{subguild['name']}", total_mes)
            stats.append(pair)
        del result
        stats.sort(key=lambda i: i[1])
        stats.reverse()

        desc = ""
        for i in range(len(stats)):
            guild_name = f_username(stats[i][0])
            total_mes = stats[i][1]
            desc += f"**{i+1})** {guild_name} • **{total_mes}** {filters[filtration]}\n"
        
        lb = discord.Embed(
            title = f"Гильдии сервера {ctx.guild.name}",
            description = f"Подробнее о гильдии: `{prefix}guild-info Название`\n\n{desc}",
            color = discord.Color.dark_blue()
        )
        lb.set_thumbnail(url = f"{ctx.guild.icon_url}")
        await ctx.send(embed = lb)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["guild-info", "guildinfo", "gi"])
async def guild_info(ctx, *, guild_name):
    collection = db["subguilds"]

    result = collection.find_one({"_id": ctx.guild.id, "subguilds.name": guild_name})
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{prefix}guilds`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        await ctx.send(embed = reply)
    else:
        subguild = get_subguild(result, guild_name)
        del result

        total_mes = 0
        total_memb = 0
        for str_id in subguild["members"]:
            memb = subguild["members"][str_id]
            total_mes += memb["messages"]
            total_memb += 1
        subguild["members"] = None
        leader = client.get_user(subguild["leader_id"])
        
        reply = discord.Embed(
            title = subguild["name"],
            description = (
                f"{subguild['description']}\n"
                f"**->** Топ 10 гильдии: `{prefix}guild-top 1 {guild_name}`"
            ),
            color = discord.Color.green()
        )
        reply.set_thumbnail(url = subguild["avatar_url"])
        reply.add_field(name = "🔰 Владелец", value = f"{leader}", inline=False)
        reply.add_field(name = "👥 Всего участников", value = f"{total_memb}", inline=False)
        reply.add_field(name = "`💬` Всего сообщений", value = f"{total_mes}", inline=False)
        if subguild["mentions"] > 0:
            reply.add_field(name = "📯 Упоминаний", value = f"{subguild['mentions']}", inline = False)
        if subguild["role_id"] != None:
            reply.add_field(name = "🎗 Роль", value = f"<@&{subguild['role_id']}>", inline = False)
        if subguild["private"]:
            reply.add_field(name = "🔒 Приватность", value = "Вступление по заявкам")
        await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["guild-members", "guildmembers", "gm", "guild-top", "gt"])
async def guild_members(ctx, page_num, *, guild_name):
    collection = db["subguilds"]
    interval = 10

    if not page_num.isdigit():
        reply = discord.Embed(
            title = "💢 Неверный аргумент",
            description = (
                f"**{page_num}** должно быть целым числом\n"
                f"Команда: `{prefix}{ctx.command.name} Номер_страницы Гильдия`"
            )
        )
        await ctx.send(embed = reply)
    else:
        page_num = int(page_num)

        result = collection.find_one(
            {"_id": ctx.guild.id, "subguilds.name": guild_name},
            projection={"subguilds.name": True, "subguilds.members": True}
        )
        if result == None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = (
                    f"На сервере нет гильдий с названием **{guild_name}**\n"
                    f"Список гильдий: `{prefix}guilds`"
                ),
                color = discord.Color.from_rgb(40, 40, 40)
            )
            await ctx.send(embed = reply)
        else:
            subguild = get_subguild(result, guild_name)
            del result

            members = subguild["members"]
            total_memb = len(members)
            if interval*(page_num - 1) >= total_memb:
                reply = discord.Embed(
                    title = "💢 Упс",
                    description = f"Страница не найдена. Всего страниц: **{(total_memb - 1)//interval + 1}**"
                )
                await ctx.send(embed = reply)
            else:
                pairs = []
                for key in members:
                    member = members[key]
                    pairs.append((member["id"], member["messages"]))
                pairs.sort(key=lambda i: i[1], reverse=True)

                last_num = min(total_memb, interval*page_num)
                
                desc = ""
                for i in range(interval*(page_num-1), last_num):
                    pair = pairs[i]
                    user = get_member(ctx.guild, pair[0])
                    desc += f"**{i + 1})** {f_username(user)} • {pair[1]} `💬`\n"
                
                lb = discord.Embed(
                    title = f"🔎 Участники гильдии {guild_name}",
                    description = desc,
                    color = discord.Color.green()
                )
                lb.set_footer(text=f"Стр. {page_num}/{(total_memb - 1)//interval + 1}")
                await ctx.send(embed = lb)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["user-guild", "userguild", "ug", "user-info", "userinfo", "ui"])
async def user_guild(ctx, user_s = None):
    if user_s == None:
        user = ctx.author
    else:
        user = detect.member(ctx.guild, user_s)
    if user == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"Вы ввели {user_s}, подразумевая участника, но он не был найден",
        )
        await ctx.send(embed = reply)
    else:
        collection = db["subguilds"]
        result = collection.find_one(
            {"_id": ctx.guild.id, f"subguilds.members.{user.id}.id": user.id}
        )
        if result == None:
            reply = discord.Embed(
                title = f"🛠 Пользователь не в гильдии",
                description = f"Вы можете посмотреть список гильдий здесь: `{prefix}guilds`",
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            for sg in result["subguilds"]:
                if f"{user.id}" in sg["members"]:
                    subguild = sg
                    break
            del result

            total_memb = 0
            total_mes = 0
            for key in subguild["members"]:
                member = subguild["members"][key]
                total_memb += 1
                total_mes += member["messages"]
            subguild["members"] = None
            leader = client.get_user(subguild["leader_id"])

            stat_emb = discord.Embed(
                title = subguild["name"],
                description = subguild["description"],
                color = discord.Color.green()
            )
            stat_emb.set_thumbnail(url = subguild["avatar_url"])
            stat_emb.add_field(name = "🔰 Владелец", value = f"{leader}", inline=False)
            stat_emb.add_field(name = "👥 Всего участников", value = f"{total_memb}", inline=False)
            stat_emb.add_field(name = "`💬` Всего сообщений", value = f"{total_mes}", inline=False)
            if subguild["mentions"] > 0:
                stat_emb.add_field(name = "📯 Упоминаний", value = f"{subguild['mentions']}", inline = False)
            if subguild["role_id"] != None:
                stat_emb.add_field(name = "🎗 Роль", value = f"<@&{subguild['role_id']}>", inline = False)
            if subguild["private"]:
                stat_emb.add_field(name = "🔒 Приватность", value = "Вступление по заявкам")
            await ctx.send(embed = stat_emb)

#========Events========
@client.event
async def on_message(message):
    if message.guild != None:
        collection = db["cmd_channels"]
        result = collection.find_one({"_id": message.guild.id})
        if result == None:
            wl_channels = [message.channel.id]
        elif result["channels"] == None:
            wl_channels = [message.channel.id]
        else:
            wl_channels = result["channels"]
        
        if message.channel.id in wl_channels:
            await client.process_commands(message)
        
        collection = db["subguilds"]

        if not message.author.bot:
            collection.find_one_and_update(
                {
                    "_id": message.guild.id,
                    f"subguilds.members.{message.author.id}.id": message.author.id
                    },
                {
                    "$inc": {
                        f"subguilds.$.members.{message.author.id}.messages": 1
                    }
                }
            )
        
        members = message.mentions
        if members != []:
            search = {}
            search.update([
                ("_id", message.guild.id),
                ("mentioner_id", message.author.id)
            ])
            key_words = [f"subguilds.members.{m.id}.id" for m in members]
            search.update([(key_words[i], members[i].id) for i in range(len(key_words))])
            del members
            
            proj = {"subguilds.name": True}
            proj.update([(kw, True) for kw in key_words])

            result = collection.find_one(
                search,
                projection=proj
            )
            
            if result != None:
                subguilds = result["subguilds"]
                for sg in subguilds:
                    collection.find_one_and_update(
                        {"_id": message.guild.id,
                        "subguilds.name": sg["name"]},
                        {"$inc": {"subguilds.$.mentions": len(sg["members"])}}
                    )

#========Errors==========
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        
        def TimeExpand(time):
            if time//60 > 0:
                return str(time//60)+'мин. '+str(time%60)+' сек.'
            else:
                return str(time)+' сек.'
        
        cool_notify = discord.Embed(
                title='⏳ Подождите немного',
                description = f"Осталось {TimeExpand(int(error.retry_after))}"
            )
        await ctx.send(embed=cool_notify)
#====Exact errors=====
@create_guild.error
async def create_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "🛠 Недостаточно аргументов",
            description = (
                f"**Использование:** `{prefix}{ctx.command.name} [Название гильдии]`\n"
                f"**Пример:** `{prefix}{ctx.command.name} Дамы и господа`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@edit_guild.error
async def edit_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Об аргументах",
            description = (
                "> `name`\n"
                "> `description`\n"
                "> `avatar`\n"
                "> `leader`\n"
                "> `role`\n"
                "> `privacy`\n"
                f'**Использование:** `{prefix}{ctx.command.name} Параметр "Название гильдии" [Новое значение]`\n'
                f'**Пример:** `{prefix}{ctx.command.name} name "Дамы и господа" Хранители`\n'
                f'**Примечания:**\n'
                f'-> Если в названии гильдии есть пробелы, то название нужно указать **"в кавычках"**\n'
                f"-> Если настраиваете владельца или роль гильдии, укажите **@упоминание** или **ID**\n"
                f"-> Если нужно убрать роль гильдии, напишите **delete** в качестве нового значения\n"
                f"-> Если хотите поставить новый аватар гильдии, то в качестве аргумента введите ссылку на картинку\n"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@join_guild.error
async def join_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Название гильдии`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@delete_guild.error
async def delete_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Название гильдии`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@guild_info.error
async def guild_info_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Название гильдии`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@guild_members.error
async def guild_members_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Номер_страницы Название гильдии`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@ping_count.error
async def ping_count_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} @Пользователь`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@reset_guilds.error
async def reset_guilds_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} messages или mentions`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@count_roles.error
async def count_roles_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} "Гильдия" @роль1 @роль2 ...`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@cmd_channels.error
async def cmd_channels_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} #канал-1 #канал-2 ...`\n'
                f"**Сбросить настройки:** `{prefix}{ctx.command.name} delete`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@requests.error
async def requests_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Страница Гильдия`\n'
                f"**Пример:** `{prefix}{ctx.command.name} 1 Моя гильдия`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@accept.error
async def accept_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Номер_заявки Гильдия`\n'
                f"**Пример:** `{prefix}{ctx.command.name} 1 Моя гильдия`\n"
                f"**Список заявок:** `{prefix}requests Страница Гильдия`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@decline.error
async def decline_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Номер_заявки Гильдия`\n'
                f"**Пример:** `{prefix}{ctx.command.name} 1 Моя гильдия`\n"
                f"**Список заявок:** `{prefix}requests Страница Гильдия`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

async def change_status():
    await client.wait_until_ready()
    await client.change_presence(activity=discord.Game(f"{prefix}help"))
client.loop.create_task(change_status())

client.run(token)
