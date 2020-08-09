import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import os, datetime

import pymongo
from pymongo import MongoClient

app_string = str(os.environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

#---------- Variables ------------
from functions import member_limit, guild_limit, cool_servers, owner_ids

#---------- Functions ------------
from functions import has_permissions, get_field, detect, find_alias, read_message, display_list

# Other
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

def is_cool_server():
    def predicate(ctx):
        return ctx.guild.id in cool_servers
    return commands.check(predicate)

def is_developer():
    def predicate(ctx):
        return ctx.author.id in owner_ids
    return commands.check(predicate)

async def post_log(guild, channel_id, log):
    if channel_id is not None:
        channel = guild.get_channel(channel_id)
        if channel is not None:
            await channel.send(embed=log)

async def do_smart_reset(server: int):     # BETA
    collection = db["subguilds"]
    result = collection.find_one(
        {"_id": server.id},
        projection={
            "subguilds.name": True,
            "subguilds.members": True,
            "log_channel": True
        }
    )
    if result is not None:
        xp_pairs = []
        for sg in result["subguilds"]:
            zero_data = {}
            total_xp = 0
            for key in sg["members"]:
                total_xp += sg["members"][key]["messages"]
                zero_data[f"subguilds.$.members.{key}"] = {"messages": 0}

            if zero_data != {}:
                collection.update_one(
                    {"_id": server.id, "subguilds.name": sg["name"]},
                    {"$set": zero_data}
                )
            
            xp_pairs.append((sg["name"], total_xp))
        
        # Smart-reset test: adding super-points
        xp_pairs.sort(reverse=True, key=lambda p: p[1])
        max_points = len(xp_pairs)
        desc = ""
        for i, pair in enumerate(xp_pairs):
            collection.update_one(
                {"_id": server.id, "subguilds.name": pair[0]},
                {"$inc": {"subguilds.$.superpoints": max_points - i}}
            )
            desc += f"> {pair[0]}: `+{max_points - i}` 🪐\n"

    log = discord.Embed(
        title="♻ Сброс опыта и начисление супер-поинтов",
        description=f"Проведён автоматически\n{desc}"
    )
    lc_id = get_field(result, "log_channel")
    await post_log(server, lc_id, log)

class Timer:
    def __init__(self, server_id: int, data: dict=None):
        self.id = server_id
        if data is None:
            collection = db["timers"]
            data = collection.find_one({"_id": self.id, "cycles": {"$gt": 0}})
            if data is None:
                data = {}
        now = datetime.datetime.utcnow()
        self.cycles = data.get("cycles", 1)
        self.interval = datetime.timedelta(hours=data.get("interval", 24))
        self.last_at = data.get("last_at", now - self.interval)
        self.next_at = self.last_at + self.interval
    
    @property
    def time_remaining(self):
        now = datetime.datetime.utcnow()
        return datetime.timedelta(seconds=0) if now >= self.next_at else self.next_at - now
    
    def update(self):
        collection = db["timers"]
        collection.update_one(
            {"_id": self.id, "cycles": {"$gt": 0}},
            {"$set": {"last_at": self.next_at, "cycles": self.cycles - 1}}
        )
        self.cycles -= 1
        self.last_at, self.next_at = self.next_at, self.next_at + self.interval
    
    def save(self):
        collection = db["timers"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {
                "cycles": self.cycles,
                "interval": self.interval.total_seconds() // 3600,
                "last_at": self.last_at
            }},
            upsert=True
        )
    
    def delete(self):
        collection = db["timers"]
        collection.delete_one({"_id": self.id})

class TimerList:
    def __init__(self):
        collection = db["timers"]
        self.timers = [ Timer(data.get("_id"), data) for data in collection.find() ]


