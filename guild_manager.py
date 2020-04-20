import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import os
import datetime

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
turned_on_at = datetime.datetime.utcnow()

param_desc = {
    "name": {
        "usage": f'`{prefix}edit-guild name [Старое название] Новое название`',
        "example": f'`{prefix}edit-guild name [Моя гильдия] Лучшая гильдия`'
    },
    "description": {
        "usage": f'`{prefix}edit-guild description [Гильдия] Новое описание`',
        "example": f'`{prefix}edit-guild description [Моя гильдия] Для тех, кто любит общаться`'
    },
    "avatar_url": {
        "usage": f'`{prefix}edit-guild avatar [Гильдия] Ссылка`',
        "example": f'`{prefix}edit-guild avatar [Моя гильдия] {default_avatar_url}`'
    },
    "leader_id": {
        "usage": f'`{prefix}edit-guild leader [Гильдия] @Пользователь`',
        "example": f'`{prefix}edit-guild leader [Моя гильдия] @Пользователь`'
    },
    "helper_id": {
        "usage": f'`{prefix}edit-guild helper [Гильдия] @Пользователь`',
        "example": f'`{prefix}edit-guild helper [Моя гильдия] @Пользователь`'
    },
    "role_id": {
        "usage": f'`{prefix}edit-guild role [Гильдия] @Роль (или delete)`',
        "example": f'`{prefix}edit-guild role [Моя гильдия] delete`'
    },
    "private": {
        "usage": f'`{prefix}edit-guild privacy [Гильдия] on / off`',
        "example": f'`{prefix}edit-guild privacy [Моя гильдия] on`'
    }
}

owner_ids = [301295716066787332]

exp_buffer = {"last_clean": datetime.datetime.utcnow()}

guild_limit = 30
member_limit = 500
#======== Functions ========
from functions import detect, has_permissions, has_roles, carve_int, find_alias, get_field, has_any_permission

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

def get_subguild(collection_part, subguild_sign):
    out = None
    if collection_part != None and "subguilds" in collection_part:
        user_id_given = "int" in f"{type(subguild_sign)}".lower()

        subguilds = collection_part["subguilds"]
        for subguild in subguilds:
            if user_id_given:
                if f"{subguild_sign}" in subguild["members"]:
                    out = subguild
                    break
            else:
                if subguild["name"] == subguild_sign:
                    out = subguild
                    break
    return out

def is_command(word):
    out = False
    for cmd in client.commands:
        group = cmd.aliases
        group.append(cmd.name)
        if word in group:
            out = True
            break
    return out

def image_link(string):
    return string.startswith("https://")

def role_gte(role, member):
    return member.id == member.guild.owner_id or role.position == member.top_role.position

def anf(user):
    line = f"{user}"
    fsymbs = ">`*_~|"
    out = ""
    for s in line:
        if s in fsymbs:
            out += f"\\{s}"
        else:
            out += s
    return out

def emj(name):
    emoji_guild = client.get_guild(642107341868630016)
    emoji = discord.utils.get(emoji_guild.emojis, name = name)
    return emoji

def mmorpg_col(col_name):
    colors = {
        "paper": discord.Color.from_rgb(163, 139, 101),
        "canopy": discord.Color.from_rgb(120, 55, 55),
        "sky": discord.Color.from_rgb(131, 171, 198),
        "clover": discord.Color.from_rgb(59, 160, 113),
        "vinous": discord.Color.from_rgb(135, 20, 20),
        "lilac": discord.Color.from_rgb(120, 100, 153),
        "pancake": discord.Color.from_rgb(211, 150, 65)
    }
    return colors[col_name]

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

#======== Events =========

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
@client.command(aliases = ["bot-stats"])
async def bot_stats(ctx):
    servers = client.guilds
    total_users = 0
    total_servers = 0
    for server in servers:
        total_users += len(server.members)
        total_servers += 1
    
    dev_desc = ""
    for owner_id in owner_ids:
        dev_desc += f"> {anf(client.get_user(owner_id))}\n"
    
    now = datetime.datetime.utcnow()
    delta = now - turned_on_at
    delta_sec = delta.seconds
    delta_exp = {
        "сут": delta.days,
        "ч": delta_sec//3600,
        "мин": delta_sec%3600//60,
        "сек": delta_sec%60
    }
    delta_desc = ""
    for key in delta_exp:
        if delta_exp[key] != 0:
            delta_desc += f"{delta_exp[key]} {key} "

    link_desc = (
        "> [Добавить бота](https://discordapp.com/api/oauth2/authorize?client_id=677976225876017190&permissions=470150209&scope=bot)\n"
        "> [Сервер бота](https://discord.gg/Hp8XFcp)"
    )

    reply = discord.Embed(
        title = "📊 Статистика бота",
        color = mmorpg_col("lilac")
    )
    reply.set_thumbnail(url = f"{client.user.avatar_url}")
    reply.add_field(name="📚 **Всего серверов**", value=f"> {total_servers}", inline=False)
    reply.add_field(name="👥 **Всего пользователей**", value=f"> {total_users}", inline=False)
    reply.add_field(name="🌐 **Бот онлайн**", value=f"> {delta_desc}", inline=False)
    reply.add_field(name="🛠 **Разработчик**", value=dev_desc, inline=False)
    reply.add_field(name="🔗 **Ссылки**", value=link_desc, inline=False)

    await ctx.send(embed = reply)

