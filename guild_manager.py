import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import os, json, datetime
from xlsxwriter import Workbook
from memory_profiler import memory_usage


async def get_prefix(client, message):
    if message.guild is not None:
        if client.user.id == 582881093154504734:
            return ".."
        # In case it's not test bot:
        pconf = ResponseConfig(message.guild.id)
        if pconf.cmd_channels == []:
            return pconf.prefix
        author = message.author
        channel = message.channel
        iscmd = is_command(message.content, pconf.prefix, client)
        del message, client
        if channel.id not in pconf.cmd_channels and iscmd:
            if author.guild_permissions.administrator:
                return pconf.prefix
            reply = discord.Embed(color=discord.Color.gold())
            reply.title = "⚠ | Канал"
            reply.description = "Для использования команд, пожалуйста, пишите в другом канале."
            reply.set_footer(text=str(author), icon_url=author.avatar_url)
            await channel.send(embed=reply)
            return " "
        return pconf.prefix
    return " "


#----------------------------+
#        Connecting          |
#----------------------------+
intents = discord.Intents.default()
intents.members = True
client = commands.AutoShardedBot(command_prefix=get_prefix, intents=intents)
client.remove_command("help")

token = str(os.environ.get("guild_manager_token"))

#----------------------------+
#         Constants          |
#----------------------------+
from functions import owner_ids, XP_gateway, display_perms, EmergencyExit


turned_on_at = datetime.datetime.utcnow()
logged_in_at = None

statuses = {
    "dnd": discord.Status.dnd,
    "idle": discord.Status.idle,
    "online": discord.Status.online,
    "invisible": discord.Status.invisible
}

to_send = []

xp_gateway_path = "XP_buckets"
# Setting up the XP_gateway
gw = XP_gateway(xp_gateway_path)
gw.set_path()
del gw

#----------------------------+
#         Functions          |
#----------------------------+
from functions import find_alias, is_command, anf
from db_models import ResponseConfig, Server, Guild, default_prefix
from custom_converters import IsNotInt, IsNotSubguild


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


def add_tabs(text, amount=1):
    text = "\n" + text
    return text.replace("\n", "\n" + amount * "    ")


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

#----------------------------+
#           Events           |
#----------------------------+

