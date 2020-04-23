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

statuses = {
    "dnd": discord.Status.dnd,
    "idle": discord.Status.idle,
    "online": discord.Status.online,
    "invisible": discord.Status.invisible
}

exp_buffer = {"last_clean": datetime.datetime.utcnow()}

from functions import guild_limit, member_limit, owner_ids

#======== Functions ========
from functions import get_field, find_alias, has_permissions

def is_command(word):
    out = False
    for cmd in client.commands:
        group = cmd.aliases
        group.append(cmd.name)
        if word in group:
            out = True
            break
    return out

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

#======== Events =========

@client.event
async def on_ready():
    print(
        ">> Bot is ready\n"
        f">> Prefix is {prefix}\n"
        f">> Bot user: {client.user}\n"
        ">> Loading Cogs...\n"
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

@client.command()
async def status(ctx, *, text):
    if ctx.author.id in owner_ids:
        if "||" in text:
            status_text, str_activity = text.split("||", maxsplit=1)
        else:
            status_text, str_activity = text, None
        
        client.loop.create_task(change_status(status_text, str_activity))

        reply = discord.Embed(
            title="📝 Статуст изменён",
            description=f"**Текст:** {status_text}",
            color=mmorpg_col("clover")
        )
        await ctx.send(embed=reply)

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
                if has_permissions(message.author, ["administrator"]):
                    await client.process_commands(message)
                else:
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
                            title="⚠ Канал",
                            description="Пожалуйста, используйте команды в другом канале.",
                            color=discord.Color.gold()
                        )
                        reply.set_footer(text = f"{message.author}", icon_url=f"{message.author.avatar_url}")
                        await message.channel.send(embed=reply)

            else:
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

async def change_status(status_text, str_activity):
    await client.wait_until_ready()
    await client.change_presence(
        activity=discord.Game(status_text),
        status=get_field(statuses, str_activity)
    )
client.loop.create_task(change_status(f"{prefix}help", "idle"))

#--------- Loading Cogs ---------

for file_name in os.listdir("./cogs"):
    if file_name.endswith(".py"):
        client.load_extension(f"cogs.{file_name[:-3]}")

client.run(token)