@commands.cooldown(1, 1, commands.BucketType.member)
@client.command()
async def help(ctx, *, section=None):
    p = ctx.prefix
    sections = {
        "settings": ["s", "настройки"],
        "guilds": ["гильдии"],
        "manage guilds": ["set guilds", "настроить гильдию"]
    }
    titles = {
        "settings": "О настройках",
        "guilds": "О гильдиях",
        "manage guilds": "О ведении гильдий"
    }
    if section is None:
        reply = discord.Embed(
            title="📖 Меню помощи",
            description=(
                "Введите команду, интересующую Вас:\n\n"
                f"`{p}help guilds` - о гильдиях\n"
                f"`{p}help manage guilds` - ведение гильдии\n"
                f"`{p}help settings` - настройки\n\n"
                f"**Состояние бота:** `{p}bot-stats`\n"
                "**[Добавить на сервер](https://discordapp.com/api/oauth2/authorize?client_id=677976225876017190&permissions=470150209&scope=bot)**"
            ),
            color=mmorpg_col("sky")
        )
        reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed=reply)
    
    else:
        section = find_alias(sections, section)
        if section is None:
            reply = discord.Embed(
                title="🔎 Раздел не найден",
                description=f"Попробуйте снова с одной из команд, указанных в `{p}help`"
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            text = open(f"help/{section}.txt", "r", encoding="utf8").read()
            text = text.replace("{p}", p)

            reply = discord.Embed(
                title=f"📋 {titles[section]}",
                description=(
                    f"Подробнее о команде: `{p}команда`\n\n"
                    f"{text}"
                ),
                color=ctx.guild.me.color
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

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
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        collection = db["cmd_channels"]
        result = collection.find_one({"_id": ctx.guild.id})
        wl_channels = get_field(result, "channels")
        
        if wl_channels is None:
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
        pinger_id = get_field(result, "mentioner_id")
        mr_id = get_field(result, "master_role_id")
        lim_desc = get_field(result, "member_limit", default=member_limit)
        
        if pinger_id is None:
            ping_desc = "выключено"
        else:
            ping_desc = f"{client.get_user(pinger_id)}"
        
        if mr_id is None:
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
            color = mmorpg_col("lilac")
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
            color = mmorpg_col("vinous")
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
            color = mmorpg_col("clover")
        )
        await ctx.send(embed = reply)

    else:
        channels = [detect.channel(ctx.guild, s) for s in raw_ch]
        if None in channels:
            reply = discord.Embed(
                title = f"💢 Ошибка",
                description = (
                    f"В качестве каналов укажите их **#ссылки** или **ID**"
                ),
                color=mmorpg_col("vinous")
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
                color = mmorpg_col("lilac")
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
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    elif not lim.isdigit() or "-" in lim:
        reply = discord.Embed(
            title = "💢 Неверный аргумент",
            description = f"Аргумент {lim} должен быть целым положительным числом",
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    elif int(lim) > member_limit or int(lim) < 1:
        reply = discord.Embed(
            title = "❌ Ошибка",
            description = f"Лимит пользователей не может превышать **{member_limit}** на гильдию",
            color = mmorpg_col("vinous")
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
            color = mmorpg_col("clover")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@commands.cooldown(1, 30, commands.BucketType.member)
@client.command(aliases=["clear-guilds", "delete-all-guilds"])
async def clear_guilds(ctx):
    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "❌ Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

    else:
        reply = discord.Embed(
            title="🛠 Подтверждение",
            description=(
                "Использовав эту команду Вы удалите **все** гильдии этого сервера. Продолжить?\n"
                "Напишите `да` или `нет`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        sys_msg = await ctx.send(embed=reply)

        msg = await read_message(ctx.channel, ctx.author, 60)
        if msg != "Timeout":
            reply_text = msg.content.lower()
            if reply_text in ["yes", "1", "да"]:
                collection = db["subguilds"]
                collection.find_one_and_update(
                    {"_id": ctx.guild.id},
                    {"$unset": {"subguilds": ""}}
                )
                reply = discord.Embed(
                    title="♻ Выполнено",
                    description = "Все гильдии удалены",
                    color=mmorpg_col("clover")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
                await sys_msg.delete()
            else:
                reply = discord.Embed(
                    title="❌ Отмена",
                    description="Действие отменено",
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)
                await sys_msg.delete()

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
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

    else:
        correct_arg = True
        role = discord.utils.get(ctx.guild.roles, name = r_search)
        if role is None:
            role = detect.role(ctx.guild, r_search)
        
        if r_search.lower() == "delete":
            value = None

        elif role is None:
            correct_arg = False
            reply = discord.Embed(
                title = "💢 Неверный аргумент",
                description = f"Вы ввели {r_search}, подразумевая роль, но она не была найдена",
                color = mmorpg_col("vinous")
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
                color = mmorpg_col("clover")
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
            "info": "Изменяет репутацию гильдии на указанное кол-во очков",
            "log": "Изменено"
        },
        "set": {
            "usage": f"`{prefix}rep set Кол-во Гильдия`",
            "example": f"`{prefix}rep set 70 Гильдия`",
            "info": "Устанавливает у гильдии указанную репутацию",
            "log": "Установлено"
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
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

    elif value is None or text_data is None:
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
            color = mmorpg_col("vinous")
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
        
        if result is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = (
                    f"На сервере нет гильдий с названием **{guild_name}**\n"
                    f"Список гильдий: `{prefix}guilds`"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        else:
            mr_id = get_field(result, "master_role_id")
            rep_logs = get_field(result, "rep_logs", default=[])
            
            if not has_roles(ctx.author, [mr_id]) and not has_permissions(ctx.author, ["administrator"]):
                reply = discord.Embed(
                    title = "❌ Недостаточно прав",
                    description = (
                        "**Нужно быть одним из них:**\n"
                        "> Администратор\n"
                        "> Мастер гильдий"
                    ),
                    color = mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            else:
                log = {
                    "guild": guild_name,
                    "changer_id": ctx.author.id,
                    "reason": text,
                    "action": params[param]["log"],
                    "value": int(value)
                }
                rep_logs.append(log)
                lll = len(rep_logs)
                if lll > 10:
                    rep_logs = rep_logs[lll-10:lll]
                
                if param == "change":
                    to_update = {
                        "$inc": {"subguilds.$.reputation": int(value)},
                        "$set": {"rep_logs": rep_logs}
                    }
                elif param == "set":
                    to_update = {
                        "$set": {"subguilds.$.reputation": int(value),
                        "rep_logs": rep_logs}
                    }
                
                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    to_update,
                    upsert=True
                )

                reply = discord.Embed(
                    title = "✅ Выполнено",
                    description = f"Репутация гильдии изменена.\nПрофиль: `{prefix}guild-info {guild_name}`",
                    color = mmorpg_col("clover")
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
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        log_emb = discord.Embed(
            title = "🛠 Последние 10 действий",
            color = mmorpg_col("lilac")
        )
        for log in rep_logs:
            user = client.get_user(log["changer_id"])
            desc = (
                f"Модератор: {anf(user)}\n"
                f"{log['action']} на **{log['value']}** 🔅\n"
                f"Причина: {log['reason']}"
            )
            log_emb.add_field(name=f"💠 **Гильдия:** {log['guild']}", value=desc, inline = False)
        await ctx.send(embed=log_emb)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["create-guild", "createguild", "cg"])
async def create_guild(ctx, *, guild_name):
    collection = db["subguilds"]
    guild_name = exclude(["[", "]"], guild_name[:+30])

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
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        total_guilds = 0
        if result != None and "subguilds" in result:
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
                    color = mmorpg_col("clover")
                )
                reply.set_thumbnail(url = default_avatar_url)
                await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["edit-guild", "editguild", "eg", "edit"])
async def edit_guild(ctx, param, *, text_data = None):
    p = ctx.prefix
    collection = db["subguilds"]
    parameters = {
        "name": ["название"],
        "description": ["описание"],
        "avatar_url": ["аватарка"],
        "leader_id": ["глава", "owner"],
        "helper_id": ["помощник", "заместитель"],
        "role_id": ["роль"],
        "private": ["приватность", "privacy"]
    }
    parameter = find_alias(parameters, param)

    if parameter is None:
        reply = discord.Embed(
            title = "❓ Доступные параметры настроек",
            description = (
                "> `name`\n"
                "> `description`\n"
                "> `avatar`\n"
                "> `leader`\n"
                "> `helper`\n"
                "> `role`\n"
                "> `privacy`\n"
                f"**Подробнее:** `{p}{ctx.command.name}`\n"
                f'**Использование:** `{p}{ctx.command.name} Параметр [Название гильдии] Новое значение`\n'
                f'**Пример:** `{p}{ctx.command.name} name [Моя гильдия] Хранители`\n'
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        if text_data is None:
            reply = discord.Embed(
                title = f"🛠 Использование {p}edit-guild {param}",
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

        if result is None:
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"Гильдии с названием **{guild_name}** нет на сервере",
                color = mmorpg_col("vinous")
            )
            await ctx.send(embed = reply)
        
        else:
            subguild = get_subguild(result, guild_name)
            leader_id = subguild["leader_id"]
            mr_id = get_field(result, "master_role_id")

            if ctx.author.id != leader_id and not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]):
                reply = discord.Embed(
                    title = "❌ Недостаточно прав",
                    description = (
                        f"Нужно быть одним из них:\n"
                        f"> Глава гильдии {guild_name}\n"
                        "> Мастер гильдий\n"
                        "> Администратор"
                    ),
                    color = mmorpg_col("vinous")
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
                            description = f"Гильдия с названием {anf(value)} уже есть",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                elif parameter in ["leader_id", "helper_id"]:
                    value = detect.member(ctx.guild, text)

                    if text.lower() == "delete":
                        value = None

                    elif value is None:
                        correct_arg = False

                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Вы ввели {text}, подразумевая участника, но он не был найден",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                    elif value.id == leader_id:
                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"{anf(value)} является главой этой гильдии.",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                    else:
                        value = value.id
                    
                elif parameter == "role_id":
                    value = detect.role(ctx.guild, text)
                    if text.lower() == "delete":
                        value = None
                    elif value is None:
                        correct_arg = False

                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Вы ввели {text}, подразумевая роль, но она не была найдена",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                    elif role_gte(value, ctx.author) or not has_permissions(ctx.author, ["manage_roles"]):
                        correct_arg = False

                        reply = discord.Embed(
                            title = "💢 Недостаточно прав",
                            description = f"Роль <@&{value.id}> не ниже Вашей или у Вас нет прав на управление ролями.",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)
                    
                    elif role_gte(value, ctx.guild.me) or not has_permissions(ctx.guild.me, ["manage_roles"]):
                        correct_arg = False

                        reply = discord.Embed(
                            title = "⚠ У меня нет прав",
                            description = f"Роль <@&{value.id}> не ниже моей или у меня нет прав на управление ролями.",
                            color = discord.Color.gold()
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                    else:
                        value = value.id

                elif parameter == "avatar_url":
                    correct_arg = image_link(text)
                    if not correct_arg:
                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Не удаётся найти картинку по ссылке {text}",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

                elif parameter == "private":
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
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)
                
                if correct_arg:
                    subguild[parameter] = value

                    collection.find_one_and_update(
                        {"_id": ctx.guild.id, "subguilds.name": guild_name},
                        {"$set": {f"subguilds.$.{parameter}": value}},
                        upsert=True
                    )

                    reply = discord.Embed(
                        title = "✅ Настроено",
                        description = f"**->** Профиль гильдии: `{prefix}guild-info {subguild['name']}`",
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
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

    if result is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{prefix}guilds`"
            ),
            color = mmorpg_col("vinous")
        )
        await ctx.send(embed = reply)
    else:
        mr_id = get_field(result, "master_role_id")
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
                color = mmorpg_col("vinous")
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
                description = f"Вы удалили гильдию **{guild_name}**"
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
    
    if result is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"На сервере нет гильдии с названием **{guild_name}**"
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        mr_id = get_field(result, "master_role_id")
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
                color = mmorpg_col("vinous")
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

        elif carve_int(page) is None:
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
                member = ctx.guild.get_member(ID)
                if member is None:
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
                    color = mmorpg_col("paper")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                desc = ""
                last_num = min(first_num + interval, length)
                for i in range(first_num, last_num):
                    if req_list != None:
                        desc += f"**{i + 1})** {anf(req_list[i])}\n"

                reply = discord.Embed(
                    title = "Запросы на вступление",
                    description = (
                        f"**В гильдию:** {anf(guild_name)}\n"
                        f"**Принять запрос:** `{prefix}accept Номер_запроса {guild_name}`\n"
                        f"**Отклонить запрос:** `{prefix}decline Номер_запроса {guild_name}`\n\n"
                        f"{desc}"
                    ),
                    color = mmorpg_col("lilac")
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
    if result is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"На сервере нет гильдии с названием **{guild_name}**"
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        mr_id = get_field(result, "master_role_id")
        subguild = get_subguild(result, guild_name)
        del result

        id_list = []
        to_pull = []
        for ID in subguild["requests"]:
            member = ctx.guild.get_member(ID)
            if member is None:
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
                color = mmorpg_col("vinous")
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
        
        elif carve_int(num) is None:
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
                new_data.update([(f"subguilds.$.members.{ID}", {"messages": 0}) for ID in id_list])

                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {
                        "$pull": {"subguilds.$.requests": {"$in": subguild["requests"]}},
                        "$set": new_data
                    }
                )
                desc = "Все заявки приняты"
                for ID in id_list:
                    client.loop.create_task(give_join_role(ctx.guild.get_member(ID), subguild["role_id"]))
                
            else:
                user_id = id_list[num-1]
                to_pull.append(user_id)

                collection.find_one_and_update(
                    {"_id": ctx.guild.id, "subguilds.name": guild_name},
                    {
                        "$pull": {"subguilds.$.requests": {"$in": to_pull}},
                        "$set": {f"subguilds.$.members.{user_id}": {"messages": 0}}
                    }
                )
                member = ctx.guild.get_member(user_id)
                desc = f"Заявка {anf(member)} принята"

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
    if result is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"На сервере нет гильдии с названием **{guild_name}**"
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        mr_id = get_field(result, "master_role_id")
        subguild = get_subguild(result, guild_name)
        del result

        id_list = []
        to_pull = []
        for ID in subguild["requests"]:
            member = ctx.guild.get_member(ID)
            if member is None:
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
                color = mmorpg_col("vinous")
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
        
        elif carve_int(num) is None:
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
                member = ctx.guild.get_member(user_id)
                desc = f"Заявка {anf(member)} отклонена"
            
            reply = discord.Embed(
                title = "🛠 Выполнено",
                description = desc
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command()
async def kick(ctx, parameter, value = None, *, guild_name = None):
    param_aliases = {
        "user": ["участник", "member", "пользователь"],
        "under": ["lower", "ниже"],
        "last": ["последние"]
    }

    params = {
        "user": {
            "usage": f"`{prefix}kick user @Участник Гильдия`",
            "example": f"`{prefix}kick user @Участник Моя Гильдия`",
            "info": "Кикнуть конкретного участника"
        },
        "under": {
            "usage": f"`{prefix}kick under Планка_опыта Гильдия`",
            "example": f"`{prefix}kick under 500 Моя Гильдия`",
            "info": "Кикнуть тех, у кого кол-во опыта меньше заданной планки"
        },
        "last": {
            "usage": f"`{prefix}kick last Кол-во Гильдия`",
            "example": f"`{prefix}kick last 10 Моя гильдия`",
            "info": "Кикнуть сколько-то последних участников"
        }
    }
    parameter = find_alias(param_aliases, parameter)
    if parameter is None:
        desc = ""
        for param in params:
            desc += f"> `{param}`\n"
        reply = discord.Embed(
            title = "❌ Неверный параметр",
            description = f"Вы ввели: `{parameter}`\nДоступные параметры:\n{desc}",
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    elif value is None or guild_name is None:
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
        if result is None:
            reply = discord.Embed(
                title = "❌ Гильдия не найдена",
                description = f"На сервере нет гильдии с названием **{guild_name}**",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            mr_id = get_field(result, "master_role_id")
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
                    color = mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            elif parameter == "user":
                user = detect.member(ctx.guild, value)
                if user is None:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = f"Вы ввели {value}, подразумевая участника, но он не был найден",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                elif user.id == subguild["leader_id"]:
                    desc = "Вы не можете кикнуть главу гильдии"
                    if user.id == ctx.author.id:
                        desc = "Вы не можете кикнуть самого себя"
                    reply = discord.Embed(
                        title = "❌ Ошибка",
                        description = desc,
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                else:
                    collection.find_one_and_update(
                        {"_id": ctx.guild.id, "subguilds.name": guild_name},
                        {"$unset": {f"subguilds.$.members.{user.id}": ""}}
                    )
                    reply = discord.Embed(
                        title = "✅ Выполнено",
                        description = f"{anf(user)} был исключён из гильдии **{guild_name}**",
                        color = mmorpg_col("clover")
                    )
                await remove_join_role(user, subguild["role_id"])
                await ctx.send(embed = reply)
            
            elif parameter == "under":
                if not value.isdigit() or "-" in value:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = f"Планка сообщений должна быть целым положительным числом\nВы ввели: {value}",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                else:
                    value = int(value)

                    memb_data = subguild["members"]
                    holder = []
                    for key in memb_data:
                        memb = memb_data[key]
                        user_id = int(key)
                        if memb["messages"] <= value and user_id != subguild["leader_id"]:
                            holder.append(user_id)
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
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")

                    if subguild["role_id"] != None:
                        for ID in holder:
                            client.loop.create_task(remove_join_role(ctx.guild.get_member(ID), subguild["role_id"]))
                
                await ctx.send(embed = reply)

            elif parameter == "last":
                if not value.isdigit() or "-" in value:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = f"Кол-во участников должно быть целым положительным числом\nВы ввели: {value}",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                else:
                    value = int(value)

                    memb_data = subguild["members"]
                    pairs = []
                    for key in memb_data:
                        memb = memb_data[key]
                        user_id = int(key)
                        if user_id != subguild["leader_id"]:
                            pairs.append((user_id, memb["messages"]))
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
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")

                    if subguild["role_id"] != None:
                        for pair in pairs:
                            ID = pair[0]
                            client.loop.create_task(remove_join_role(ctx.guild.get_member(ID), subguild["role_id"]))
                
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
            color = mmorpg_col("vinous")
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
            color = mmorpg_col("clover")
        )

    elif user is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"Вы ввели {u_search}, подразумевая участника, но он не был найден",
            color = mmorpg_col("vinous")
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
            color = mmorpg_col("clover")
        )
    await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["reset-guilds", "resetguilds", "rg", "reset-guild", "resetguild"])
async def reset_guilds(ctx, parameter):
    collection = db["subguilds"]
    params = {
        "exp": ["xp", "опыт"],
        "mentions": ["pings", "упоминания", "теги"],
        "reputation": ["репутация"]
    }
    parameter = find_alias(params, parameter)

    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "❌ Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
    
    elif parameter is None:
        reply = discord.Embed(
            title = "💢 Неверный параметр",
            description = (
                "Доступные параметры:\n"
                "> `exp`\n"
                "> `mentions`\n"
                "> `reputation`\n"
                f"Например `{prefix}reset-guilds exp`"
            ),
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")

    else:
        if parameter != "exp":
            value = 0
            if parameter == "reputation":
                value = 100
            
            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {
                    "$set": {f"subguilds.$[].{parameter}": value}
                }
            )
        elif parameter == "exp":
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
            description = "Сброс закончен",
            color = mmorpg_col("clover")
        )
    
    await ctx.send(embed = reply)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["count-roles", "countroles", "cr"])
async def count_roles(ctx, *, text_data):
    collection = db["subguilds"]

    guild_name, text = sep_args(text_data)
    raw_roles = text.split()
    
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
    if result is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"На сервере нет гильдии с названием **{guild_name}**",
            color = mmorpg_col("vinous")
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
                color = mmorpg_col("vinous")
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
                    user_id = int(key)
                    member = ctx.guild.get_member(user_id)
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
                    color = mmorpg_col("paper")
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
    if result is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{prefix}guilds`"
            ),
            color = mmorpg_col("vinous")
        )
        await ctx.send(embed = reply)
    else:
        m_lim = get_field(result, "member_limit", default=member_limit)

        subguild = get_subguild(result, guild_name)
        guild_role_id = subguild["role_id"]
        private = subguild["private"]
        total_memb = len(subguild["members"])

        if total_memb >= m_lim:
            reply = discord.Embed(
                title = "🛠 Гильдия переполнена",
                description = f"В этой гильдии достигнут максимум участников - {m_lim}",
                color = mmorpg_col("paper")
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
                    color = mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            elif user_guild != None:
                reply = discord.Embed(
                    title = "🛠 О смене гильдий",
                    description = (
                        f"В данный момент Вы являетесь членом гильдии **{user_guild}**.\n"
                        f"Для того, чтобы войти в другую гильдию, Вам нужно выйти из текущей, однако, **не забывайте**:\n"
                        f"**->** Ваш счётчик опыта обнуляется при выходе.\n"
                        f"Команда для выхода: `{prefix}leave-guild`"
                    )
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
                        color = mmorpg_col("paper")
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
                        color = mmorpg_col("clover")
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
            f"subguilds.members.{ctx.author.id}": {"$exists": True}
        },
        projection={"subguilds.name": True, "subguilds.members": True, "subguilds.role_id": True}
    )
    if result is None:
        reply = discord.Embed(
            title = "❌ Ошибка",
            description = f"Вас нет ни в одной гильдии",
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        subguild = get_subguild(result, ctx.author.id)
        guild_name = subguild["name"]
        guild_role_id = subguild["role_id"]
        del result

        no = ["no", "0", "нет"]
        yes = ["yes", "1", "да"]

        warn_emb = discord.Embed(
            title = "🛠 Подтверждение",
            description = (
                f"**->** Ваш счётчик опыта обнулится, как только Вы покинете гильдию **{guild_name}**.\nПродолжить?\n"
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

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["guilds"])
async def top(ctx, filtration = "exp", *, extra = "пустую строку"):
    collection = db["subguilds"]
    filters = {
        "exp": "✨",
        "mentions": "📯",
        "members": "👥",
        "roles": "🎗",
        "reputation": "🔅",
        "rating": "🏆"
    }
    filter_aliases = {
        "exp": ["xp", "опыт"],
        "mentions": ["упоминания", "теги", "pings"],
        "members": ["участников", "численности"],
        "roles": ["роли"],
        "reputation": ["репутация"],
        "rating": ["mixed", "рейтинг"]
    }
    filtration = find_alias(filter_aliases, filtration)

    result = collection.find_one({"_id": ctx.guild.id})
    role = detect.role(ctx.guild, extra)

    if filtration is None:
        reply = discord.Embed(
            title = "❓ Фильтры топа",
            description = (
                "> `exp`\n"
                "> `mentions`\n"
                "> `members`\n"
                "> `reputation`\n"
                "> `rating`\n"
                "> `roles`\n"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

    elif filtration == "roles" and role is None:
        reply = discord.Embed(
            title = "💢 Ошибка",
            description = f"Вы ввели {extra}, подразумевая роль, но она не была найдена",
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

    elif result is None or not "subguilds" in result:
        lb = discord.Embed(
            title = f"⚔ Гильдии сервера {ctx.guild.name}",
            description = "Отсутствуют",
            color = mmorpg_col("pancake")
        )
        lb.set_thumbnail(url = f"{ctx.guild.icon_url}")
        await ctx.send(embed = lb)
    else:
        subguilds = result["subguilds"]

        stats = []

        if filtration == "rating":
            desc = "Фильтрация одновременно **по опыту и репутации** - рейтинг гильдий"

            total_mes = 0
            total_rep = 0
            for sg in subguilds:
                total_rep += sg["reputation"]
                guild_mes = 0
                for key in sg["members"]:
                    guild_mes += sg["members"][key]["messages"]
                total_mes += guild_mes
                stats.append((sg["name"], sg["reputation"], guild_mes))

            if total_rep <= 0:
                total_rep = 1
            transfer_weight = total_mes / total_rep

            stats = [(pair[0], pair[1] + round(pair[2] / transfer_weight)) for pair in stats]
        
        else:
            for subguild in subguilds:
                if filtration == "exp":
                    desc = "Фильтрация **по количеству опыта**"
                    total = 0
                    for str_id in subguild["members"]:
                        memb = subguild["members"][str_id]
                        total += memb["messages"]
                elif filtration == "roles":
                    desc = f"Фильтрация **по количеству участников, имеющих роль <@&{role.id}>**"
                    total = 0
                    for key in subguild["members"]:
                        memb = subguild["members"][key]
                        user_id = int(key)
                        member = ctx.guild.get_member(user_id)
                        if member != None and role in member.roles:
                            total += 1
                elif filtration == "mentions":
                    desc = "Фильтрация **по количеству упоминаний**"
                    total = subguild["mentions"]
                elif filtration == "members":
                    desc = "Фильтрация **по количеству участников**"
                    total = len(subguild["members"])
                elif filtration == "reputation":
                    desc = "Фильтрация **по репутации**"
                    total = subguild["reputation"]

                pair = (f"{subguild['name']}", total)
                stats.append(pair)
        
        del result
        stats.sort(key=lambda i: i[1], reverse=True)

        table = ""
        for i in range(len(stats)):
            guild_name = anf(stats[i][0])
            total = stats[i][1]
            table += f"**{i+1})** {guild_name} • **{total}** {filters[filtration]}\n"
        
        lb = discord.Embed(
            title = f"⚔ Гильдии сервера {ctx.guild.name}",
            description = (
                f"{desc}\n"
                f"Подробнее о гильдии: `{prefix}guild-info Название`\n"
                f"Вступить в гильдию: `{prefix}join-guild Название`\n\n"
                f"{table}"
            ),
            color = mmorpg_col("pancake")
        )
        lb.set_thumbnail(url = f"{ctx.guild.icon_url}")
        await ctx.send(embed = lb)

@commands.cooldown(1, 10, commands.BucketType.member)
@client.command(aliases = ["global-top", "globaltop", "glt"])
async def global_top(ctx, page="1"):
    collection = db["subguilds"]
    interval = 15

    if not page.isdigit():
        reply = discord.Embed(
            title = "💢 Ошибка",
            description = f"Входной аргумент {page} должен быть целым числом",
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed=reply)
    
    else:
        page = int(page)
        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={"subguilds.members": True}
        )

        pairs = []
        if result != None and "subguilds" in result:
            for sg in result["subguilds"]:
                for key in sg["members"]:
                    memb = sg["members"][key]
                    user_id = int(key)
                    pairs.append((user_id, memb["messages"]))
        pairs.sort(key=lambda i: i[1], reverse=True)

        length = len(pairs)
        total_pages = (length-1) // interval + 1
        if page > total_pages:
            reply = discord.Embed(
                title = "💢 Упс",
                description = f"Страница не найдена. Всего страниц: **{total_pages}**",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)
        
        else:
            place = None
            for i in range(length):
                if pairs[i][0] == ctx.author.id:
                    place = i
                    break
            if place is None:
                auth_desc = "Вас нет в этом топе, так как Вы не состоите ни в одной гильдии"
            else:
                auth_desc = f"Ваше место в топе: **{place+1} / {length}**"
            
            first_num = interval * (page-1)
            last_num = min(length, interval * page)

            desc = ""
            for i in range(first_num, last_num):
                user = ctx.guild.get_member(pairs[i][0])
                desc += f"**{i+1})** {anf(user)} • **{pairs[i][1]}** ✨\n"
            
            reply = discord.Embed(
                title = f"🌐 Топ всех участников гильдий сервера\n{ctx.guild.name}",
                description = f"{auth_desc}\n\n{desc}",
                color = mmorpg_col("sky")
            )
            reply.set_thumbnail(url = f"{ctx.guild.icon_url}")
            reply.set_footer(text=f"Стр. {page}/{total_pages} | {ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["guild-info", "guildinfo", "gi"])
async def guild_info(ctx, *, guild_name = None):
    collection = db["subguilds"]

    result = collection.find_one({"_id": ctx.guild.id})
    if guild_name is None:
        subguild = get_subguild(result, ctx.author.id)
        error_text = (
            "Вас нет в какой-либо гильдии, однако, можно посмотреть профиль конкретной гильдии:\n"
            f"`{prefix}guild-info Название гильдии`\n"
            f"Список гильдий: `{prefix}top`"
        )
    else:
        subguild = get_subguild(result, guild_name)
        error_text = (
            f"На сервере нет гильдий с названием **{guild_name}**\n"
            f"Список гильдий: `{prefix}top`"
        )
    del result
        
    if subguild is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = error_text,
            color = mmorpg_col("vinous")
        )
        reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:

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
                f"**->** Топ участников: `{prefix}guild-top 1 {subguild['name']}`"
            ),
            color = mmorpg_col("sky")
        )
        reply.set_thumbnail(url = subguild["avatar_url"])
        if subguild['leader_id'] != None:
            leader = client.get_user(subguild["leader_id"])
            reply.add_field(name = "💠 Владелец", value = f"> {anf(leader)}", inline=False)
        if subguild['helper_id'] != None:
            helper = client.get_user(subguild["helper_id"])
            reply.add_field(name = "🔰 Помощник", value = f"> {anf(helper)}", inline=False)
        reply.add_field(name = "👥 Всего участников", value = f"> {total_memb}", inline=False)
        reply.add_field(name = "✨ Всего опыта", value = f"> {total_mes}", inline=False)
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
async def guild_members(ctx, page_num="1", *, guild_name = None):
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
            {"_id": ctx.guild.id},
            projection={
                "subguilds.name": True,
                "subguilds.members": True,
                "subguilds.avatar_url": True
            }
        )
        if guild_name is None:
            subguild = get_subguild(result, ctx.author.id)
            error_text = (
                "Вас нет в какой-либо гильдии, но Вы можете посмотреть топ конкретной гильдии:\n"
                f"`{prefix}guild-top Страница Название гильдии`"
            )
        else:
            subguild = get_subguild(result, guild_name)
            error_text = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{prefix}top`"
            )
        del result

        if subguild is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = error_text,
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:

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
                    user_id = int(key)
                    pairs.append((user_id, member["messages"]))
                pairs.sort(key=lambda i: i[1], reverse=True)

                last_num = min(total_memb, interval*page_num)
                
                desc = ""
                for i in range(interval*(page_num-1), last_num):
                    pair = pairs[i]
                    user = ctx.guild.get_member(pair[0])
                    desc += f"**{i + 1})** {anf(user)} • **{pair[1]}** ✨\n"
                
                lb = discord.Embed(
                    title = f"👥 Участники гильдии {subguild['name']}",
                    description = desc,
                    color = mmorpg_col("clover")
                )
                lb.set_footer(text=f"Стр. {page_num}/{(total_memb - 1)//interval + 1}")
                lb.set_thumbnail(url = subguild["avatar_url"])
                await ctx.send(embed = lb)

@commands.cooldown(1, 5, commands.BucketType.member)
@client.command(aliases = ["user-guild", "userguild", "ug", "user-info", "userinfo", "ui"])
async def user_guild(ctx, user_s = None):
    if user_s is None:
        user = ctx.author
    else:
        user = detect.member(ctx.guild, user_s)
    if user is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = f"Вы ввели {user_s}, подразумевая участника, но он не был найден",
        )
        await ctx.send(embed = reply)
    else:
        collection = db["subguilds"]
        result = collection.find_one(
            {"_id": ctx.guild.id, f"subguilds.members.{user.id}": {"$exists": True}},
            projection={"subguilds.requests": False}
        )
        if result is None:
            heading = "🛠 Пользователь не в гильдии"
            if user_s is None:
                heading = "🛠 Вы не в гильдии"
            reply = discord.Embed(
                title = heading,
                description = f"Вы можете посмотреть список гильдий здесь: `{prefix}guilds`",
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            subguild = get_subguild(result, user.id)
            del result

            user_mes = subguild["members"][f"{user.id}"]["messages"]
            pairs = [(int(ID), subguild["members"][ID]["messages"]) for ID in subguild["members"]]
            subguild["members"] = {}
            pairs.sort(key=lambda i: i[1], reverse=True)

            place = pairs.index((user.id, user_mes)) + 1

            stat_emb = discord.Embed(color = mmorpg_col("paper"))
            stat_emb.add_field(name="🛡 Гильдия", value=anf(subguild['name']), inline = False)
            stat_emb.add_field(name="✨ Заработано опыта", value=f"{user_mes}", inline = False)
            stat_emb.add_field(name="🏅 Место", value=f"{place} / {len(pairs)}", inline = False)
            stat_emb.set_author(name = f"Профиль 🔎 {user}", icon_url = f"{user.avatar_url}")
            stat_emb.set_thumbnail(url = subguild["avatar_url"])
            await ctx.send(embed = stat_emb)

#======== Events ========
@client.event
async def on_message(message):
    # If not direct message
    if message.guild != None:
        collection = None
        user_id = message.author.id
        server_id = message.guild.id
        channel_id = message.channel.id
        mentioned_members = message.mentions

        if not message.author.bot:
            # Check if command and process command

            mes_content = message.content.strip(prefix)
            words = mes_content.split(maxsplit=1)

            first_word = None
            if len(words) > 0:
                first_word = words[0]

            if is_command(first_word):
                collection = db["cmd_channels"]
                result = collection.find_one({"_id": server_id})

                if result is None:
                    wl_channels = [channel_id]
                elif result["channels"] is None:
                    wl_channels = [channel_id]
                else:
                    wl_channels = result["channels"]
                    server_channel_ids = [c.id for c in message.guild.channels]

                    total_not_exist = 0
                    for wl_channel_id in wl_channels:
                        if wl_channel_id not in server_channel_ids:
                            total_not_exist += 1
                    
                    if total_not_exist >= len(wl_channels):
                        wl_channels = [channel_id]
                
                if channel_id in wl_channels:
                    await client.process_commands(message)
                
                else:
                    reply = discord.Embed(
                        title="⚠ Лимит",
                        description="Пожалуйста, используйте команды в другом канале.",
                        color=discord.Color.gold()
                    )
                    reply.set_footer(text = f"{message.author}", icon_url=f"{message.author.avatar_url}")
                    await message.channel.send(embed=reply)

            # Check cooldown and calculate income
            collection = db["subguilds"]
            global exp_buffer

            now = datetime.datetime.utcnow()

            _5_min = datetime.timedelta(seconds=300)
            if now - exp_buffer["last_clean"] >= _5_min:
                exp_buffer = {"last_clean": now}

            if not server_id in exp_buffer:
                exp_buffer.update([(server_id, {})])
            
            passed_cd = False
            if not user_id in exp_buffer[server_id]:
                exp_buffer[server_id].update([(user_id, now)])
                passed_cd = True
            else:
                past = exp_buffer[server_id][user_id]
                _10_sec = datetime.timedelta(seconds=10)

                if now - past >= _10_sec:
                    passed_cd = True
                    exp_buffer[server_id][user_id] = now
            
            if passed_cd:
                result = collection.find_one(
                    {
                        "_id": server_id,
                        f"subguilds.members.{user_id}": {"$exists": True}
                    },
                    projection={
                        "subguilds.name": True,
                        "subguilds.members": True
                    }
                )
                if result != None and "subguilds" in result:
                    sg_found = False
                    sg_name = None
                    S, M = -1, -1
                    for sg in result["subguilds"]:
                        total_mes = 0
                        total_memb = 0
                        for key in sg["members"]:
                            memb = sg["members"][key]

                            if not sg_found and f"{user_id}" == key:
                                sg_found = True
                                sg_name = "temporary"
                            
                            total_mes += memb["messages"]
                            total_memb += 1
                        
                        if total_mes > S:
                            S, M = total_mes, total_memb
                        if sg_name != None and sg_found:
                            sg_name = None
                            Si, Mi = total_mes, total_memb
                        
                    if sg_found:
                        income = round(10 * (((M+10) / (Mi+10))**(1/4) * ((S+10) / (Si+10))**(1/2)))

                        collection.find_one_and_update(
                            {
                                "_id": server_id,
                                f"subguilds.members.{user_id}": {"$exists": True}
                            },
                            {"$inc": {f"subguilds.$.members.{user_id}.messages": income}}
                        )
        
        # Award with mentions
        if mentioned_members != []:
            if collection is None:
                collection = db["subguilds"]

            search = {
                "_id": server_id,
                "mentioner_id": user_id
            }
            key_words = [f"subguilds.members.{m.id}" for m in mentioned_members]
            search.update([(kw, {"$exists": True}) for kw in key_words])
            del mentioned_members
            
            proj = {"subguilds.name": True}
            proj.update([(kw, True) for kw in key_words])

            result = collection.find_one(
                search,
                projection=proj
            )
            
            if result != None and "subguilds" in result:
                subguilds = result["subguilds"]
                for sg in subguilds:
                    if sg["members"] != {}:
                        collection.find_one_and_update(
                            {"_id": server_id, "subguilds.name": sg["name"]},
                            {"$inc": {"subguilds.$.mentions": len(sg["members"])}}
                        )

#======== Errors ==========
# Cooldown
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

# Missing arguments
@create_guild.error
async def create_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** создаёт гильдию\n"
                f"**Использование:** `{p}{cmd} Название гильдии`\n"
                f"**Пример:** `{p}{cmd} Короли`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@edit_guild.error
async def edit_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** настраивает гильдию\n"
                "**Параметры:**\n"
                "> `name`\n"
                "> `description`\n"
                "> `avatar`\n"
                "> `leader`\n"
                "> `helper`\n"
                "> `role`\n"
                "> `privacy`\n"
                f'**Использование:** `{p}{cmd} Параметр [Название гильдии] Новое значение`\n'
                f'**Пример:** `{p}{cmd} name [Цари Горы] Хранители`\n'
                f'**Подробнее о параметрах:**\n'
                f"`{p}{cmd} name`\n"
                f"`{p}{cmd} description`\n"
                f"`{p}{cmd} ...`\n"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@join_guild.error
async def join_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** вход в гильдию\n"
                f"**Использование:** `{p}{cmd} Название гильдии`\n"
                f"**Пример:** `{p}{cmd} Короли`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@delete_guild.error
async def delete_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** удаляет гильдию\n"
                f"**Использование:** `{p}{cmd} Название гильдии`\n"
                f"**Пример:** `{p}{cmd} Короли`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

# @guild_members.error
# async def guild_members_error(ctx, error):
#     if isinstance(error, commands.MissingRequiredArgument):
#         p = ctx.prefix
#         cmd = ctx.command
#         reply = discord.Embed(
#             title = f"❓ Об аргументах `{p}{cmd}`",
#             description = (
#                 f'**Использование:** `{prefix}{ctx.command.name} Номер_страницы Название гильдии`'
#             )
#         )
#         reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
#         await ctx.send(embed = reply)

@ping_count.error
async def ping_count_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** настраивает пользователя, упоминания которым нужно учитывать в статистике гильдий\n"
                f"**Использование:** `{p}{cmd} @Пользователь`\n"
                f"**Пример:** `{p}{cmd} @MEE6#4876`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@reset_guilds.error
async def reset_guilds_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** обнуляет топ по указанному фильтру\n"
                "**Использование:**\n"
                f"> `{p}{cmd} exp` - по опыту\n"
                f"> `{p}{cmd} reputation - по репутации`\n"
                f"> `{p}{cmd} mentions` - по упоминаниям"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@count_roles.error
async def count_roles_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** подсчитать кол-во перечисленных ролей в существующих гильдиях\n"
                f"**Использование:** `{p}{cmd} [Гильдия] @роль1 @роль2 ...`\n"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@cmd_channels.error
async def cmd_channels_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** настраивает каналы реагирования на команды\n"
                f'**Использование:** `{p}{cmd} #канал-1 #канал-2 ...`\n'
                f"**Сброс:** `{p}{cmd} delete`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@requests.error
async def requests_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** просмотр списка заявок на вступление в какую-либо гильдию\n"
                f'**Использование:** `{p}{cmd} Страница Гильдия`\n'
                f"**Пример:** `{p}{cmd} 1 Короли`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@accept.error
async def accept_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** принять заявку на вступление\n"
                f'**Использование:** `{p}{cmd} Номер_заявки Гильдия`\n'
                f"**Примеры:** `{p}{cmd} 1 Короли`\n"
                f">> `{p}{cmd} all Короли`\n"
                f"**Список заявок:** `{prefix}requests Страница Гильдия`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@decline.error
async def decline_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** отклонить заявку на вступление\n"
                f'**Использование:** `{p}{cmd} Номер_заявки Гильдия`\n'
                f"**Примеры:** `{p}{cmd} 1 Короли`\n"
                f">> `{p}{cmd} all Короли`\n"
                f"**Список заявок:** `{prefix}requests Страница Гильдия`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** исключает участника(ов) из гильдии\n"
                f"**Подкоманды:**\n"
                f"> `{p}{cmd} user`\n"
                f"> `{p}{cmd} under`\n"
                f"> `{p}{cmd} last`\n"
                "Введите одну из команд для подробностей"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@reputation.error
async def reputation_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** изменяет репутацию гильдии\n"
                f"**Подкоманды:**\n"
                f"> `{p}{cmd} change`\n"
                f"> `{p}{cmd} set`\n"
                f"**Примеры:** `{p}{cmd} change -10 Короли Участник был наказан`\n"
                f">> `{p}{cmd} set 100 Короли Начнём с чистого листа`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@members_limit.error
async def members_limit_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** устанавливает лимит участников во всех гильдиях\n"
                f'**Использование:** `{p}{cmd} Число`\n'
                f"**Пример:** `{p}{cmd} 50`\n"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

async def change_status():
    await client.wait_until_ready()
    await client.change_presence(activity=discord.Game(f"{prefix}help"))
client.loop.create_task(change_status())

client.run(token)