class setting_system(commands.Cog):
    def __init__(self, client):
        self.client = client

    #---------- Events -----------
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Setting system cog is loaded")

        async def my_task(timer: Timer):
            while timer.cycles > 0:
                await asyncio.sleep(timer.time_remaining.total_seconds())
                try:
                    server = self.client.get_guild(timer.id)
                except Exception:
                    server = None
                if server is None:
                    break
                else:
                    await do_smart_reset(server)
                    del server
                timer.update()
            timer.delete()
            return
        
        tl = TimerList()
        for timer in tl.timers:
            self.client.loop.create_task(my_task(timer))
        print("--> Launched timers")
    
    #---------- Commands ----------
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases=["set", "how-set", "config"])
    async def settings(self, ctx):
        collection = db["cmd_channels"]
        result = collection.find_one({"_id": ctx.guild.id})
        wl_channels = get_field(result, "channels")
        c_prefix = get_field(result, "prefix", default=".")
        
        if wl_channels is None:
            chan_desc = "> Все каналы\n"
        else:
            chan_desc = ""
            for ID in wl_channels:
                chan_desc += f"> <#{ID}>\n"
            if chan_desc == "":
                chan_desc = "> Все каналы\n"
        
        collection = db["subguilds"]
        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={
                "subguilds": False
            }
        )
        log_channel_id = get_field(result, "log_channel")
        pinger_id = get_field(result, "mentioner_id")
        mr_ids = get_field(result, "master_roles", default=[])
        cr_ids = get_field(result, "creator_roles", default=[])
        lim_desc = get_field(result, "member_limit", default=member_limit)
        g_lim_desc = get_field(result, "guild_limit", default=guild_limit)
        igch = get_field(result, "ignore_chats")
        xp_locked = get_field(result, "xp_locked", default=False)
        join_filter = get_field(result, "auto_join", default=False)
        leave_blocker = get_field(result, "block_leave", default=False)

        if igch is None:
            ig_desc = "> Отсутствуют\n"
        else:
            ig_desc = ""
            for ID in igch:
                ig_desc += f"> <#{ID}>\n"
        
        if log_channel_id is None:
            lc_desc = "> Отсутствует"
        else:
            lc_desc = f"> <#{log_channel_id}>"
        
        if pinger_id is None:
            ping_desc = "> выключено"
        else:
            ping_desc = f"> {ctx.guild.get_member(pinger_id)}"
        
        if mr_ids == []:
            mr_desc = "> Отсутствуют"
        else:
            mr_desc = ""
            for ID in mr_ids:
                mr_desc += f"> <@&{ID}>\n"
        
        if cr_ids == []:
            cr_desc = "> Отсутствуют"
        else:
            cr_desc = ""
            for ID in cr_ids:
                cr_desc += f"> <@&{ID}>\n"
        
        if xp_locked:
            xpl_desc = "✅ Включена"
        else:
            xpl_desc = "❌ Выключена"
        if join_filter:
            aj_desc = "✅ Включен"
        else:
            aj_desc = "❌ Выключен"
        if leave_blocker:
            lb_desc = "✅ Включен"
        else:
            lb_desc = "❌ Выключен"

        reply = discord.Embed(
            title = "⚙ Текущие настройки сервера",
            description = (
                f"**Префикс:** `{c_prefix}`"
            ),
            color = mmorpg_col("lilac")
        )
        reply.add_field(name="**Каналы для команд бота**", value=f"{chan_desc}")
        reply.add_field(name="**Каналы игнорирования опыта**", value=f"{ig_desc}")
        reply.add_field(name="**Канал логов**", value=f"{lc_desc}", inline=False)
        reply.add_field(name="**Роли мастера гильдий:**", value=f"{mr_desc}")
        reply.add_field(name="**Роли для создания гильдий**", value=f"{cr_desc}")
        reply.add_field(name="**Вести подсчёт упоминаний от**", value=f"{ping_desc}", inline=False)
        reply.add_field(name="**Лимит гильдий на сервере**", value=f"> {g_lim_desc}")
        reply.add_field(name="**Лимит пользователей на гильдию**", value=f"> {lim_desc}")
        reply.add_field(name="**Блокировка опыта**", value=f"> {xpl_desc}")
        reply.add_field(name="**Авто вход в гильдии**", value=f"> {aj_desc}")
        reply.add_field(name="**Запрет на выход из гильдий**", value=f"> {lb_desc}")

        reply.set_thumbnail(url = f"{ctx.guild.icon_url}")
        await ctx.send(embed = reply)

    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["set-prefix", "setprefix", "sp"])
    async def prefix(self, ctx, text_input):
        text_input = text_input[:30]
        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title = "💢 Недостаточно прав",
                description = (
                    "Требуемые права:\n"
                    "> Администратор"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = str(ctx.author), icon_url = str(ctx.author.avatar_url))
            await ctx.send(embed = reply)
        
        else:
            collection = db["cmd_channels"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"prefix": text_input}},
                upsert=True
            )
            reply = discord.Embed(
                title="✅ Настроено",
                description=f"Новый префикс: {text_input}\nТекущие настройки: `{text_input}settings`",
                color=mmorpg_col("clover")
            )
            reply.set_footer(text = str(ctx.author), icon_url = str(ctx.author.avatar_url))
            await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["cmd-channels", "cmdchannels", "cc"])
    async def cmd_channels(self, ctx, *, text_input):
        collection = db["cmd_channels"]
        raw_ch = text_input.split()

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
            collection.update_one(
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
            channel_ids = []
            invalid_channel_mentioned = False
            for s in raw_ch:
                ch = detect.channel(ctx.guild, s)
                if ch is None:
                    invalid_channel_mentioned = True
                    break
                elif not ch.id in channel_ids:
                    channel_ids.append(ch.id)

            if invalid_channel_mentioned:
                reply = discord.Embed(
                    title = f"💢 Упс",
                    description = (
                        f"Возможно, я не вижу какие-то каналы, или они указаны неправильно\n"
                        f"В качестве каналов укажите их **#ссылки** или **ID**\n"
                        f"Или же, чтобы отключить - `delete`"
                    ),
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            else:
                channel_ids = channel_ids[:+30]
                collection.update_one(
                    {"_id": ctx.guild.id},
                    {
                        "$set": {"channels": channel_ids}
                    },
                    upsert=True
                )
                desc = ""
                for ch in channel_ids:
                    desc += f"> <#{ch}>\n"
                reply = discord.Embed(
                    title = "🛠 Каналы настроены",
                    description = (
                        f"Теперь бот реагирует на команды только в каналах:\n"
                        f"{desc}"
                        f"Исключение - администраторы 😉"
                    ),
                    color = mmorpg_col("lilac")
                )
                await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["ignore-channels", "ignore", "ic"])
    async def ignore_channels(self, ctx, *, text_input):
        collection = db["subguilds"]
        raw_ch = text_input.split()

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
            collection.update_one(
                {"_id": ctx.guild.id},
                {
                    "$unset": {"ignore_chats": ""}
                }
            )
            reply = discord.Embed(
                title = "♻ Каналы сброшены",
                description = "Теперь я начисляю опыт за сообщения во всех каналах",
                color = mmorpg_col("clover")
            )
            await ctx.send(embed = reply)

        else:
            channel_ids = []
            invalid_channel_mentioned = False
            for s in raw_ch:
                ch = detect.channel(ctx.guild, s)
                if ch is None:
                    invalid_channel_mentioned = True
                    break
                elif not ch.id in channel_ids:
                    channel_ids.append(ch.id)
            
            if invalid_channel_mentioned:
                reply = discord.Embed(
                    title = f"💢 Упс",
                    description = (
                        f"Возможно, я не вижу какие-то каналы, или они указаны неправильно\n"
                        f"В качестве каналов укажите их **#ссылки** или **ID**\n"
                        f"Или, чтобы отключить игнорирование укажите `delete`"
                    ),
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            else:
                channel_ids = channel_ids[:+30]

                collection.update_one(
                    {"_id": ctx.guild.id},
                    {
                        "$set": {"ignore_chats": channel_ids}
                    },
                    upsert=True
                )
                desc = ""
                for ch in channel_ids:
                    desc += f"> <#{ch}>\n"
                reply = discord.Embed(
                    title = "🛠 Каналы настроены",
                    description = (
                        f"Теперь я не буду начислять опыт за сообщения в каналах:\n"
                        f"{desc}"
                    ),
                    color = mmorpg_col("lilac")
                )
                await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["xp-lock", "freeze"])
    async def xp_lock(self, ctx, option):
        p = ctx.prefix
        option = option.lower()
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
        
        elif option in ["on", "вкл"]:
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"xp_locked": True}},
                upsert=True
            )
            reply = discord.Embed(
                title = "🔒 Выполнено",
                description = (
                    "Включена блокировка опыта\n"
                    f"Выключить: `{p}xp-lock off`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif option in ["off", "выкл"]:
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"xp_locked": False}},
                upsert=True
            )
            reply = discord.Embed(
                title = "🔑 Выполнено",
                description = (
                    "Блокировка опыта выключена\n"
                    f"Включить: `{p}xp-lock on`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            reply = discord.Embed(
                title = f"💢 Неверная опция `{option}`",
                description = (
                    f"`{p}xp-lock on` - остановить доход опыта\n"
                    f"`{p}xp-lock off` - возобновить доход опыта"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["auto-join", "join-filter", "aj"])
    async def auto_join(self, ctx, option):
        p = ctx.prefix
        option = option.lower()
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
        
        elif option in ["on", "вкл"]:
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"auto_join": True}},
                upsert=True
            )
            reply = discord.Embed(
                title = "🔒 Выполнено",
                description = (
                    "Включен режим автоматического распределения по гильдиям.\n"
                    f"Выключить: `{p}auto-join off`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif option in ["off", "выкл"]:
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"auto_join": False}},
                upsert=True
            )
            reply = discord.Embed(
                title = "🔑 Выполнено",
                description = (
                    "Выключен режим автоматического распределения по гильдиям. Теперь участники сами могут выбрать гильдию для вступления.\n"
                    f"Включить: `{p}auto-join on`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            reply = discord.Embed(
                title = f"💢 Неверная опция `{option}`",
                description = (
                    f"`{p}auto-join on` - включить режим автоматического распределения по гильдиям.\n"
                    f"`{p}auto-join off` - выключить"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["block-leave", "bl", "blockleave"])
    async def block_leave(self, ctx, option):
        p = ctx.prefix
        option = option.lower()
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
        
        elif option in ["on", "вкл"]:
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"block_leave": True}},
                upsert=True
            )
            reply = discord.Embed(
                title = "🔒 Выполнено",
                description = (
                    "Теперь участники не смогут выходить из гильдий.\n"
                    f"Выключить: `{p}block-leave off`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif option in ["off", "выкл"]:
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"block_leave": False}},
                upsert=True
            )
            reply = discord.Embed(
                title = "🔑 Выполнено",
                description = (
                    "Теперь участники снова могут выходить из гильдий.\n"
                    f"Включить: `{p}block-leave on`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            reply = discord.Embed(
                title = f"💢 Неверная опция `{option}`",
                description = (
                    f"`{p}block-leave on` - включить блокировку выхода\n"
                    f"`{p}block-leave off` - выключить"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["log-channel", "logchannel", "logs-channel", "lc"])
    async def log_channel(self, ctx, channel_s):
        pr = ctx.prefix
        channel = detect.channel(ctx.guild, channel_s)
        
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
        
        elif channel_s.lower() == "delete":
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$unset": {"log_channel": ""}}
            )
            reply = discord.Embed(
                title="✅ Настроено",
                description=(
                    f"Канал для отчётов удалён\n\n"
                    f"Текущие настройки: `{pr}settings`"
                ),
                color=mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif channel is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = f"Вы указали {channel_s}, подразумевая канал, но он не был найден",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        else:
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"log_channel": channel.id}},
                upsert=True
            )

            reply = discord.Embed(
                title="✅ Настроено",
                description=(
                    f"Теперь отчёты приходят в канал <#{channel.id}>\n"
                    f"Отменить: `{pr}log-channel delete`\n"
                    f"Текущие настройки: `{pr}settings`"
                ),
                color=mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["members-limit", "memberslimit", "ml"])
    async def members_limit(self, ctx, lim):
        pr = ctx.prefix
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
        elif not lim.isdigit():
            reply = discord.Embed(
                title = "💢 Неверный аргумент",
                description = f"Аргумент {lim} должен быть целым положительным числом",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        elif int(lim) > member_limit:
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

            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"member_limit": lim}},
                upsert=True
            )
            reply = discord.Embed(
                title = "✅ Настроено",
                description = (
                    f"Текущий лимит пользователей в гильдиях: **{lim}**\n"
                    f"Отчёт о настройках: `{pr}settings`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(name="guild-limit", aliases = ["guildlimit", "gl"])
    async def guilds_limit(self, ctx, lim):
        pr = ctx.prefix
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
        elif not lim.isdigit():
            reply = discord.Embed(
                title = "💢 Неверный аргумент",
                description = f"Аргумент {lim} должен быть целым положительным числом",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        elif int(lim) > guild_limit:
            reply = discord.Embed(
                title = "❌ Ошибка",
                description = f"Лимит кланов не может превышать **{guild_limit}**",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            collection = db["subguilds"]
            lim = int(lim)

            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"guild_limit": lim}},
                upsert=True
            )
            reply = discord.Embed(
                title = "✅ Настроено",
                description = (
                    f"Текущий лимит кланов на сервере: **{lim}**\n"
                    f"Отчёт о настройках: `{pr}settings`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 30, commands.BucketType.member)
    @commands.command(aliases=["clear-guilds", "delete-all-guilds"])
    async def clear_guilds(self, ctx):
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

            msg = await read_message(ctx.channel, ctx.author, 60, self.client)
            if msg != None:
                reply_text = msg.content.lower()
                if reply_text in ["yes", "1", "да"]:
                    collection = db["subguilds"]
                    result = collection.find_one_and_update(
                        {"_id": ctx.guild.id},
                        {"$unset": {"subguilds": ""}},
                        projection={"log_channel": True}
                    )
                    reply = discord.Embed(
                        title="♻ Выполнено",
                        description = "Все гильдии удалены",
                        color=mmorpg_col("clover")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                    await sys_msg.delete()

                    lc_id = get_field(result, "log_channel")
                    log = discord.Embed(
                        title="🗑 Удалены все гильдии",
                        description=(
                            f"**Модератор:** {ctx.author}"
                        ),
                        color=discord.Color.dark_red()
                    )
                    await post_log(ctx.guild, lc_id, log)

                else:
                    reply = discord.Embed(
                        title="❌ Отмена",
                        description="Действие отменено",
                        color=mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                    await sys_msg.delete()

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(name="master-role", aliases = ["master-roles", "masterrole", "mr"])
    async def master_role(self, ctx, option, *, role_s=None):
        mr_lim = 5
        p, cmd = ctx.prefix, ctx.command.name

        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title = "💢 Недостаточно прав",
                description = (
                    "Требуемые права:\n"
                    "> Администратор"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)

        else:
            parameters = {
                "add": ["append", "set"],
                "delete": ["remove"]
            }
            parameter = find_alias(parameters, option)
            if parameter is None:
                reply = discord.Embed(
                    title = f"💢 Неизвестный параметр `{option}`",
                    description = (
                        "Попробуйте одну из этих команд:\n"
                        f"> `{p}{cmd} add`\n"
                        f"> `{p}{cmd} delete`"
                    ),
                    color = mmorpg_col("vinous")
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

            elif role_s is None:
                help_texts = {
                    "add": {
                        "desc": "Добавляет мастер-роль",
                        "usage": f"`{p}{cmd} add @Роль`"
                    },
                    "delete": {
                        "desc": "Удаляет мастер-роли",
                        "usage": (
                            f"удаление одной мастер-роли: `{p}{cmd} delete @Роль`\n"
                            f"Удаление всех мастер-ролей: `{p}{cmd} delete all`"
                        )
                    }
                }
                help_text = help_texts[parameter]
                reply = discord.Embed(
                    title=f"❔ Как использовать `{p}{cmd} {parameter}`",
                    description=f"**Описание:** {help_text['desc']}\n**Использование:** {help_text['usage']}"
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

            else:
                collection = db["subguilds"]
                result = collection.find_one(
                    {"_id": ctx.guild.id},
                    projection={"master_roles": True}
                )
                master_roles = get_field(result, "master_roles", default=[])
                del result

                if role_s.lower() != "all":
                    role = detect.role(ctx.guild, role_s)
                if parameter == "add":
                    if role is None:
                        reply = discord.Embed(
                            title = "💢 Роль не распознана",
                            description = f"Вы ввели **{role_s}**, подразумевая роль, но она не была найдена",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    elif role.id in master_roles:
                        reply = discord.Embed(
                            title = "💢 Уже мастер-роль",
                            description = f"<@&{role.id}> уже является мастер-ролью.\nСписок Ваших настроек: `{p}settings`",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    elif len(master_roles) >= mr_lim:
                        reply = discord.Embed(
                            title = "💢 Лимит",
                            description = (
                                f"Мастер-ролей на сервере не может быть больше {mr_lim}\n"
                                f"Ваши текущие настройки: `{p}settings`"
                            ),
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    else:
                        collection.update_one(
                            {"_id": ctx.guild.id},
                            {"$addToSet": {"master_roles": role.id}},
                            upsert=True
                        )
                        reply = discord.Embed(
                            title = "♻ Выполнено",
                            description = f"Теперь <@&{role.id}> является мастер-ролью\nСписок настроек: `{p}settings`",
                            color = mmorpg_col("clover")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                else:
                    if role_s.lower() == "all":
                        collection.update_one(
                            {"_id": ctx.guild.id},
                            {"$unset": {"master_roles": ""}}
                        )
                        reply = discord.Embed(
                            title = "♻ Выполнено",
                            description = f"Все мастер-роли удалены.\nСписок настроек: `{p}settings`",
                            color = mmorpg_col("clover")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    elif role is None:
                        reply = discord.Embed(
                            title = "💢 Роль не распознана",
                            description = f"Вы ввели **{role_s}**, подразумевая роль, но она не была найдена",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    elif role.id not in master_roles:
                        reply = discord.Embed(
                            title = "💢 Не мастер-роль",
                            description = f"<@&{role.id}> не является мастер-ролью.\nСписок Ваших настроек: `{p}settings`",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    else:
                        collection.update_one(
                            {"_id": ctx.guild.id},
                            {"$pull": {"master_roles": {"$in": [role.id]}}},
                            upsert=True
                        )
                        reply = discord.Embed(
                            title = "♻ Выполнено",
                            description = f"Теперь <@&{role.id}> больше не является мастер-ролью\nСписок настроек: `{p}settings`",
                            color = mmorpg_col("clover")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["creator-role"])
    async def creator(self, ctx, option, *, role_s=None):
        cr_lim = 5
        p, cmd = ctx.prefix, ctx.command.name

        if not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title = "💢 Недостаточно прав",
                description = (
                    "Требуемые права:\n"
                    "> Администратор"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)

        else:
            parameters = {
                "add": ["append", "set"],
                "delete": ["remove"]
            }
            parameter = find_alias(parameters, option)
            if parameter is None:
                reply = discord.Embed(
                    title = f"💢 Неизвестный параметр `{option}`",
                    description = (
                        "Попробуйте одну из этих команд:\n"
                        f"> `{p}{cmd} add`\n"
                        f"> `{p}{cmd} delete`"
                    ),
                    color = mmorpg_col("vinous")
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

            elif role_s is None:
                help_texts = {
                    "add": {
                        "desc": "Добавляет роль для создания гильдий",
                        "usage": f"`{p}{cmd} add @Роль`"
                    },
                    "delete": {
                        "desc": "Удаляет роли для создания гильдий",
                        "usage": (
                            f"удаление одной: `{p}{cmd} delete @Роль`\n"
                            f"Удаление всех: `{p}{cmd} delete all`"
                        )
                    }
                }
                help_text = help_texts[parameter]
                reply = discord.Embed(
                    title=f"❔ Как использовать `{p}{cmd} {parameter}`",
                    description=f"**Описание:** {help_text['desc']}\n**Использование:** {help_text['usage']}"
                )
                reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                await ctx.send(embed=reply)

            else:
                collection = db["subguilds"]
                result = collection.find_one(
                    {"_id": ctx.guild.id},
                    projection={"creator_roles": True}
                )
                creator_roles = get_field(result, "creator_roles", default=[])
                del result

                if role_s.lower() != "all":
                    role = detect.role(ctx.guild, role_s)
                if parameter == "add":
                    if role is None:
                        reply = discord.Embed(
                            title = "💢 Роль не распознана",
                            description = f"Вы ввели **{role_s}**, подразумевая роль, но она не была найдена",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    elif role.id in creator_roles:
                        reply = discord.Embed(
                            title = "💢 Уже роль для создания гильдий",
                            description = f"<@&{role.id}> уже является ролью для создания гильдий.\nСписок Ваших настроек: `{p}settings`",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    elif len(creator_roles) >= cr_lim:
                        reply = discord.Embed(
                            title = "💢 Лимит",
                            description = (
                                f"Ролей для создания гильдий на сервере не может быть больше {cr_lim}\n"
                                f"Ваши текущие настройки: `{p}settings`"
                            ),
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    else:
                        collection.update_one(
                            {"_id": ctx.guild.id},
                            {"$addToSet": {"creator_roles": role.id}},
                            upsert=True
                        )
                        reply = discord.Embed(
                            title = "♻ Выполнено",
                            description = f"Теперь <@&{role.id}> является ролю для создания гильдий\nСписок настроек: `{p}settings`",
                            color = mmorpg_col("clover")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                else:
                    if role_s.lower() == "all":
                        collection.update_one(
                            {"_id": ctx.guild.id},
                            {"$unset": {"creator_roles": ""}}
                        )
                        reply = discord.Embed(
                            title = "♻ Выполнено",
                            description = f"Все роли для создания гильдий удалены.\nСписок настроек: `{p}settings`",
                            color = mmorpg_col("clover")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    elif role is None:
                        reply = discord.Embed(
                            title = "💢 Роль не распознана",
                            description = f"Вы ввели **{role_s}**, подразумевая роль, но она не была найдена",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    elif role.id not in creator_roles:
                        reply = discord.Embed(
                            title = "💢 Не роль для создания гильдий",
                            description = f"<@&{role.id}> не является ролью для создания гильдий.\nСписок Ваших настроек: `{p}settings`",
                            color = mmorpg_col("vinous")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)

                    else:
                        collection.update_one(
                            {"_id": ctx.guild.id},
                            {"$pull": {"creator_roles": {"$in": [role.id]}}},
                            upsert=True
                        )
                        reply = discord.Embed(
                            title = "♻ Выполнено",
                            description = f"<@&{role.id}> больше не является ролью для создания гильдий\nСписок настроек: `{p}settings`",
                            color = mmorpg_col("clover")
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)
    
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["ping-count", "pingcount", "pc"])
    async def ping_count(self, ctx, u_search):
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
            collection.update_one(
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
            collection.update_one(
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
    @commands.command(aliases = ["reset-guilds", "resetguilds", "rg", "reset-guild", "resetguild"])
    async def reset_guilds(self, ctx, parameter):
        pr = ctx.prefix
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
            await ctx.send(embed=reply)
        
        elif parameter is None:
            reply = discord.Embed(
                title = "💢 Неверный параметр",
                description = (
                    "Доступные параметры:\n"
                    "> `exp`\n"
                    "> `mentions`\n"
                    "> `reputation`\n"
                    f"Например `{pr}reset-guilds exp`"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

        else:
            result = None
            if parameter != "exp":
                value = 0
                if parameter == "reputation":
                    value = 100
                    desc = "Репутация была сброшена до 100"
                else:
                    desc = "None"
                
                result = collection.find_one_and_update(
                    {"_id": ctx.guild.id},
                    {
                        "$set": {f"subguilds.$[].{parameter}": value}
                    },
                    projection={"log_channel": True}
                )
            elif parameter == "exp":
                desc = "Опыт был обнулён"
                result = collection.find_one(
                    {"_id": ctx.guild.id},
                    projection={
                        "subguilds.name": True,
                        "subguilds.members": True,
                        "log_channel": True
                    }
                )
                if result != None:
                    for sg in result["subguilds"]:
                        zero_data = {}
                        zero_data.update([
                            (f"subguilds.$.members.{key}", {"messages": 0}) for key in sg["members"]])
                        if zero_data != {}:
                            collection.update_one(
                                {"_id": ctx.guild.id, "subguilds.name": sg["name"]},
                                {"$set": zero_data}
                            )
            
            reply = discord.Embed(
                title = "♻ Завершено",
                description = "Сброс закончен",
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

            log = discord.Embed(
                title="♻ Сброс характеристик",
                description=(
                    f"**Модератор:** {ctx.author}\n"
                    f"{desc}"
                )
            )
            lc_id = get_field(result, "log_channel")
            await post_log(ctx.guild, lc_id, log)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @is_developer()
    @commands.command(aliases = ["smart-reset", "sr"])
    async def smart_reset(self, ctx, cycles: int=1, hours: int=1):
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
            await ctx.send(embed=reply)

        else:
            if cycles < 1:
                cycles = 1
            if hours < 1:
                hours = 1
            timer_data = {
                "cycles": cycles,
                "interval": hours,
                "last_at": datetime.datetime.utcnow()
            }
            timer = Timer(ctx.guild.id, timer_data)
            timer.save()
            
            reply = discord.Embed(
                title = "🕑 Таймер запущен",
                description = (
                    f"Сброс очков будет проходить **{cycles}** раз с перерывами по **{hours}** часов\n"
                    f"**Следующее обнуление:** `{timer.next_at + datetime.timedelta(hours=3)}  (UTC+3)`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

            while timer.cycles > 0:
                await asyncio.sleep(timer.time_remaining.total_seconds())
                await do_smart_reset(ctx.guild)
                timer.update()
            timer.delete()

    
    @commands.cooldown(1, 3, commands.BucketType.member)
    @is_developer()
    @commands.command(aliases = ["smart-reset-status", "srs"])
    async def smart_reset_status(self, ctx):
        timer = Timer(ctx.guild.id)
        reply = discord.Embed(
            title="🕑 Статус авто обнуления",
            description=(
                f"**Циклов осталось:** {timer.cycles}\n"
                f"**Интервал:** (в часах) {timer.interval.total_seconds() // 3600}\n"
                f"**Ближайшее обнуление:** {timer.next_at}\n"
            ),
            color=discord.Color.greyple()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed=reply)


    #========== Errors ===========
    @prefix.error
    async def prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** настраивает префикс бота.\n"
                    f"**Использование:** `{p}{cmd} Новый_префикс`\n"
                    f"**Пример:** `{p}{cmd} !`\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @ping_count.error
    async def ping_count_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** настраивает пользователя, упоминания которым нужно учитывать в статистике гильдий\n"
                    f"**Использование:** `{p}{cmd} @Пользователь`\n"
                    f"**Пример:** `{p}{cmd} @MEE6#4876`\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @reset_guilds.error
    async def reset_guilds_error(self, ctx, error):
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
                    f"> `{p}{cmd} mentions` - по упоминаниям\n\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @cmd_channels.error
    async def cmd_channels_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** настраивает каналы реагирования на команды\n"
                    f'**Использование:** `{p}{cmd} #канал-1 #канал-2 ...`\n'
                    f"**Сброс:** `{p}{cmd} delete`\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
    
    @ignore_channels.error
    async def ignore_channels_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** убирает начисление опыта за сообщения в указанных каналах.\n"
                    f'**Использование:** `{p}{cmd} #канал-1 #канал-2 ...`\n'
                    f"**Сброс:** `{p}{cmd} delete`\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @xp_lock.error
    async def xp_lock_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** выключает начисление опыта\n"
                    f'**Использование:** `{p}{cmd} on | off`\n\n'
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @auto_join.error
    async def auto_join_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** когда автоматический вход включен, команда `{p}join` сама определяет гильдию, в которую добавит участника.\n"
                    f'**Использование:** `{p}{cmd} on | off`\n\n'
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @block_leave.error
    async def block_leave_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    f"**Описание:** когда запрет на выход включен, участник не может покинуть свою текущую гильдию.\n"
                    f'**Использование:** `{p}{cmd} on | off`\n\n'
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @members_limit.error
    async def members_limit_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** устанавливает лимит участников во всех гильдиях\n"
                    f'**Использование:** `{p}{cmd} Число`\n'
                    f"**Пример:** `{p}{cmd} 50`\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @guilds_limit.error
    async def guilds_limit_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** устанавливает лимит кланов на сервере\n"
                    f'**Использование:** `{p}{cmd} Число`\n'
                    f"**Пример:** `{p}{cmd} 20`\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @log_channel.error
    async def log_channel_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** настраивает канал для логов и отчётов о действиях с гильдиями.\n"
                    f'**Использование:** `{p}{cmd} #канал`\n'
                    f"**Сброс:** `{p}{cmd} delete`\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @master_role.error
    async def master_role_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** настраивает роли, дающие её обладателям права на создание и редактирование любых гильдий, а также на кики из гильдий и начисление репутации.\n"
                    f"**Добавить мастер-роль:** `{p}{cmd} add @Роль`\n"
                    f"**Сбросить мастер-роль:** `{p}{cmd} delete @Роль`\n"
                    f"**Сбросить все:** `{p}{cmd} delete all`\n\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @creator.error
    async def creator_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** настраивает роли, дающие её обладателям права на создание гильдий.\n"
                    f"**Добавить:** `{p}{cmd} add @Роль`\n"
                    f"**Сбросить одну:** `{p}{cmd} delete @Роль`\n"
                    f"**Сбросить все:** `{p}{cmd} delete all`\n"
                    f"**Разрешить всем:** `{p}{cmd} add @everyone`\n\n"
                    f"**Синонимы:** {display_list(ctx.command.aliases)}"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

def setup(client):
    client.add_cog(setting_system(client))