@client.event
async def on_ready():
    global logged_in_at
    logged_in_at = datetime.datetime.utcnow()
    print(
        ">> Bot is ready\n"
        f">> Bot user: {client.user}\n"
        ">> Loading Cogs...\n"
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
        await channel.send(embed=greet)
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
    Server(guild.id, {"_id": True}).delete()
    ResponseConfig(guild.id, {"_id": True}).delete()

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

#----------------------------+
#          Commands          |
#----------------------------+
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
        text = add_tabs(text, 3)

        cog_code = open("cogs/ghost_cog.py", "r", encoding="utf8").read()
        length = len(cog_code)

        u_string, d_string = "# INSERT_START", "# INSERT_END"
        u_wid, d_wid = len(u_string), len(d_string)
        u_i, d_i = None, None

        i = 0
        while i < length:
            if cog_code[i:i + u_wid] == u_string:
                i += u_wid
                u_i = i
                while i < length:
                    if cog_code[i:i + d_wid] == d_string:
                        d_i = i
                        break
                    i += 1
            if u_i is not None:
                break
            i += 1
        
        if u_i is None:
            await ctx.send("```>>> No placeholders detected in ghost_cog.py```")
        else:
            if d_i is None:
                d_i = u_i
            cog_code = f"{cog_code[:u_i]}\n{text}\n{cog_code[d_i:]}"

            with open("cogs/ghost_cog.py", "w", encoding="utf8") as f:
                f.write(cog_code)
            
            client.reload_extension("cogs.ghost_cog")
            await ctx.send("```>>> Ghost cog updated```")


@commands.cooldown(1, 5, commands.BucketType.member)
@commands.is_owner()
@client.command(aliases = ["view-memory"])
async def view_memory(ctx):
    mb = memory_usage()
    reply = discord.Embed(
        title="💾 | Расход оперативной памяти",
        description=f"Около **{mb[0]}** Мб",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=reply)


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
    reply.add_field(name="🛰 **Пинг**", value=f"> {client.latency * 1000:.0f}", inline=False)
    reply.add_field(name="🌐 **Аптайм**", value=f"> {delta_desc}", inline=False)
    if ctx.author.id in owner_ids:
        if logged_in_at is None:
            value = "logging in..."
        else:
            value = logged_in_at - turned_on_at
        reply.add_field(name="💻 **Потрачено времени на логин**", value=f"> `{value}`", inline=False)
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
@client.command(
    aliases=["load"],
    description="скачивает данные гильдии в виде `.xlsx` таблицы.",
    usage="Название гильдии",
    brief="Короли" )
async def download(ctx, *, guild_name):
    pr = ctx.prefix
    g = Guild(ctx.guild.id, name=guild_name)
    if g is None:
        raise IsNotSubguild(guild_name)
    
    else:
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
        for m in sorted(g.members, key=lambda m: m.xp, reverse=True):
            member = ctx.guild.get_member(m.id)
            table[0].append(f"{member}")
            table[1].append(f"{m.id}")
            table[2].append(f"{m.xp}")
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

#----------------------------+
#         On Message         |
#----------------------------+
@client.event
async def on_message(message):
    # If not direct message
    if message.guild is not None:
        user_id = message.author.id
        server_id = message.guild.id
        channel_id = message.channel.id
        mentioned_members = [m.id for m in message.mentions]

        if not message.author.bot:
            if message.content in [f"<@!{client.user.id}>", f"<@{client.user.id}>"]:
                pref = ResponseConfig(server_id, {"prefix": True}).prefix
                await message.channel.send(f"Мой префикс: `{pref}`")

            await client.process_commands(message)
            del message

            # Checking cooldown
            xpbuf = XP_gateway(xp_gateway_path)
            passed_cd = xpbuf.process(user_id)
            
            if passed_cd:
                sconf = Server(server_id, {"ignore_chats": True, "xp_locked": True, "subguilds.members": True})
                # Adding xp
                if not sconf.xp_locked and channel_id not in sconf.ignore_channels:
                    sconf.add_auto_xp(user_id)
        
        # Award with mentions
        if mentioned_members != []:
            Server(server_id, dont_request_bd=True).add_mentions(user_id, mentioned_members)

#----------------------------+
#   Processing Exceptions    |
#----------------------------+
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
        
        reply = discord.Embed()
        reply.title ='⏳ | Подождите немного'
        reply.description = f"Осталось {TimeExpand(int(error.retry_after))}"
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)
    
    elif isinstance(error, commands.CommandNotFound):
        pass
    
    elif isinstance(error, EmergencyExit):
        pass

    elif isinstance(error, commands.MissingRequiredArgument):
        p = ctx.prefix; cmd = ctx.command
        iw = cmd.name
        description = "`-`"; usage = "`-`"; brief = "`-`"; aliases = "-"
        if cmd.description != "":
            description = cmd.description
        if cmd.usage is not None:
            usage = "\n> ".join( [f"`{p}{iw} {u}`" for u in cmd.usage.split("\n")] )
        if cmd.brief is not None:
            brief = "\n> ".join( [f"`{p}{iw} {u}`" for u in cmd.brief.split("\n")] )
        if len(cmd.aliases) > 0:
            aliases = "`, `".join(cmd.aliases)
        
        reply = discord.Embed(
            title = f"❓ | Об аргументах `{p}{iw}`",
            description = (
                f"**Описание:** {description}\n\n"
                f"**Использование:** {usage}\n"
                f"**Примеры:** {brief}\n\n"
                f"**Синонимы:** `{aliases}`"
            ),
            color=int("ffce4b", 16)
        )
        if cmd.help is not None:          # So here I use cmd.help as an optional url holder
            reply.set_image(url=cmd.help) # Ok? So don't forget please
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)

        try:
            ctx.command.reset_cooldown(ctx)
        except Exception:
            pass
    
    elif isinstance(error, commands.BadArgument):
        if isinstance(error, commands.MemberNotFound):
            desc = f"Участник **{anf(error.argument)}** не был найден."
        elif isinstance(error, commands.ChannelNotFound):
            desc = f"Канал **{anf(error.argument)}** не был найден."
        elif isinstance(error, commands.RoleNotFound):
            desc = f"Роль **{anf(error.argument)}** не была найдена."
        elif isinstance(error, IsNotInt):
            desc = f"Аргумент **{error.argument}** должен быть целым числом, например `5`."
        elif isinstance(error, IsNotSubguild):
            desc = f"По запросу **{anf(error.argument)}** не было найдено гильдий."
        else:
            desc = "Введённый аргумент не соответствует требуемому формату."

        reply = discord.Embed(
            title="❌ | Что-то введено неправильно...",
            description=desc,
            color=discord.Color.dark_red()
        )
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)

    elif isinstance(error, commands.MissingPermissions):
        reply = discord.Embed(
            title="❌ | Недостаточно прав",
            description=f"Нужно одно из прав:\n{display_perms(error.missing_perms)}",
            color=discord.Color.dark_red()
        )
        reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=reply)

    else:
        print(error)


async def change_status(status_text, str_activity):
    await client.wait_until_ready()
    await client.change_presence(
        activity=discord.Game(status_text),
        status=statuses.get(str_activity, discord.Status.online)
    )
client.loop.create_task(change_status(f"{default_prefix}help", "online"))

#--------- Loading Cogs ---------

for file_name in os.listdir("./cogs"):
    if file_name.endswith(".py"):# and not file_name.startswith("dbl"):  # TEMPORARY PARTIAL LOAD
        try:
            client.load_extension(f"cogs.{file_name[:-3]}")
        except Exception as e:
            print(f">> Error: {e}")

client.run(token)