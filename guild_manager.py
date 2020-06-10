import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import os, json, datetime
from xlsxwriter import Workbook

import pymongo
from pymongo import MongoClient
app_string = str(os.environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

default_prefix = "."

async def get_prefix(client, message):
    collection = db["cmd_channels"]
    result = collection.find_one(
        {"_id": message.guild.id}
    )
    prefix = get_field(result, "prefix", default=default_prefix)
    if is_command(message.content, prefix, client):
        cmd_channels_ids = get_field(result, "channels")
        if cmd_channels_ids is None:
            cmd_channels_ids = [message.channel.id]
        else:
            server_channel_ids = [c.id for c in message.guild.text_channels]
            channels_exist = False
            for _id in cmd_channels_ids:
                if _id in server_channel_ids:
                    channels_exist = True
                    break
            if not channels_exist:
                cmd_channels_ids = [message.channel.id]

        if message.channel.id not in cmd_channels_ids and not has_permissions(message.author, ["administrator"]):
            reply = discord.Embed(
                title="⚠ Канал",
                description="Пожалуйста, используйте команды в другом канале.",
                color=discord.Color.gold()
            )
            reply.set_footer(text = f"{message.author}", icon_url=f"{message.author.avatar_url}")
            await message.channel.send(embed=reply, delete_after=5)
            return " _"
        else:
            return prefix
    
    else:
        return " _"

client = commands.AutoShardedBot(command_prefix=get_prefix)
client.remove_command("help")

token = str(os.environ.get("guild_manager_token"))
default_avatar_url = "https://cdn.discordapp.com/attachments/664230839399481364/677534213418778660/default_image.png"

#========Lists and values=========
from functions import guild_limit, member_limit, owner_ids, is_command

turned_on_at = datetime.datetime.utcnow()

statuses = {
    "dnd": discord.Status.dnd,
    "idle": discord.Status.idle,
    "online": discord.Status.online,
    "invisible": discord.Status.invisible
}

#======== Functions ========
from functions import get_field, find_alias, has_permissions, is_command, Guild

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

def first_allowed_channel(guild):
    out = None
    for channel in guild.text_channels:
        can = channel.permissions_for(guild.me)
        if can.send_messages and can.embed_links:
            out = channel
            break
    return out

def array(date_time):
    return list(date_time.timetuple())[:-3]

def dt(array):
    return datetime.datetime(*array)

async def send_to_dev(content=None, embed=None):
    dev_server_id = 670679133294034995
    key_name = "активность-пользователей"
    dev_server = client.get_guild(dev_server_id)
    if dev_server is not None:
        dev_channel = None
        for tc in dev_server.text_channels:
            if key_name in tc.name:
                dev_channel = tc
                break
        if dev_channel is not None:
            await dev_channel.send(content=content, embed=embed)

async def try_send(channel, content=None, embed=None):
    dm_opened = True
    try:
        await channel.send(content=content, embed=embed)
    except Exception:
        dm_opened = False
    return dm_opened

class LocalGuildData:
    def __init__(self, folder_name):
        self.folder_name = folder_name
        self.opened_data = None

    def get_bucket(self, guild_id):
        bucket = str(guild_id >> 22)[:-10]
        if bucket == "":
            bucket = "0"
        return bucket

    def open_for(self, guild_id):
        bucket = self.get_bucket(guild_id)
        filename = f"{self.folder_name}_{bucket}.json"
        if self.folder_name in os.listdir("."):
            if filename in os.listdir(f"{self.folder_name}"):
                with open(f"{self.folder_name}/{filename}", "r", encoding="utf8") as fff:
                    self.opened_data = json.load(fff)
            else:
                self.opened_data = {}
        else:
            self.opened_data = {}
    
    def update(self, guild_id, user_id, value):
        g, u = str(guild_id), str(user_id)
        if g not in self.opened_data:
            self.opened_data[g] = {u: value}
        else:
            self.opened_data[g][u] = value

    def save_changes_for(self, guild_id):
        if self.opened_data is not None:
            bucket = self.get_bucket(guild_id)
            filename = f"{self.folder_name}/{self.folder_name}_{bucket}.json"
            if self.folder_name not in os.listdir("."):
                os.mkdir(self.folder_name)
            with open(filename, "w", encoding="utf8") as fff:
                json.dump(self.opened_data, fff)
            self.opened_data = None

#======== Events =========

@client.event
async def on_ready():
    print(
        ">> Bot is ready\n"
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
async def on_guild_join(guild):
    p = default_prefix
    greet = discord.Embed(
        title=f"🎁 Спасибо за то, что выбрали **{client.user.name}**!",
        description=(
            f"Категории команд можно увидеть, написав `{p}help`\n"
            f"Рекомендую начать с категории `{p}help settings`\n"
            f"Не забудьте настроить канал для отчётов, это очень полезно! `{p}log-channel #канал`\n"
            f"Более понятное руководство есть **[на страничке бота](https://top.gg/bot/677976225876017190)**\n\n"
            "`🔼` **[Проголосовать за меня](https://top.gg/bot/677976225876017190/vote)**\n"
            "`🌍` **[Сервер разработчика](https://discord.gg/Hp8XFcp)**\n"
            "`🐱` **[GitHub](https://github.com/EQUENOS/Subguild-Manager)**\n"
            "`💌` **[Добавить на сервер](https://discordapp.com/api/oauth2/authorize?client_id=677976225876017190&permissions=470150209&scope=bot)**\n"
        ),
        color=discord.Color.gold()
    )
    greet.set_thumbnail(url=f"{guild.me.avatar_url}")

    channel = first_allowed_channel(guild)
    if channel is None:
        dm_opened = await try_send(guild.owner, f"{guild.owner.mention}", greet)
        if dm_opened:
            greet_desc = "отправлено **главе**"
        else:
            greet_desc = "не было отправлено"
    else:
        await channel.send(f"{guild.owner.mention}", embed=greet)
        greet_desc = f"отправлено в канал **#{channel.name}**"
    
    log = discord.Embed(
        title="⚡ Добавлен на сервер",
        description=(
            f"**Название:** {guild.name}\n"
            f"**Участников:** {guild.member_count}\n"
            f"**Статус приветствия:** {greet_desc}\n"
        ),
        color=discord.Color.gold()
    )
    log.set_footer(text=f"ID: {guild.id}")
    log.set_thumbnail(url=f"{guild.icon_url}")
    await send_to_dev(embed=log)

@client.event
async def on_guild_remove(guild):
    collection = db["subguilds"]
    collection.delete_one({"_id": guild.id})
    collection = db["cmd_channels"]
    collection.delete_one({"_id": guild.id})

    log = discord.Embed(
        title="💥 Больше нет на сервере",
        description=(
            f"**Название:** {guild.name}\n"
            f"**Участников:** {guild.member_count}"
        ),
        color=discord.Color.dark_red()
    )
    log.set_footer(text=f"ID: {guild.id}")
    log.set_thumbnail(url=f"{guild.icon_url}")
    await send_to_dev(embed=log)

#=========Commands==========
@client.command()
async def logout(ctx):
    if ctx.author.id in owner_ids:
        await ctx.send("Logging out...")
        await client.logout()

@client.command()
async def execute(ctx, *, text):
    if ctx.author.id in owner_ids:
        text = text.strip("```")
        if text.startswith("py"):
            text = text[2:]
        try:
            exec(text)
        except Exception as e:
            await ctx.send(f">>> Произошёл сбой: {e}")

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
@client.command(aliases = ["bot-stats", "bs"])
async def bot_stats(ctx):
    servers = client.guilds
    total_users = 0
    total_servers = 0
    total_shards = client.shard_count
    for server in servers:
        total_users += server.member_count
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
        "> [Добавить на сервер](https://discordapp.com/api/oauth2/authorize?client_id=677976225876017190&permissions=470150209&scope=bot)\n"
        "> [Проголосовать за бота](https://top.gg/bot/677976225876017190/vote)\n"
        "> [Страничка бота](https://top.gg/bot/677976225876017190)\n"
        "> [Сервер разработчика](https://discord.gg/Hp8XFcp)\n"
        "> [GitHub](https://github.com/EQUENOS/Subguild-Manager)\n"
    )

    reply = discord.Embed(
        title = "📊 О боте",
        color = mmorpg_col("lilac")
    )
    reply.set_thumbnail(url = f"{client.user.avatar_url}")
    reply.add_field(name="💠 **Всего шардов**", value=f"> {total_shards}", inline=False)
    reply.add_field(name="📚 **Всего серверов**", value=f"> {total_servers}", inline=False)
    reply.add_field(name="👥 **Всего пользователей**", value=f"> {total_users}", inline=False)
    reply.add_field(name="🌐 **Аптайм**", value=f"> {delta_desc}", inline=False)
    reply.add_field(name="🛠 **Разработчик**", value=f"{dev_desc}\nБлагодарность:\n> VernonRoshe")
    reply.add_field(name="🔗 **Ссылки**", value=link_desc)

    await ctx.send(embed = reply)

@commands.cooldown(1, 1, commands.BucketType.member)
@client.command(aliases=["h"])
async def help(ctx, *, section=None):
    p = ctx.prefix
    sections = {
        "settings": ["настройки"],
        "guilds": ["гильдии"],
        "manage guilds": ["set guilds", "настроить гильдию", "mg"],
        "event": ["ивент", "событие"]
    }
    titles = {
        "settings": "О настройках",
        "guilds": "О гильдиях",
        "manage guilds": "О ведении гильдий",
        "event": "Об игровом событии"
    }
    if section is None:
        reply = discord.Embed(
            title="📖 Меню помощи",
            description=(
                "Введите команду, интересующую Вас:\n\n"
                f"`{p}help guilds` - о гильдиях\n"
                f"`{p}help manage guilds` - ведение гильдии\n"
                f"`{p}help settings` - настройки\n"
                f"`{p}help event` - об ивенте\n\n"
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

@commands.cooldown(1, 30, commands.BucketType.user)
@client.command(aliases=["load"])
async def download(ctx, *, guild_name):
    pr = ctx.prefix
    collection = db["subguilds"]
    result = collection.find_one(
        {"_id": ctx.guild.id, "subguilds.name": guild_name},
        projection={"subguilds": True}
    )
    if result is None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{pr}top`"
            ),
            color = mmorpg_col("vinous")
        )
        await ctx.send(embed = reply)
    
    else:
        g = Guild(get_subguild(result, guild_name))
        del result

        leader = None
        if g.leader_id is not None:
            leader = ctx.guild.get_member(g.leader_id)
        helper = None
        if g.helper_id is not None:
            helper = ctx.guild.get_member(g.helper_id)
        
        table = [
            ["Репутация", f"{g.reputation}", "", "Глава", f"{leader}", "", "Участник"],
            ["Упоминания", f"{g.mentions}", "", "ID главы", f"{g.leader_id}", "", "ID участника"],
            ["", "", "", "Помощник", f"{helper}", "", "Опыт участника"],
            ["", "", "", "ID помощника", f"{g.helper_id}"]
        ]
        members = g.members_as_pairs()
        g.forget_members()
        members.sort(key=lambda pair: pair[1], reverse=True)
        for pair in members:
            member = ctx.guild.get_member(pair[0])
            table[0].append(f"{member}")
            table[1].append(f"{pair[0]}")
            table[2].append(f"{pair[1]}")
        del g

        workbook = Workbook(f"Guild_download_{ctx.author.id}.xlsx")
        worksheet = workbook.add_worksheet()
        for i, column in enumerate(table):
            worksheet.write_column(0, i, column)
        workbook.close()

        with open(f"Guild_download_{ctx.author.id}.xlsx", "rb") as temp_file:
            await ctx.send(
                f"{ctx.author.mention}, данные гильдии {guild_name}",
                file=discord.File(temp_file, "Guild Profile Tabulated.xlsx")
            )
        os.remove(f"Guild_download_{ctx.author.id}.xlsx")

#======== Events ========
@client.event    # TEMPORARY INACTIVE EVENT
async def on_message(message):
    # If not direct message
    if message.guild != None:
        collection = None
        user_id = message.author.id
        server_id = message.guild.id
        channel_id = message.channel.id
        mentioned_members = message.mentions

        if not message.author.bot:
            if message.content in [f"<@!{client.user.id}>", f"<@{client.user.id}>"]:
                collection = db["cmd_channels"]
                result = collection.find_one({"_id": server_id}, projection={"prefix": True})
                await message.channel.send(f"Мой префикс: `{result.get('prefix', default_prefix)}`")

            await client.process_commands(message)

            # Check cooldown and calculate income
            collection = db["subguilds"]
            now = datetime.datetime.utcnow()

            xpbuf = LocalGuildData("XP_Buckets")
            xpbuf.open_for(server_id)
            past = get_field(xpbuf.opened_data, str(server_id), str(user_id))
            
            passed_cd = False
            if past is None:
                passed_cd = True
            else:
                past = dt(past)
                _10_sec = datetime.timedelta(seconds=10)
                if now - past >= _10_sec:
                    passed_cd = True
            
            if passed_cd:
                xpbuf.update(server_id, user_id, array(now))
                xpbuf.save_changes_for(server_id)

                # GoT event: temporary "$or" query operator
                result = collection.find_one(
                    {
                        "_id": server_id,
                        "$or": [
                            {f"subguilds.members.{user_id}": {"$exists": True}},
                            {f"night_watch.members.{user_id}": {"$exists": True}}
                        ]
                    }
                )
                to_ignore = get_field(result, "ignore_chats", default=[])
                if channel_id not in to_ignore and result is not None:
                    # GoT event: checking where to add XP
                    if str(user_id) in get_field(result, "night_watch", "members", default=[]):
                        collection.find_one_and_update(
                            {"_id": server_id, f"night_watch.members.{user_id}": {"$exists": True}},
                            {"$inc": {f"night_watch.members.{user_id}": 10}}
                        )

                    else:
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

            key_words = [f"subguilds.members.{m.id}" for m in mentioned_members]
            # GoT event: adding search query
            key_words.extend([f"night_watch.members.{m.id}" for m in mentioned_members])
            del mentioned_members

            proj = {kw: True for kw in key_words}
            proj.update([("subguilds.name", True)])

            result = collection.find_one(
                {"_id": server_id, "mentioner_id": user_id},
                projection=proj
            )
            
            if result is not None:
                subguilds = get_field(result, "subguilds", default=[])
                for sg in subguilds:
                    if sg["members"] != {}:
                        collection.find_one_and_update(
                            {"_id": server_id, "subguilds.name": sg["name"]},
                            {"$inc": {"subguilds.$.mentions": len(sg["members"])}}
                        )
                
                # GoT event: adding mentions
                nw = get_field(result, "night_watch")
                if nw is not None:
                    collection.find_one_and_update(
                        {"_id": server_id},
                        {"$inc": {"night_watch.mentions": len(nw["members"])}}
                    )

#======== Errors ==========
# Cooldown
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        
        def TimeExpand(time):
            if time//60 > 0:
                return str(time//60)+'мин. '+str(time%60)+' сек.'
            elif time > 0:
                return str(time)+' сек.'
            else:
                return f"0.1 сек."
        
        cool_notify = discord.Embed(
                title='⏳ Подождите немного',
                description = f"Осталось {TimeExpand(int(error.retry_after))}"
            )
        await ctx.send(embed=cool_notify)

@download.error
async def download_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix
        cmd = ctx.command.name
        reply = discord.Embed(
            title = f"❓ Об аргументах `{p}{cmd}`",
            description = (
                "**Описание:** скачивает данные гильдии в виде .xlsx таблицы\n"
                f"**Использование:** `{p}{cmd} Название гильдии`\n"
                f"**Пример:** `{p}{cmd} Короли`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)


async def change_status(status_text, str_activity):
    await client.wait_until_ready()
    await client.change_presence(
        activity=discord.Game(status_text),
        status=get_field(statuses, str_activity)
    )
client.loop.create_task(change_status(f"{default_prefix}help", "online"))

#--------- Loading Cogs ---------

for file_name in os.listdir("./cogs"):
    if file_name.endswith(".py"):# and not file_name.startswith("dbl"):  # TEMPORARY PARTIAL LOAD
        client.load_extension(f"cogs.{file_name[:-3]}")

client.run(token)