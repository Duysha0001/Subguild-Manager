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

#========Lists and values=========
param_desc = {
    "name": {
        "usage": f'`{prefix}edit-guild name [Старое название] Новое название`',
        "example": f'`{prefix}edit-guild name [Моя гильдия] Лучшая гильдия`'
    },
    "description": {
        "usage": f'`{prefix}edit-guild description [Гильдия] Новое описание`',
        "example": f'`{prefix}edit-guild description [Моя гильдия] Для тех, кто любит общаться`'
    },
    "avatar": {
        "usage": f'`{prefix}edit-guild avatar [Гильдия] Ссылка`',
        "example": f'`{prefix}edit-guild avatar [Моя гильдия] {default_avatar_url}`'
    },
    "leader": {
        "usage": f'`{prefix}edit-guild leader [Гильдия] @Пользователь`',
        "example": f'`{prefix}edit-guild leader [Моя гильдия] @Пользователь`'
    },
    "helper": {
        "usage": f'`{prefix}edit-guild helper [Гильдия] @Пользователь`',
        "example": f'`{prefix}edit-guild helper [Моя гильдия] @Пользователь`'
    },
    "role": {
        "usage": f'`{prefix}edit-guild role [Гильдия] @Роль (или delete)`',
        "example": f'`{prefix}edit-guild role [Моя гильдия] delete`'
    },
    "privacy": {
        "usage": f'`{prefix}edit-guild privacy [Гильдия] on / off`',
        "example": f'`{prefix}edit-guild privacy [Моя гильдия] on`'
    }
}

owner_ids = [301295716066787332]

guild_limit = 30
member_limit = 500

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

def is_int(string):
    out = True
    try:
        int(string)
    except ValueError:
        out = False
    return out

def sep_args(text):
    text += " "
    if text[0] != "[":
        i = text.find(" ")
        return (text[:+i], text[+i:].strip())
    else:
        bal = 0
        sep = len(text) - 1
        for i in range(len(text)):
            s = text[i]
            if s == "[":
                bal += 1
            elif s == "]":
                bal -= 1
            if bal == 0:
                sep = i
                break
        return (text[1:sep], text[+sep+1:].strip())

def exclude(symbols, text):
    out = ""
    for s in text:
        if s not in symbols:
            out += s
    return out

def get_subguild(collection_part, subguild_name):
    out = None
    if "subguilds" in collection_part:
        subguilds = collection_part["subguilds"]
        for subguild in subguilds:
            if "name" in subguild and subguild["name"] == subguild_name:
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
    owner_ids = [301295716066787332]

    to_have = len(perm_array)
    if member.id == member.guild.owner_id or member.id in owner_ids:
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
            if f"{type(role)}" == "<class 'bson.int64.Int64'>":
                role = member.guild.get_role(role)
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

def emj(name):
    emoji_guild = client.get_guild(642107341868630016)
    emoji = discord.utils.get(emoji_guild.emojis, name = name)
    return emoji

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
        member = guild.get_member(ID)
        return member
    
    @staticmethod
    def channel(guild, search):
        ID = carve_int(search)
        if ID == None:
            ID = 0
        channel = guild.get_channel(ID)
        return channel
    
    @staticmethod
    def role(guild, search):
        ID = carve_int(search)
        if ID == None:
            ID = 0
        role = guild.get_role(ID)
        if role == None:
            role = discord.utils.get(guild.roles, name=search)
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
        {"_id": member.guild.id, f"subguilds.members.{member.id}": {"$exists": True}},
        {
            "$unset": {f"subguilds.$.members.{member.id}": ""},
            "$pull": {f"subguilds.$.requests": member.id}
        }
    )

@client.event
async def on_member_ban(guild, member):
    collection = db["subguilds"]

    res = collection.find_one(
        {"_id": guild.id, f"subguilds.members.{member.id}": {"$exists": True}},
        projection={
            "subguilds.name": True,
            "subguilds.members": True,
            "rep_logs": True
        }
    )
    subguild = None
    if res != None:
        for sg in res["subguilds"]:
            for memb in sg["members"]:
                if f"{member.id}" in memb:
                    subguild = sg
                    break
            if subguild != None:
                break
        logs = res["rep_logs"]
    del res

    if subguild != None:
        log = {
            "guild": subguild["name"],
            "changer_id": client.user.id,
            "reason": "Участник был забанен",
            "action": "Изменение",
            "value": -50
        }
        logs.append(log)
        lll = len(logs)
        if lll > 10:
            logs = logs[lll - 10:lll]

        collection.find_one_and_update(
            {"_id": guild.id, f"subguilds.name": subguild["name"]},
            {
                "$inc": {"subguilds.$.reputation": -50},
                "$unset": {f"subguilds.$.members.{member.id}": ""},
                "$set": {"rep_logs": logs}
            },
            upsert=True
        )

