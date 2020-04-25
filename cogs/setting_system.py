import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import json, os, datetime

import pymongo
from pymongo import MongoClient

app_string = str(os.environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

#---------- Variables ------------
from functions import member_limit

lc_json = "log_channels.json"

#---------- Functions ------------
from functions import has_permissions, get_field, detect, find_alias

# JSON functions
def delete(filename):
    if filename in os.listdir("."):
        os.remove(filename)

def load(filename, default=None):
    if filename in os.listdir("."):
        with open(filename, "r", encoding="utf8") as fff:
            default = json.load(fff)
    return default

def save(data, filename):
    with open(filename, "w", encoding="utf8") as fff:
        json.dump(data, fff)

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

async def read_message(channel, user, t_out, client):
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

async def post_log(guild, log):
    data = load(lc_json, {})
    if not f"{guild.id}" in data:
        collection = db["cmd_channels"]
        result = collection.find_one(
            {"_id": guild.id, "log_channel": {"$exists": True}}
        )
        lc_id = get_field(result, "log_channel")
        data.update([(f"{guild.id}", lc_id)])

        save(data, lc_json)
        del data
    else:
        lc_id = data[f"{guild.id}"]
        del data

    if lc_id is not None:
        channel = guild.get_channel(lc_id)
        await channel.send(embed=log)

class setting_system(commands.Cog):
    def __init__(self, client):
        self.client = client

    #---------- Events -----------
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Setting system cog is loaded")
    
    #---------- Commands ----------
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases=["set", "how-set", "config"])
    async def settings(self, ctx):
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
        else:
            collection = db["cmd_channels"]
            result = collection.find_one({"_id": ctx.guild.id})
            wl_channels = get_field(result, "channels")
            log_channel_id = get_field(result, "log_channel")
            
            if wl_channels is None:
                chan_desc = "> Все каналы\n"
            else:
                chan_desc = ""
                for ID in wl_channels:
                    chan_desc += f"> <#{ID}>\n"
                if chan_desc == "":
                    chan_desc = "> Все каналы\n"
            
            if log_channel_id is None:
                lc_desc = "> Отсутствует"
            else:
                lc_desc = f"> <#{log_channel_id}>"
            
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
                ping_desc = f"{ctx.guild.get_member(pinger_id)}"
            
            if mr_id is None:
                mr_desc = "Отсутствует"
            else:
                mr_desc = f"<@&{mr_id}>"
            
            reply = discord.Embed(
                title = "⚙ Текущие настройки сервера",
                description = (
                    f"**Каналы для команд бота:**\n"
                    f"{chan_desc}\n"
                    f"**Канал логов:**\n"
                    f"{lc_desc}\n\n"
                    f"**Роль мастера гильдий:**\n"
                    f"> {mr_desc}\n\n"
                    f"**Вести подсчёт упоминаний от:**\n"
                    f"> {ping_desc}\n\n"
                    f"**Лимит пользователей на гильдию:**\n"
                    f"> {lim_desc}\n\n"
                    f"-> Список команд: `{pr}help`"
                ),
                color = mmorpg_col("lilac")
            )
            reply.set_thumbnail(url = f"{ctx.guild.icon_url}")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["cmd-channels", "cmdchannels", "cc"])
    async def cmd_channels(self, ctx, text_input):
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
                        f"{desc[:+1000]}"
                        f"Исключение - администраторы 😉"
                    ),
                    color = mmorpg_col("lilac")
                )
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
            collection = db["cmd_channels"]
            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {"$unset": {"log_channel": ""}}
            )
            data = load(lc_json, {})
            data[f"{ctx.guild.id}"] = None
            save(data, lc_json)
            del data
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
            collection = db["cmd_channels"]
            collection.find_one_and_update(
                {"_id": ctx.guild.id},
                {"$set": {"log_channel": channel.id}},
                upsert=True
            )
            data = load(lc_json, {})
            data[f"{ctx.guild.id}"] = channel.id
            save(data, lc_json)
            del data
            reply = discord.Embed(
                title="✅ Настроено",
                description=(
                    f"Теперь отчёты теперь приходят в канал <#{channel.id}>\n"
                    f"Отменить: `{pr}log-channel delete`\n"
                    f"Текущие настройки: `{pr}settings`"
                ),
                color=mmorpg_col("clover")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 10, commands.BucketType.member)
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

                    log = discord.Embed(
                        title="🗑 Удалены все гильдии",
                        description=(
                            f"**Модератор:** {ctx.author}"
                        ),
                        color=discord.Color.dark_red()
                    )
                    await post_log(ctx.guild, log)
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
    @commands.command(aliases = ["master-role", "masterrole", "mr"])
    async def master_role(self, ctx, *, r_search):
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

    @commands.cooldown(1, 10, commands.BucketType.member)
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
            if parameter != "exp":
                value = 0
                if parameter == "reputation":
                    value = 100
                    desc = "Репутация была сброшена до 100"
                else:
                    desc = "None"
                
                collection.find_one_and_update(
                    {"_id": ctx.guild.id},
                    {
                        "$set": {f"subguilds.$[].{parameter}": value}
                    }
                )
            elif parameter == "exp":
                desc = "Опыт был обнулён"
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
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

            log = discord.Embed(
                title="♻ Сброс характеристик",
                description=(
                    f"**Модератор:** {ctx.author}\n"
                    f"{desc}"
                )
            )
            await post_log(ctx.guild, log)

    #========== Errors ===========
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
                    f"**Пример:** `{p}{cmd} @MEE6#4876`"
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
                    f"> `{p}{cmd} mentions` - по упоминаниям"
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
                    f"**Сброс:** `{p}{cmd} delete`"
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
                    "**Описание:** настраивает канал для логов и отчётов\n"
                    f'**Использование:** `{p}{cmd} #канал`\n'
                    f"**Сброс:** `{p}{cmd} delete`"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

def setup(client):
    client.add_cog(setting_system(client))