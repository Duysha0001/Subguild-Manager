import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import os, datetime


from pymongo import MongoClient
app_string = str(os.environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

#----------------------------+
#         Constants          |
#----------------------------+
from functions import cool_servers, owner_ids
from db_models import guild_limit, member_limit


#----------------------------+
#         Functions          |
#----------------------------+
from functions import find_alias, is_command, EmergencyExit
from db_models import Server, ResponseConfig
from custom_converters import IntConverter

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


async def post_log(guild, channel_id, log):
    if channel_id is not None:
        channel = guild.get_channel(channel_id)
        if channel is not None:
            await channel.send(embed=log)


async def do_smart_reset(server):     # BETA
    sconf = Server(server.id,
                {"subguilds.name": True,
                "subguilds.members": True,
                "log_channel": True})
    res = sconf.smart_reset()
    if sconf.log_channel is not None:
        desc = ""
        for name, sp in res:
            desc += f"> {name}: `+{sp}` 🪐\n"

        log = discord.Embed(
            title="♻ Сброс опыта и начисление супер-поинтов",
            description=f"Проведён автоматически\n{desc}"
        )
        await post_log(server, sconf.log_channel, log)


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

    #----------------------------+
    #           Events           |
    #----------------------------+
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
    
    #----------------------------+
    #          Commands          |
    #----------------------------+
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases=["set", "how-set", "config"])
    async def settings(self, ctx):
        rconf = ResponseConfig(ctx.guild.id)
        
        if rconf.cmd_channels == []:
            chan_desc = "> Все каналы\n"
        else:
            chan_desc = ""
            for ID in rconf.cmd_channels:
                chan_desc += f"> <#{ID}>\n"
            if chan_desc == "":
                chan_desc = "> Все каналы\n"
        
        sconf = Server(ctx.guild.id, {"subguilds": False})

        if sconf.ignore_channels == []:
            ig_desc = "> Отсутствуют\n"
        else:
            ig_desc = ""
            for ID in sconf.ignore_channels:
                ig_desc += f"> <#{ID}>\n"
        
        if sconf.log_channel is None:
            lc_desc = "> Отсутствует"
        else:
            lc_desc = f"> <#{sconf.log_channel}>"
        
        if sconf.mentioner_id is None:
            ping_desc = "> выключено"
        else:
            ping_desc = f"> {ctx.guild.get_member(sconf.mentioner_id)}"
        
        if sconf.master_roles == []:
            mr_desc = "> Отсутствуют"
        else:
            mr_desc = ""
            for ID in sconf.master_roles:
                mr_desc += f"> <@&{ID}>\n"
        
        if sconf.creator_roles == []:
            cr_desc = "> Отсутствуют"
        else:
            cr_desc = ""
            for ID in sconf.creator_roles:
                cr_desc += f"> <@&{ID}>\n"
        
        if sconf.xp_locked:
            xpl_desc = "✅ Включена"
        else:
            xpl_desc = "❌ Выключена"
        if sconf.auto_join:
            aj_desc = "✅ Включен"
        else:
            aj_desc = "❌ Выключен"
        if sconf.block_leave:
            lb_desc = "✅ Включен"
        else:
            lb_desc = "❌ Выключен"

        reply = discord.Embed(
            title = "⚙ Текущие настройки сервера",
            description = (
                f"**Префикс:** `{rconf.prefix}`"
            ),
            color = mmorpg_col("lilac")
        )
        reply.add_field(name="**Каналы для команд бота**", value=f"{chan_desc}")
        reply.add_field(name="**Каналы игнорирования опыта**", value=f"{ig_desc}")
        reply.add_field(name="**Канал логов**", value=f"{lc_desc}", inline=False)
        reply.add_field(name="**Роли мастера гильдий:**", value=f"{mr_desc}")
        reply.add_field(name="**Роли для создания гильдий**", value=f"{cr_desc}")
        reply.add_field(name="**Вести подсчёт упоминаний от**", value=f"{ping_desc}", inline=False)
        reply.add_field(name="**Лимит гильдий на сервере**", value=f"> {sconf.guild_limit}")
        reply.add_field(name="**Лимит пользователей на гильдию**", value=f"> {sconf.member_limit}")
        reply.add_field(name="**Лимит создаваемых одним человеком гильдий**", value=f"> {sconf.creator_limit}", inline=False)
        reply.add_field(name="**Блокировка опыта**", value=f"> {xpl_desc}")
        reply.add_field(name="**Авто вход в гильдии**", value=f"> {aj_desc}")
        reply.add_field(name="**Запрет на выход из гильдий**", value=f"> {lb_desc}")

        reply.set_thumbnail(url = f"{ctx.guild.icon_url}")
        await ctx.send(embed = reply)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases = ["set-prefix", "setprefix", "sp", "gm-prefix"],
        description="настраивает префикс бота.",
        usage="Новый_префикс",
        brief="!" )
    async def prefix(self, ctx, text_input):
        text_input = text_input[:30]
        ResponseConfig(ctx.guild.id, dont_request_bd=True).set_prefix(text_input)
        reply = discord.Embed(
            title="✅ Настроено",
            description=f"Новый префикс: {text_input}\nТекущие настройки: `{text_input}settings`",
            color=mmorpg_col("clover")
        )
        reply.set_footer(text = str(ctx.author), icon_url = str(ctx.author.avatar_url))
        await ctx.send(embed = reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases = ["cmd-channels", "cmdchannels", "cc"],
        description="настраивает каналы реагирования на команды.",
        usage='#канал-1 #канал-2 ...\ndelete  (сбросить настройки)' )
    async def cmd_channels(self, ctx, *, text_input):
        rconf = ResponseConfig(ctx.guild.id, dont_request_bd=True)
        raw_ch = text_input.split()
        if "delete" == raw_ch[0].lower():
            rconf.remove_all_cmd_channels()
            reply = discord.Embed(
                title = "♻ | Каналы сброшены",
                description = "Теперь я реагирую на команды во всех каналах",
                color = mmorpg_col("clover")
            )
            await ctx.send(embed = reply)

        else:
            channel_ids = []
            for s in raw_ch:
                # Converting string to channel
                tcc = commands.TextChannelConverter()
                try:
                    ch = await tcc.convert(ctx, s)
                except:
                    ch = None
                
                if ch is None:
                    pass
                elif not ch.id in channel_ids:
                    channel_ids.append(ch.id)

            channel_ids = channel_ids[:+30]
            if channel_ids != []:
                rconf.set_cmd_channels(channel_ids)
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
            
            else:
                reply = discord.Embed(color=discord.Color.dark_red())
                reply.title = "❌ | Не удалось распознать каналы"
                reply.description = "Либо Вы указали текстовые каналы неверно, либо у меня нет прав видеть их."
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(embed = reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases=["ignore-channels", "ignore", "ic"],
        description="блокирует начисление опыта за сообщения в указанных каналах.",
        usage='#канал-1 #канал-2 ...\ndelete  (сброс настроек)' )
    async def ignore_channels(self, ctx, *, text_input):
        sconf = Server(ctx.guild.id, dont_request_bd=True)
        raw_ch = text_input.split()
        if "delete" == raw_ch[0].lower():
            sconf.set_ignore_channels([])
            reply = discord.Embed(
                title = "♻ | Каналы сброшены",
                description = "Теперь я начисляю опыт во всех каналах.",
                color = mmorpg_col("clover")
            )
            await ctx.send(embed = reply)

        else:
            channel_ids = []
            for s in raw_ch:
                # Converting string to channel
                tcc = commands.TextChannelConverter()
                try:
                    ch = await tcc.convert(ctx, s)
                except:
                    ch = None
                
                if ch is None:
                    pass
                elif not ch.id in channel_ids:
                    channel_ids.append(ch.id)

            channel_ids = channel_ids[:+30]
            if channel_ids != []:
                sconf.set_ignore_channels(channel_ids)
                desc = ""
                for ch in channel_ids:
                    desc += f"> <#{ch}>\n"
                reply = discord.Embed(color = mmorpg_col("lilac"))
                reply.title = "🛠 | Каналы настроены"
                reply.description = (
                        f"Теперь я начисляю опыт только в этих каналах:\n"
                        f"{desc}"
                    )
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(embed = reply)
            
            else:
                reply = discord.Embed(color=discord.Color.dark_red())
                reply.title = "❌ | Не удалось распознать каналы"
                reply.description = "Либо Вы указали текстовые каналы неверно, либо у меня нет прав видеть их."
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(embed = reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases=["xp-lock", "freeze"],
        description="блокирует начисление опыта на всём сервере.",
        usage='on\noff' )
    async def xp_lock(self, ctx, option):
        p = ctx.prefix
        option = option.lower()
        sconf = Server(ctx.guild.id, dont_request_bd=True)
        if option in ["on", "вкл"]:
            sconf.set_xp_lock(True)
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
            sconf.set_xp_lock(False)
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
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases=["auto-join", "join-filter", "aj"],
        description="когда автоматический вход включен, команда `join` сама определяет гильдию, в которую попадёт участник.",
        usage='on\noff' )
    async def auto_join(self, ctx, option):
        p = ctx.prefix
        option = option.lower()
        sconf = Server(ctx.guild.id, dont_request_bd=True)
        if option in ["on", "вкл"]:
            sconf.set_auto_join(True)
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
            sconf.set_auto_join(False)
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
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases=["block-leave", "bl", "blockleave"],
        description="когда запрет на выход включен, участник не может покинуть свою текущую гильдию.",
        usage='on\noff' )
    async def block_leave(self, ctx, option):
        p = ctx.prefix
        option = option.lower()
        sconf = Server(ctx.guild.id, dont_request_bd=True)
        if option in ["on", "вкл"]:
            sconf.set_block_leave(True)
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
            sconf.set_block_leave(False)
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
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases=["log-channel", "logchannel", "logs-channel", "lc"],
        description="настраивает канал для логов и отчётов о действиях с гильдиями.",
        usage='#канал\ndelete  (сброс настроек)' )
    async def log_channel(self, ctx, *, channel):
        pr = ctx.prefix
        if channel.lower() == "delete":
            Server(ctx.guild.id, {"_id": True}).set_log_channel(None)
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
        
        else:
            channel = await commands.TextChannelConverter().convert(ctx, channel)

            Server(ctx.guild.id, dont_request_bd=True).set_log_channel(channel.id)

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
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases=["members-limit", "memberslimit", "ml"],
        description="устанавливает лимит участников по всем гильдиям. У каждой гильдии отдельно может быть настроен свой лимит, но не выше этого.",
        usage='Число',
        brief="50" )
    async def members_limit(self, ctx, lim: IntConverter):
        pr = ctx.prefix
        if lim > member_limit or lim < 0:
            reply = discord.Embed(
                title = "❌ Ошибка",
                description = f"Лимит пользователей не может превышать **{member_limit}** на гильдию",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            Server(ctx.guild.id, dont_request_bd=True).set_member_limit(lim)
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
    @commands.has_permissions(administrator=True)
    @commands.command(
        name="guild-limit", aliases=["guildlimit", "gl"],
        description="устанавливает лимит кланов на сервере.",
        usage='Число',
        brief="20" )
    async def guilds_limit(self, ctx, lim: IntConverter):
        pr = ctx.prefix
        if lim > guild_limit or lim < 0:
            reply = discord.Embed(
                title = "❌ Ошибка",
                description = f"Лимит кланов не может превышать **{guild_limit}**",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            Server(ctx.guild.id, dont_request_bd=True).set_guild_limit(lim)
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


    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(aliases=["clear-guilds", "delete-all-guilds"])
    async def clear_guilds(self, ctx):
        reply = discord.Embed(
            title="🛠 Подтверждение",
            description=(
                "Использовав эту команду Вы удалите **все** гильдии этого сервера. Продолжить?\n"
                "Напишите `да` или `нет`"
            )
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        sys_msg = await ctx.send(embed=reply)

        yes = ["yes", "y", "да", "1"]
        no = ["no", "n", "нет", "0"]
        def check(msg):
            if msg.channel.id != ctx.channel.id or msg.author.id != ctx.author.id:
                return False
            _1st_word = msg.content.split(maxsplit=1)[0]
            del msg
            if _1st_word.lower() in [*yes, *no]:
                return True
            if is_command(_1st_word, ctx.prefix, self.client):
                raise EmergencyExit()
            return False
        # Read message
        reply_text = None
        try:
            msg = await self.client.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            await ctx.send(f"{ctx.author.mention}, Вы слишком долго не отвечали. Выход отменён.")
        else:
            reply_text = msg.content.lower()
        
        # Delete sysmsg
        try:
            await sys_msg.delete()
        except:
            pass
        
        if reply_text is not None:
            if reply_text in no:
                reply = discord.Embed(
                    title="❌ | Отмена",
                    description="Действие отменено",
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed=reply)

            elif reply_text in yes:
                if reply_text in ["yes", "1", "да"]:
                    sconf = Server(ctx.guild.id, {"log_channel": True})
                    sconf.delete_all_guilds()
                    reply = discord.Embed(
                        title="♻ | Выполнено",
                        description = "Все гильдии удалены",
                        color=mmorpg_col("clover")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)

                    log = discord.Embed(
                        title="🗑 Удалены все гильдии",
                        description=(
                            f"**Модератор:** {ctx.author}"
                        ),
                        color=discord.Color.dark_red()
                    )
                    await post_log(ctx.guild, sconf.log_channel, log)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        name="master-role", aliases=["master-roles", "masterrole", "mr"],
        description="настраивает роли, дающие её обладателям права на создание и редактирование любых гильдий, а также на кик из гильдий и начисление репутации.",
        usage="add @Роль  (добавить мастер-роль)\ndelete @Роль  (сбросить)\ndelete all  (сбросить всё)" )
    async def master_role(self, ctx, option, *, role_s=None):
        mr_lim = 5
        p, cmd = ctx.prefix, ctx.command.name

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
            sconf = Server(ctx.guild.id, {"master_roles": True})
            ghost_roles = [rid for rid in sconf.master_roles if ctx.guild.get_role(rid) is None]
            if ghost_roles != []:
                sconf.remove_master_roles(*ghost_roles)

            if role_s.lower() != "all":
                role = await commands.RoleConverter().convert(ctx, role_s)
            if parameter == "add":
                if role.id in sconf.master_roles:
                    reply = discord.Embed(
                        title = "💢 | Уже мастер-роль",
                        description = f"<@&{role.id}> уже является мастер-ролью.\nСписок Ваших настроек: `{p}settings`",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

                elif len(sconf.master_roles) - len(ghost_roles) >= mr_lim:
                    reply = discord.Embed(
                        title = "💢 | Лимит",
                        description = (
                            f"Мастер-ролей на сервере не может быть больше {mr_lim}\n"
                            f"Ваши текущие настройки: `{p}settings`"
                        ),
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

                else:
                    sconf.add_master_role(role.id)
                    reply = discord.Embed(
                        title = "♻ | Выполнено",
                        description = f"Теперь <@&{role.id}> является мастер-ролью\nСписок настроек: `{p}settings`",
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

            else:
                if role_s.lower() == "all":
                    sconf.remove_master_roles(*sconf.master_roles)
                    reply = discord.Embed(
                        title = "♻ | Выполнено",
                        description = f"Все мастер-роли удалены.\nСписок настроек: `{p}settings`",
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

                elif role.id not in sconf.master_roles:
                    reply = discord.Embed(
                        title = "💢 | Не мастер-роль",
                        description = f"<@&{role.id}> не является мастер-ролью.\nСписок Ваших настроек: `{p}settings`",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

                else:
                    sconf.remove_master_roles(role.id)
                    reply = discord.Embed(
                        title = "♻ | Выполнено",
                        description = f"Теперь <@&{role.id}> больше не является мастер-ролью\nСписок настроек: `{p}settings`",
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases = ["creator-role"],
        description="настраивает роли, дающие её обладателям права на создание гильдий.",
        usage="add @Роль  (добавить роль создателя)\ndelete @Роль  (сбросить)\ndelete all  (сбросить всё)",
        brief="add @Moderator\nadd @everyone  (разрешить всем создавать гильдии)" )
    async def creator(self, ctx, option, *, role_s=None):
        cr_lim = 5
        p, cmd = ctx.prefix, ctx.command.name

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
            sconf = Server(ctx.guild.id, {"creator_roles": True})
            ghost_roles = [rid for rid in sconf.creator_roles if ctx.guild.get_role(rid) is None]
            if ghost_roles != []:
                sconf.remove_creator_roles(*ghost_roles)

            if role_s.lower() != "all":
                role = await commands.RoleConverter().convert(ctx, role_s)
            if parameter == "add":
                if role.id in sconf.creator_roles:
                    reply = discord.Embed(
                        title = "💢 | Уже роль для создания гильдий",
                        description = f"<@&{role.id}> уже является ролью для создания гильдий.\nСписок Ваших настроек: `{p}settings`",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

                elif len(sconf.creator_roles) - len(ghost_roles) >= cr_lim:
                    reply = discord.Embed(
                        title = "💢 | Лимит",
                        description = (
                            f"Ролей для создания гильдий на сервере не может быть больше {cr_lim}\n"
                            f"Ваши текущие настройки: `{p}settings`"
                        ),
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

                else:
                    sconf.add_creator_role(role.id)
                    reply = discord.Embed(
                        title = "♻ | Выполнено",
                        description = f"Теперь <@&{role.id}> является ролю для создания гильдий\nСписок настроек: `{p}settings`",
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

            else:
                if role_s.lower() == "all":
                    sconf.remove_creator_roles(*sconf.creator_roles)
                    reply = discord.Embed(
                        title = "♻ | Выполнено",
                        description = f"Все роли для создания гильдий удалены.\nСписок настроек: `{p}settings`",
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

                elif role.id not in sconf.creator_roles:
                    reply = discord.Embed(
                        title = "💢 | Не роль для создания гильдий",
                        description = f"<@&{role.id}> не является ролью для создания гильдий.\nСписок Ваших настроек: `{p}settings`",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

                else:
                    sconf.remove_creator_roles(role.id)
                    reply = discord.Embed(
                        title = "♻ | Выполнено",
                        description = f"<@&{role.id}> больше не является ролью для создания гильдий\nСписок настроек: `{p}settings`",
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)
    

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases=["creator-limit", "crelim"],
        description="устанавливает ограничение количества создаваемых одним человеком кланов. Не касается администрации и обладателей мастер-роли.",
        usage="Число",
        brief="1" )
    async def creator_limit(self, ctx, lim: IntConverter):
        pr = ctx.prefix
        if lim > guild_limit or lim < 0:
            reply = discord.Embed(
                title = "❌ | Ошибка",
                description = f"Ограничение создаваемых участником кланов не может превышать **{guild_limit}**",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            Server(ctx.guild.id, dont_request_bd=True).set_creator_limit(lim)
            reply = discord.Embed(
                title = "✅ | Настроено",
                description = (
                    f"Текущее ограничение количества создаваемых участником кланов: **{lim}**\n"
                    f"❗Не распространяется на администрацию и обладателей мастер-роли\n"
                    f"Отчёт о настройках: `{pr}settings`"
                ),
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases = ["ping-count", "pingcount", "pc"],
        description="настраивает пользователя, чьи упоминания будут накапливаться гильдиями.",
        usage="@Пользователь",
        brief="@MEE6#4876" )
    async def ping_count(self, ctx, *, member):
        if member.lower() == "delete":
            member = None
            desc = "Больше не ведётся подсчёт упоминаний"
        else:
            member = await commands.MemberConverter().convert(ctx, member)
            desc = f"Теперь в гильдиях ведётся подсчёт пингов от **{member}**"
            member = member.id
        Server(ctx.guild.id, dont_request_bd=True).set_mentioner_id(member)
        reply = discord.Embed(
            title = "✅ | Настроено",
            description = desc,
            color = mmorpg_col("clover")
        )
        await ctx.send(embed = reply)


    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases = ["reset-guilds", "resetguilds", "rg", "reset-guild", "resetguild"],
        description="обнуляет топ по указанному фильтру.",
        usage="exp\nreputation\nmentions" )
    async def reset_guilds(self, ctx, parameter):
        pr = ctx.prefix
        params = {
            "exp": ["xp", "опыт"],
            "mentions": ["pings", "упоминания", "теги"],
            "reputation": ["репутация"]
        }
        parameter = find_alias(params, parameter)

        if parameter is None:
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
            proj = {"log_channel": True}
            if parameter is "exp": proj["subguilds.members"] = True
            sconf = Server(ctx.guild.id, proj)
            del proj
            desc = "???"

            if parameter is "exp":
                sconf.reset_xp()
                desc = "Опыт обнулён"
            elif parameter is "reputation":
                sconf.reset_reputation()
                desc = "Репутация сброшена"
            elif parameter is "mentions":
                sconf.reset_mentions()
                desc = "Упоминания обнулены"
            reply = discord.Embed(
                title = "♻ | Завершено",
                description = desc,
                color = mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

            log = discord.Embed(
                title="♻ | Сброс характеристик",
                description=(
                    f"**Модератор:** {ctx.author}\n"
                    f"{desc}"
                ),
                color=discord.Color.red()
            )
            
            await post_log(ctx.guild, sconf.log_channel, log)


    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.is_owner()
    @commands.command(aliases = ["smart-reset", "sr"])
    async def smart_reset(self, ctx, cycles: int=1, hours: int=1):
        if not ctx.author.guild_permissions.administrator:
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
    @commands.is_owner()
    @commands.command(aliases = ["smart-reset-status", "srs"])
    async def smart_reset_status(self, ctx):
        timer = Timer(ctx.guild.id)
        reply = discord.Embed(
            title="🕑 Статус авто обнуления",
            description=(
                f"**Циклов осталось:** {timer.cycles}\n"
                f"**Интервал:** (в часах) {timer.interval.total_seconds() // 3600}\n"
                f"**Ближайшее обнуление:** {timer.next_at + datetime.timedelta(hours=3)} (UTC+3)\n"
            ),
            color=discord.Color.greyple()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed=reply)



def setup(client):
    client.add_cog(setting_system(client))