@client.event
async def on_guild_remove(guild):
    collection = db["subguilds"]
    collection.delete_one({"_id": guild.id})
    collection = db["cmd_channels"]
    collection.delete_one({"_id": guild.id})

#=========Commands==========
@client.command()
async def logout(ctx):
    if ctx.author.id in owner_ids:
        await ctx.send("Logging out...")
        await client.logout()

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["info", "commands"])
async def help(ctx):
    p = prefix
    user_cmd_desc = (
        f"`{p}join-guild Гильдия` - *зайти в гильдию*\n"
        f"`{p}leave-guild` - *выйти из текущей гильдии*\n"
        f"`{p}top` - *топ гильдий сервера*\n"
        f"‣—‣ `{p}top mentions / members / roles / reputation` - *другие фильтры топа*\n"
        f"`{p}guild-info Гильдия` - *посмотреть подробности гильдии*\n"
        f"`{p}guild-top Страница_топа Гильдия` - *топ участников гильдии*\n"
        f"`{p}user-info @Пользователь` - *посмотреть свой / чужой прогресс*\n"
    )
    owners_cmd_desc = (
        f'`{p}edit-guild Параметр [Гильдия] Новое значение` - *подробнее: `{p}edit-guild`*\n'
        f"`{p}delete-guild Гильдия` - *удаляет гильдию*\n"
        f"`{p}requests Страница Гильдия` - *список заявок на вступление в гильдию*\n"
        f"`{p}accept Номер_заявки Гильдия` - *принять заявку*\n"
        f"`{p}decline Номер_заявки Гильдия` - *отклонить заявку*\n"
        f"‣—‣ `{p}accept/decline all Гильдия` - *принять/отклонить все заявки*\n"
        f"`{p}kick Параметр Значение Гильдия` - *кик разных калибров, подробнее: `{p}kick`*\n"
        f'`{p}count-roles [Название гильдии] @Роль1 @Роль2 ...` - *подсчёт членов гильдии с каждой ролью*\n'
        "> Только мастерам:\n"
        f"`{p}create-guild Название` - *создаёт гильдию*\n"
        f"`{p}rep Параметр Число [Гильдия] Причина` - *действия с репутацией, подробнее: `{p}rep`*\n"
        f"`{p}rep-logs` - *последние 10 действий с репутацией*\n"
    )
    adm_cmd_desc = (
        f"`{p}settings` - *текущие настройки*\n"
        f"`{p}cmd-channels #канал-1 #канал-2 ...` - *настроить каналы реагирования*\n"
        f"‣—‣ `{p}cmd-channels delete` - *сбросить*\n"
        f"`{p}master-role Роль` - *настроить роль мастера гильдий*\n"
        f"‣—‣ `{p}master-role delete` - *сбросить*\n"
        f"`{p}members-limit Число` - *настроить лимит участников на гильдию*\n"
        f"`{p}reset-guilds messages / mentions` - *обнуляет либо упоминания, либо сообщения всех гильдий сервера*\n"
        f"`{p}ping-count @Пользователь` - *настраивает пользователя, пинги которого будут подсчитываться*\n"
    )
    help_emb = discord.Embed(
        title = f"📰 Список команд",
        color = discord.Color.from_rgb(150, 150, 150)
    )
    
    help_emb.add_field(name = "**Всем пользователям**", value = user_cmd_desc, inline=False)
    help_emb.add_field(name = "**Главам гильдий / Мастерам гильдий**", value = owners_cmd_desc, inline=False)
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
            chan_desc = "> Все каналы\n"
        else:
            chan_desc = ""
            for ID in wl_channels:
                chan_desc += f"> {client.get_channel(ID).mention}\n"
        
        collection = db["subguilds"]
        result = collection.find_one(
            {"_id": ctx.guild.id, "mentioner_id": {"$exists": True}},
            projection={
                "mentioner_id": True,
                "member_limit": True,
                "master_role_id": True
            }
        )
        pinger_id = None
        mr_id = None
        lim_desc = member_limit
        if result != None:
            if "mentioner_id" in result:
                pinger_id = result["mentioner_id"]
            if "member_limit" in result:
                lim_desc = result["member_limit"]
            if "master_role_id" in result:
                mr_id = result["master_role_id"]
        
        if pinger_id == None:
            ping_desc = "выключено"
        else:
            ping_desc = f"{client.get_user(pinger_id)}"
        
        if mr_id == None:
            mr_desc = "Отсутствует"
        else:
            mr_desc = f"<@&{mr_id}>"
        
        reply = discord.Embed(
            title = "⚙ Текущие настройки сервера",
            description = (
                f"**Каналы для команд бота:**\n"
                f"{chan_desc}"
                f"**Роль мастера гильдий:**\n"
                f"> {mr_desc}\n"
                f"**Вести подсчёт упоминаний от:**\n"
                f"> {ping_desc}\n"
                f"**Лимит пользователей на гильдию:**\n"
                f"> {lim_desc}\n\n"
                f"-> Список команд: `{prefix}help`"
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
@client.command(aliases = ["members-limit", "memberslimit", "ml"])
async def members_limit(ctx, lim):
    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "💢 Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    elif not lim.isdigit() or "-" in lim:
        reply = discord.Embed(
            title = "💢 Неверный аргумент",
            description = f"Аргумент {lim} должен быть целым положительным числом",
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    elif int(lim) > member_limit or int(lim) < 1:
        reply = discord.Embed(
            title = "❌ Ошибка",
            description = f"Лимит пользователей не может превышать **{member_limit}** на гильдию",
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        collection = db["subguilds"]
        lim = int(lim)

        collection.find_one_and_update(
            {"_id": ctx.guild.id},
            {"$set": {"member_limit": lim}},
            upsert=True
        )
        reply = discord.Embed(
            title = "✅ Настроено",
            description = (
                f"Текущий лимит пользователей в гильдиях: **{lim}**\n"
                f"Отчёт о настройках: `{prefix}settings`"
            ),
            color = discord.Color.dark_green()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["master-role", "masterrole", "mr"])
async def master_role(ctx, *, r_search):
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
        correct_arg = True
        role = discord.utils.get(ctx.guild.roles, name = r_search)
        if role == None:
            role = detect.role(ctx.guild, r_search)
        
        if r_search.lower() == "delete":
            value = None

        elif role == None:
            correct_arg = False
            reply = discord.Embed(
                title = "💢 Неверный аргумент",
                description = f"Вы ввели {r_search}, подразумевая роль, но она не была найдена",
                color = discord.Color.dark_red()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            value = role.id
        
        if correct_arg:
            collection = db["subguilds"]
            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {"$set": {"master_role_id": value}},
                upsert=True
            )

            desc = "Роль мастера гильдий удалена"
            if value != None:
                desc = f"Роль мастера гильдий: <@&{value}>"
            reply = discord.Embed(
                title = "✅ Настроено",
                description = desc,
                color = discord.Color.dark_green()
            )
            await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["rep"])
async def reputation(ctx, param, value=None, *, text_data=None):
    param = param.lower()
    params = {
        "change": {
            "usage": f"`{prefix}rep change Кол-во Гильдия`",
            "example": f"`{prefix}rep change 10 Гильдия`",
            "info": "Изменяет репутацию гильдии на указанное кол-во очков"
        },
        "set": {
            "usage": f"`{prefix}rep set Кол-во Гильдия`",
            "example": f"`{prefix}rep set 70 Гильдия`",
            "info": "Устанавливает у гильдии указанную репутацию"
        }
    }

    if not param in params:
        reply = discord.Embed(
            title = "📑 Неверный параметр",
            description = (
                f"Вы ввели: `{param}`\n"
                f"Доступные параметры:\n"
                "> `change`\n"
                "> `set`\n"
                f"Подробнее: `{prefix}rep change / set`"
            ),
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

    elif value == None or text_data == None:
        param_desc = params[param]
        reply = discord.Embed(
            title = f"❓ {prefix}rep {param}",
            description = (
                f"**Использование:** {param_desc['usage']}\n"
                f"**Пример:** {param_desc['example']}\n"
                f"-> {param_desc['info']}"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

    elif not is_int(value):
        reply = discord.Embed(
            title = "💢 Неверный аргуметн",
            description = f"Входной аргумент {value} должен быть целым числом",
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

    else:
        collection = db["subguilds"]
        guild_name, text = sep_args(text_data)
        if text == "":
            text = "Не указана"

        result = collection.find_one(
            {"_id": ctx.guild.id, "subguilds.name": guild_name},
            projection={
                "master_role_id": True,
                "rep_logs": True
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
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        else:
            mr_id = None
            if "master_role_id" in result:
                mr_id = result["master_role_id"]
            rep_logs = []
            if "rep_logs" in result:
                rep_logs = result["rep_logs"]
            
            if not has_roles(ctx.author, [mr_id]) and not has_permissions(ctx.author, ["administrator"]):
                reply = discord.Embed(
                    title = "❌ Недостаточно прав",
                    description = (
                        "**Нужно быть одним из них:**\n"
                        "> Администратор\n"
                        "> Мастер гильдий"
                    ),
                    color = discord.Color.dark_red()
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            else:
                if param == "change":
                    mode = "$inc"
                    act = "Изменение"
                elif param == "set":
                    mode = "$set"
                    act = "Установлено"
                
                log = {
                    "guild": guild_name,
                    "changer_id": ctx.author.id,
                    "reason": text,
                    "action": act,
                    "value": int(value)
                }
                rep_logs.append(log)
                lll = len(rep_logs)
                rep_logs = rep_logs[lll-10:lll]

                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {
                        mode: {"subguilds.$.reputation": int(value)},
                        "$set": {"rep_logs": rep_logs}
                    },
                    upsert=True
                )

                reply = discord.Embed(
                    title = "✅ Выполнено",
                    description = f"Репутация гильдии изменена.\nПрофиль: `{prefix}guild-info {guild_name}`",
                    color = discord.Color.dark_green()
                )
                await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["rep-logs", "replogs"])
async def rep_logs(ctx):
    collection = db["subguilds"]

    result = collection.find_one(
        {"_id": ctx.guild.id},
        projection={
            "master_role_id": True,
            "rep_logs": True
        }
    )
    mr_id = None
    if result != None and "master_role_id" in result:
        mr_id = result["master_role_id"]
    rep_logs = []
    if result != None and "rep_logs" in result:
        rep_logs = result["rep_logs"]
    
    if not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
        reply = discord.Embed(
            title = "💢 Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор\n"
                "Или\n"
                "> Мастер гильдий"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        log_emb = discord.Embed(
            title = "🛠 Последние 10 действий",
            color = discord.Color.dark_orange()
        )
        for log in rep_logs:
            user = client.get_user(log["changer_id"])
            desc = (
                f"Модератор: {f_username(user)}\n"
                f"{log['action']} на **{log['value']}** 🔅\n"
                f"Причина: {log['reason']}"
            )
            log_emb.add_field(name=f"💠 **Гильдия:** {log['guild']}", value=desc)
        await ctx.send(embed=log_emb)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["create-guild", "createguild", "cg"])
async def create_guild(ctx, *, guild_name):
    collection = db["subguilds"]
    guild_name = exclude(["[", "]"], guild_name)

    result = collection.find_one(
        {"_id": ctx.guild.id},
        projection={
            "_id": True,
            "subguilds.name": True,
            "master_role_id": True
        }
    )
    mr_id = None
    if result != None and "master_role_id" in result:
        mr_id = result["master_role_id"]

    if not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
        reply = discord.Embed(
            title = "💢 Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор\n"
                "Или\n"
                "> Мастер гильдий"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        total_guilds = 0
        if result != None:
            total_guilds = len(result["subguilds"])

        if total_guilds >= guild_limit:
            reply = discord.Embed(
                title = "🛠 Максимум гильдий",
                description = (
                    f"На этом сервере достигнут максимум гильдий - {guild_limit}\n"
                    f"Удалить гильдию: `{prefix}delete-guild Гильдия`"
                ),
                color = discord.Color.dark_orange()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            subguild = get_subguild(result, guild_name)
            if subguild != None:
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
                                "helper_id": None,
                                "role_id": None,
                                "private": False,
                                "requests": [],
                                "reputation": 100,
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
@client.command(aliases = ["edit-guild", "editguild", "eg", "edit"])
async def edit_guild(ctx, parameter, *, text_data = None):
    collection = db["subguilds"]
    parameter = parameter.lower()
    parameters = {
        "name": "name",
        "description": "description",
        "avatar": "avatar_url",
        "leader": "leader_id",
        "helper": "helper_id",
        "role": "role_id",
        "privacy": "private"
    }

    if parameter not in parameters:
        reply = discord.Embed(
            title = "📑 Доступные параметры настроек",
            description = (
                "> `name`\n"
                "> `description`\n"
                "> `avatar`\n"
                "> `leader`\n"
                "> `helper`\n"
                "> `role`\n"
                "> `privacy`\n"
                f'**Использование:** `{prefix}{ctx.command.name} Параметр [Название гильдии] Новое значение`\n'
                f'**Пример:** `{prefix}{ctx.command.name} name [Моя гильдия] Хранители`\n'
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
        
        guild_name, text = sep_args(text_data)

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
            mr_id = None
            if "master_role_id" in result:
                mr_id = result["master_role_id"]

            if ctx.author.id != leader_id and not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
                reply = discord.Embed(
                    title = "❌ Недостаточно прав",
                    description = (
                        f"Нужно быть одним из них:\n"
                        f"> Глава гильдии {guild_name}\n"
                        "> Мастер гильдий\n"
                        "> Администратор"
                    ),
                    color = discord.Color.dark_red()
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                correct_arg = True
                value = text
                if parameter == "name":
                    value = exclude(["[", "]"], text)
                    if value in [sg["name"] for sg in result["subguilds"]]:
                        correct_arg = False
                        reply = discord.Embed(
                            title = "❌ Ошибка",
                            description = f"Гильдия с названием {f_username(value)} уже есть",
                            color = discord.Color.dark_red()
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                elif parameter in ["leader", "helper"]:
                    value = detect.member(ctx.guild, text)

                    if text.lower() == "delete":
                        value = None

                    elif value == None:
                        correct_arg = False

                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Вы ввели {text}, подразумевая участника, но он не был найден",
                            color = discord.Color.dark_red()
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                    elif value.id == leader_id:
                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"{f_username(value)} является главой этой гильдии.",
                            color = discord.Color.dark_red()
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
        projection={
            "subguilds.name": True,
            "subguilds.leader_id": True,
            "master_role_id": True
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
        mr_id = None
        if "master_role_id" in result:
            mr_id = result["master_role_id"]
        
        subguild = get_subguild(result, guild_name)
        del result

        if ctx.author.id != subguild["leader_id"] and not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = (
                    f"Нужно быть одним из них:\n"
                    f"> Глава гильдии {guild_name}\n"
                    "> Мастер гильдий\n"
                    "> Администратор"
                ),
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
@client.command(aliases = ["req", "request"])
async def requests(ctx, page, *, guild_name):
    collection = db["subguilds"]
    interval = 20

    result = collection.find_one(
        {"_id": ctx.guild.id, "subguilds.name": guild_name},
        projection={
            "master_role_id": True,
            "subguilds.leader_id": True,
            "subguilds.helper_id": True,
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
        mr_id = None
        if "master_role_id" in result:
            mr_id = result["master_role_id"]
        
        subguild = get_subguild(result, guild_name)
        del result

        if ctx.author.id not in [subguild["leader_id"], subguild["helper_id"]] and not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = (
                    f"Нужно быть одним из них:\n"
                    f"> Глава / помощник гильдии {guild_name}\n"
                    "> Мастер гильдий\n"
                    "> Администратор"
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
                title = "🔎 Страница не найдена"
                desc = f"**Всего страниц:** {total_pages}"
                if length == 0:
                    title = "📜 Список запросов пуст"
                    desc = "Заходите позже 🎀"
                reply = discord.Embed(
                    title = title,
                    description = desc,
                    color = discord.Color.dark_teal()
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
                        f"**В гильдию:** {f_username(guild_name)}\n"
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
            "master_role_id": True,
            "subguilds.leader_id": True,
            "subguilds.helper_id": True,
            "subguilds.requests": True,
            "subguilds.name": True,
            "subguilds.private": True,
            "subguilds.role_id": True
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
        mr_id = None
        if "master_role_id" in result:
            mr_id = result["master_role_id"]
        
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

        if ctx.author.id not in [subguild["leader_id"], subguild["helper_id"]] and not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
            correct_args = False

            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = (
                    f"Нужно быть одним из них:\n"
                    f"> Глава / помощник гильдии {guild_name}\n"
                    "> Мастер гильдий\n"
                    "> Администратор"
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
                for ID in id_list:
                    client.loop.create_task(give_join_role(get_member(ctx.guild, ID), subguild["role_id"]))
                
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

                await give_join_role(member, subguild["role_id"])
            
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
            "subguilds.helper_id": True,
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
        mr_id = None
        if "master_role_id" in result:
            mr_id = result["master_role_id"]
        
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

        if ctx.author.id not in [subguild["leader_id"], subguild["helper_id"]] and not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
            correct_args = False

            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = (
                    f"Нужно быть одним из них:\n"
                    f"> Глава / помощник гильдии {guild_name}\n"
                    "> Мастер гильдий\n"
                    "> Администратор"
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

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command()
async def kick(ctx, parameter, value = None, *, guild_name = None):
    parameter = parameter.lower()
    params = {
        "user": {
            "usage": f"`{prefix}kick user @Участник Гильдия`",
            "example": f"`{prefix}kick user @Участник Моя Гильдия`",
            "info": "Кикнуть конкретного участника"
        },
        "under": {
            "usage": f"`{prefix}kick under Планка_сообщений Гильдия`",
            "example": f"`{prefix}kick under 50 Моя Гильдия`",
            "info": "Кикнуть тех, у кого сообщений меньше заданной планки"
        },
        "last": {
            "usage": f"`{prefix}kick last Кол-во Гильдия`",
            "example": f"`{prefix}kick last 10 Моя гильдия`",
            "info": "Кикнуть сколько-то последних участников"
        }
    }
    if not parameter in params:
        desc = ""
        for param in params:
            desc += f"> `{param}`\n"
        reply = discord.Embed(
            title = "❌ Неверный параметр",
            description = f"Вы ввели: `{parameter}`\nДоступные параметры:\n{desc}",
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    elif value == None or guild_name == None:
        reply = discord.Embed(
            title = f"🛠 {prefix}kick {parameter}",
            description = (
                f"**Описание:** {params[parameter]['info']}\n"
                f"**Использование:** {params[parameter]['usage']}\n"
                f"**Пример:** {params[parameter]['example']}"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        collection = db["subguilds"]
        result = collection.find_one(
            {"_id": ctx.guild.id, "subguilds.name": guild_name},
            projection={
                "master_role_id": True,
                "subguilds.name": True,
                "subguilds.members": True,
                "subguilds.role_id": True,
                "subguilds.leader_id": True,
                "subguilds.helper_id": True
            }
        )
        if result == None:
            reply = discord.Embed(
                title = "❌ Гильдия не найдена",
                description = f"На сервере нет гильдии с названием **{guild_name}**",
                color = discord.Color.dark_red()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            mr_id = None
            if "master_role_id" in result:
                mr_id = result["master_role_id"]
            
            subguild = get_subguild(result, guild_name)
            del result

            if ctx.author.id not in [subguild["leader_id"], subguild["helper_id"]] and not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
                reply = discord.Embed(
                    title = "❌ Недостаточно прав",
                    description = (
                        f"Нужно быть одним из них:\n"
                        f"> Глава / помощник гильдии {guild_name}\n"
                        "> Мастер гильдий\n"
                        "> Администратор"
                    ),
                    color = discord.Color.dark_red()
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            elif parameter == "user":
                user = detect.member(ctx.guild, value)
                if user == None:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = f"Вы ввели {value}, подразумевая участника, но он не был найден",
                        color = discord.Color.dark_red()
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                elif user.id == subguild["leader_id"]:
                    desc = "Вы не можете кикнуть главу гильдии"
                    if user.id == ctx.author.id:
                        desc = "Вы не можете кикнуть самого себя"
                    reply = discord.Embed(
                        title = "❌ Ошибка",
                        description = desc,
                        color = discord.Color.dark_red()
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                else:
                    collection.find_one_and_update(
                        {"_id": ctx.guild.id, "subguilds.name": guild_name},
                        {"$unset": {f"subguilds.$.members.{user.id}": ""}}
                    )
                    reply = discord.Embed(
                        title = "✅ Выполнено",
                        description = f"{f_username(user)} был исключён из гильдии **{guild_name}**",
                        color = discord.Color.dark_green()
                    )
                await remove_join_role(user, subguild["role_id"])
                await ctx.send(embed = reply)
            
            elif parameter == "under":
                if not value.isdigit() or "-" in value:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = f"Планка сообщений должна быть целым положительным числом\nВы ввели: {value}",
                        color = discord.Color.dark_red()
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                else:
                    value = int(value)

                    memb_data = subguild["members"]
                    holder = []
                    for key in memb_data:
                        memb = memb_data[key]
                        if memb["messages"] <= value and memb["id"] != subguild["leader_id"]:
                            holder.append(memb["id"])
                    del memb_data

                    to_unset = {}
                    to_unset.update([(f"subguilds.$.members.{ID}", "") for ID in holder])
                    
                    if to_unset != {}:
                        collection.find_one_and_update(
                            {"_id": ctx.guild.id, "subguilds.name": guild_name},
                            {"$unset": to_unset}
                        )
                    reply = discord.Embed(
                        title = "✅ Выполнено",
                        description = f"Из гильдии **{guild_name}** исключено {len(holder)} участник(ов)",
                        color = discord.Color.dark_green()
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")

                    if subguild["role_id"] != None:
                        for ID in holder:
                            client.loop.create_task(remove_join_role(get_member(ctx.guild, ID), subguild["role_id"]))
                
                await ctx.send(embed = reply)

            elif parameter == "last":
                if not value.isdigit() or "-" in value:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = f"Кол-во участников должно быть целым положительным числом\nВы ввели: {value}",
                        color = discord.Color.dark_red()
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                else:
                    value = int(value)

                    memb_data = subguild["members"]
                    pairs = []
                    for key in memb_data:
                        memb = memb_data[key]
                        if memb["id"] != subguild["leader_id"]:
                            pairs.append((memb["id"], memb["messages"]))
                    del memb_data

                    pairs.sort(key=lambda i: i[1], reverse=True)
                    
                    length = len(pairs)
                    segment = min(value, length)

                    pairs = pairs[length - segment: length]

                    to_unset = {}
                    to_unset.update([(f"subguilds.$.members.{pair[0]}", "") for pair in pairs])
                    
                    if to_unset != {}:
                        collection.find_one_and_update(
                            {"_id": ctx.guild.id, "subguilds.name": guild_name},
                            {"$unset": to_unset}
                        )
                    reply = discord.Embed(
                        title = "✅ Выполнено",
                        description = f"Из гильдии **{guild_name}** исключено {segment} последних участник(ов)",
                        color = discord.Color.dark_green()
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")

                    if subguild["role_id"] != None:
                        for pair in pairs:
                            ID = pair[0]
                            client.loop.create_task(remove_join_role(get_member(ctx.guild, ID), subguild["role_id"]))
                
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
            projection = {"subguilds.name": True, "subguilds.members": True}
        )
        if result != None:
            for sg in result["subguilds"]:
                zero_data = {}
                zero_data.update([
                    (f"subguilds.$.members.{key}", {"id": int(key), "messages": 0}) for key in sg["members"]])
                if zero_data != {}:
                    collection.find_one_and_update(
                        {"_id": ctx.guild.id, "subguilds.name": sg["name"]},
                        {"$set": zero_data}
                    )
        reply = discord.Embed(
            title = "♻ Завершено",
            description = "Сброс сообщений закончен",
            color = discord.Color.green()
        )
    
    await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["count-roles", "countroles", "cr"])
async def count_roles(ctx, *, text_data):
    collection = db["subguilds"]

    guild_name, text = sep_args(text_data)
    raw_roles = c_split(text)
    
    result = collection.find_one(
        {"_id": ctx.guild.id, "subguilds.name": guild_name},
        projection={
            "master_role_id": True,
            "subguilds.name": True,
            "subguilds.members": True,
            "subguilds.leader_id": True,
            "subguilds.helper_id": True
        }
    )
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"На сервере нет гильдии с названием **{guild_name}**",
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        mr_id = None
        if "master_role_id" in result:
            mr_id = result["master_role_id"]
        
        subguild = get_subguild(result, guild_name)
        del result

        if ctx.author.id not in [subguild["leader_id"], subguild["helper_id"]] and not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = (
                    f"Нужно быть одним из них:\n"
                    f"> Глава / помощник гильдии {guild_name}\n"
                    "> Мастер гильдий\n"
                    "> Администратор"
                ),
                color = discord.Color.dark_red()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            roles = [detect.role(ctx.guild, s) for s in raw_roles]
            if None in roles or roles == []:
                reply = discord.Embed(
                    title = f"💢 Ошибка",
                    description = (
                        f"В качестве ролей укажите их **@Упоминания** или **ID**\n"
                        f'**Пример:** `{prefix}count-roles "{guild_name}" {ctx.guild.default_role.id}`'
                    )
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            else:
                pairs = [[r, 0] for r in roles]
                for key in subguild["members"]:
                    memb = subguild["members"][key]
                    member = ctx.guild.get_member(memb["id"])
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
                    color = discord.Color.teal()
                )
                await ctx.send(embed = reply)

@commands.cooldown(1, 30, commands.BucketType.member)
@client.command(aliases = ["join-guild", "joinguild", "jg", "join"])
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
            color = discord.Color.dark_red()
        )
        await ctx.send(embed = reply)
    else:
        m_lim = member_limit
        if "member_limit" in result:
            m_lim = result["member_limit"]

        subguild = get_subguild(result, guild_name)
        guild_role_id = subguild["role_id"]
        private = subguild["private"]
        total_memb = len(subguild["members"])

        if total_memb >= m_lim:
            reply = discord.Embed(
                title = "🛠 Гильдия переполнена",
                description = f"В этой гильдии достигнут максимум участников - {m_lim}",
                color = discord.Color.from_rgb(145, 74, 2)
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            result = result["subguilds"]
            user_guild = None
            for sg in result:
                if f"{ctx.author.id}" in sg["members"]:
                    user_guild = sg["name"]
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
                if private and ctx.author.id not in [subguild["leader_id"], subguild["helper_id"]]:
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
                    if subguild["leader_id"] != None:
                        leader = client.get_user(subguild["leader_id"])
                        client.loop.create_task(knock_dm(leader, ctx.channel, log))
                    if subguild["helper_id"] != None:
                        helper = client.get_user(subguild["helper_id"])
                        client.loop.create_task(knock_dm(helper, ctx.channel, log))

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
@client.command(aliases = ["leave-guild", "leaveguild", "lg", "leave"])
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
async def guilds(ctx, filtration = "messages", *, extra = "пустую строку"):
    collection = db["subguilds"]
    filters = {
        "messages": "`💬`",
        "mentions": "📯",
        "members": "👥",
        "roles": "🎗",
        "reputation": "🔅"
    }
    filtration = filtration.lower()

    result = collection.find_one({"_id": ctx.guild.id})
    role = detect.role(ctx.guild, extra)

    if not filtration in filters:
        reply = discord.Embed(
            title = "💢 Ошибка",
            description = (
                f"Нет фильтра `{filtration}`\n"
                f"Доступные фильтры:\n"
                "> messages\n"
                "> mentions\n"
                "> members\n"
                "> roles\n"
                f"Или просто `{prefix}guilds`"
            )
        )
        await ctx.send(embed = reply)
    elif filtration == "roles" and role == None:
        reply = discord.Embed(
            title = "💢 Ошибка",
            description = f"Вы ввели {extra}, подразумевая роль, но она не была найдена",
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
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
                desc = "Фильтрация по количеству сообщений"
                total = 0
                for str_id in subguild["members"]:
                    memb = subguild["members"][str_id]
                    total += memb["messages"]
            elif filtration == "roles":
                desc = f"Фильтрация по количеству участников, имеющих роль <@&{role.id}>"
                total = 0
                for key in subguild["members"]:
                    memb = subguild["members"][key]
                    member = ctx.guild.get_member(memb["id"])
                    if member != None and role in member.roles:
                        total += 1
            elif filtration == "mentions":
                desc = "Фильтрация по количеству упоминаний"
                total = subguild["mentions"]
            elif filtration == "members":
                desc = "Фильтрация по количеству участников"
                total = len(subguild["members"])
            elif filtration == "reputation":
                desc = "Фильтрация по репутации"
                total = subguild["reputation"]

            pair = (f"{subguild['name']}", total)
            stats.append(pair)
        del result
        stats.sort(key=lambda i: i[1])
        stats.reverse()

        table = ""
        for i in range(len(stats)):
            guild_name = f_username(stats[i][0])
            total = stats[i][1]
            table += f"**{i+1})** {guild_name} • **{total}** {filters[filtration]}\n"
        
        lb = discord.Embed(
            title = f"Гильдии сервера {ctx.guild.name}",
            description = f"{desc}\nПодробнее о гильдии: `{prefix}guild-info Название`\n\n{table}",
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
        
        reply = discord.Embed(
            title = subguild["name"],
            description = (
                f"{subguild['description']}\n"
                f"**->** Топ 10 гильдии: `{prefix}guild-top 1 {guild_name}`"
            ),
            color = discord.Color.green()
        )
        reply.set_thumbnail(url = subguild["avatar_url"])
        if subguild['leader_id'] != None:
            leader = client.get_user(subguild["leader_id"])
            reply.add_field(name = "💠 Владелец", value = f"> {f_username(leader)}", inline=False)
        if subguild['helper_id'] != None:
            helper = client.get_user(subguild["helper_id"])
            reply.add_field(name = "🔰 Помощник", value = f"> {f_username(helper)}", inline=False)
        reply.add_field(name = "👥 Всего участников", value = f"> {total_memb}", inline=False)
        reply.add_field(name = "`💬` Всего сообщений", value = f"> {total_mes}", inline=False)
        reply.add_field(name = "🔅 Репутация", value = f"> {subguild['reputation']}", inline=False)
        if subguild["mentions"] > 0:
            reply.add_field(name = "📯 Упоминаний", value = f"> {subguild['mentions']}", inline=False)
        if subguild["role_id"] != None:
            reply.add_field(name = "🎗 Роль", value = f"> <@&{subguild['role_id']}>", inline=False)
        if subguild["private"]:
            reply.add_field(name = "🔒 Приватность", value = "> Вступление по заявкам")
        await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["guild-members", "guildmembers", "gm", "guild-top", "gt"])
async def guild_members(ctx, page_num, *, guild_name):
    collection = db["subguilds"]
    interval = 15

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
            {"_id": ctx.guild.id, f"subguilds.members.{user.id}.id": user.id},
            projection={"subguilds.requests": False}
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

            user_mes = subguild["members"][f"{user.id}"]["messages"]
            pairs = [(int(ID), subguild["members"][ID]["messages"]) for ID in subguild["members"]]
            subguild["members"] = {}
            pairs.sort(key=lambda i: i[1], reverse=True)

            place = pairs.index((user.id, user_mes)) + 1

            stat_emb = discord.Embed(color = discord.Color.blue())
            stat_emb.add_field(name="🛡 Гильдия", value=f_username(subguild['name']), inline = False)
            stat_emb.add_field(name="`💬` Написано сообщений", value=f"{user_mes}", inline = False)
            stat_emb.add_field(name="🏅 Место", value=f"{place} / {len(pairs)}", inline = False)
            stat_emb.set_author(name = f"Профиль 🔎 {user}", icon_url = f"{user.avatar_url}")
            stat_emb.set_thumbnail(url = subguild["avatar_url"])
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
                "> `helper`\n"
                "> `role`\n"
                "> `privacy`\n"
                f'**Использование:** `{prefix}{ctx.command.name} Параметр [Название гильдии] Новое значение`\n'
                f'**Пример:** `{prefix}{ctx.command.name} name [Дамы и господа] Хранители`\n'
                f'**Подробнее о параметрах:**\n'
                f"`{prefix}{ctx.command.name} name`\n"
                f"`{prefix}{ctx.command.name} description`\n"
                f"`{prefix}{ctx.command.name} ...`\n"
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
                f'**Использование:** `{prefix}{ctx.command.name} [Гильдия] @роль1 @роль2 ...`'
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

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Параметр Значение Гильдия`\n'
                "**Параметры:**\n"
                "> `user`\n"
                "> `under`\n"
                "> `last`\n"
                f"**Пример:** `{prefix}{ctx.command.name} user @Участник Моя гильдия`\n"
                f"**Подробнее:** `{prefix}{ctx.command.name} user (или under и last)`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@reputation.error
async def reputation_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Об аргументах",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Параметр Число [Гильдия] Причина`\n'
                "**Параметры:**\n"
                "> `change`\n"
                "> `set`\n"
                f"**Пример:** `{prefix}{ctx.command.name} change 10 Гильдия Участник был наказан`\n"
                "**Подробнее:**\n"
                f"`{prefix}{ctx.command.name} change`\n"
                f"`{prefix}{ctx.command.name} set`\n"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@members_limit.error
async def members_limit_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Число`\n'
                f"**Пример:** `{prefix}{ctx.command.name} 50`\n"
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
