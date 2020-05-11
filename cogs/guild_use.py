import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os, datetime

import pymongo
from pymongo import MongoClient

app_string = str(os.environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

#---------- Variables ------------
from functions import member_limit

#---------- Functions ------------
from functions import has_roles, get_field, detect, find_alias, Leaderboard, has_permissions
from functions import Server, Guild, search_and_choose, read_message

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

def is_command(word, client):
    word = word.split(maxsplit=1)[0]
    out = False
    for cmd in client.commands:
        group = cmd.aliases
        group.append(cmd.name)
        if word in group:
            out = True
            break
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

class guild_use(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Guild & Stats cog is loaded")
    
    #========= Commands ==========
    @commands.cooldown(1, 20, commands.BucketType.member)
    @commands.command(aliases = ["join-guild", "joinguild", "jg", "join"])
    async def join_guild(self, ctx, *, search):
        pr = ctx.prefix
        collection = db["subguilds"]

        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={
                "subguilds.requests": False,
                "subguilds.members": False,
                "ignore_chats": False
            }
        )
        guild_name = await search_and_choose(get_field(result, "subguilds"), search, ctx.message, ctx.prefix, self.client)

        # GoT event: getting Night Watch data
        nw_members = get_field(result, "night_watch", "members", default=[])

        if guild_name is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = (
                    f"По поиску **{search}** не найдено гильдий\n"
                    f"Список гильдий: `{pr}top`"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif guild_name == 1337:
            pass
        
        # GoT event: if-in-night-watch-check
        elif str(ctx.author.id) in nw_members:
            reply = discord.Embed(
                title = "⚔ Ночной Дозор",
                description = (
                    "Вам запрещено вступать в гильдии.\n"
                    f"-> `{pr}night-watch`"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            result = collection.find_one(
                {
                    "_id": ctx.guild.id,
                    "subguilds.name": guild_name
                },
                projection={
                    "ignore_chats": False
                }
            )
            server_lim = get_field(result, "member_limit", default=member_limit)

            subguild = get_subguild(result, guild_name)
            guild_role_id = subguild["role_id"]
            private = subguild["private"]
            total_places = len(subguild["members"]) + len(subguild["requests"])
            m_lim = get_field(subguild, "limit", default=server_lim)

            if total_places >= m_lim:
                reply = discord.Embed(
                    title = "🛠 Переполнение",
                    description = f"В этой гилдьдии участников и заявок в сумме не может быть больше {m_lim}",
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
                            f"В данный момент Вы состоите в гильдии **{user_guild}**.\n"
                            f"Вам нужно выйти из неё, чтобы зайти в другую, однако, **не забывайте**:\n"
                            f"**->** Ваш счётчик опыта обнуляется при выходе.\n"
                            f"Команда для выхода: `{pr}leave-guild`"
                        )
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

                else:
                    if private and ctx.author.id not in [subguild["leader_id"], subguild["helper_id"]] and not has_permissions(ctx.author, ["administrator"]):
                        collection.find_one_and_update(
                            {"_id": ctx.guild.id, "subguilds.name": guild_name},
                            {"$addToSet": {"subguilds.$.requests": ctx.author.id}},
                            upsert=True
                        )
                        reply = discord.Embed(
                            title = "⏳ Ваш запрос отправлен главе",
                            description = (
                                f"Это закрытая гильдия. Вы станете её участником, как только её глава примет Вашу заявку"
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
                                f"**Все запросы:** `{pr}requests Страница {guild_name}`\n"
                                f"**Важно:** используйте команды на соответствующем сервере"
                            )
                        )
                        log.set_author(name = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                        if subguild["leader_id"] != None:
                            leader = ctx.guild.get_member(subguild["leader_id"])
                            self.client.loop.create_task(knock_dm(leader, ctx.channel, log))
                        if subguild["helper_id"] != None:
                            helper = ctx.guild.get_member(subguild["helper_id"])
                            self.client.loop.create_task(knock_dm(helper, ctx.channel, log))

                    else:
                        collection.find_one_and_update(
                            {"_id": ctx.guild.id, "subguilds.name": guild_name},
                            {
                                "$set": {f"subguilds.$.members.{ctx.author.id}": {"messages": 0}}
                            }
                        )
                        collection.find_one_and_update(
                            {"_id": ctx.guild.id},
                            {"$pull": {"subguilds.$[].requests": {"$in": [ctx.author.id]}}}
                        )

                        await give_join_role(ctx.author, guild_role_id)

                        reply = discord.Embed(
                            title = "✅ Добро пожаловать",
                            description = (
                                f"Вы вступили в гильдию **{guild_name}**\n"
                                f"-> Профиль гильдии: `{pr}guild-info {guild_name}`"
                            ),
                            color = mmorpg_col("clover")
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)

    @commands.cooldown(1, 20, commands.BucketType.member)
    @commands.command(aliases = ["leave-guild", "leaveguild", "lg", "leave"])
    async def leave_guild(self, ctx):
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
                    f"**->** Ваш счётчик опыта в гильдии **{guild_name}** обнулится.\nПродолжить?\n"
                    f"Напишите `да` или `нет`"
                )
            )
            warn_emb.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            warn = await ctx.send(embed = warn_emb)

            wait_for_reply = True
            user_reply = None
            while wait_for_reply:
                msg = await read_message(ctx.channel, ctx.author, 60, self.client)

                if msg is not None:
                    user_reply = msg.content.lower()
                    if (user_reply in no) or (user_reply in yes) or is_command(user_reply, self.client):
                        wait_for_reply = False
                
                else:
                    wait_for_reply = False
            
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
                await warn.delete()

    @commands.cooldown(1, 15, commands.BucketType.member)
    @commands.command(aliases = ["get-guild-role", "give-guild-role", "ggr", "get-role"])
    async def get_guild_role(self, ctx):
        pr = ctx.prefix
        collection = db["subguilds"]
        result = collection.find_one(
            {
                "_id": ctx.guild.id,
                f"subguilds.members.{ctx.author.id}": {"$exists": True}
            },
            projection={
                "subguilds.role_id": True,
                f"subguilds.members.{ctx.author.id}": True
            }
        )
        if result is None or "subguilds" not in result:
            reply = discord.Embed(
                title = "❌ Ошибка",
                description = (
                    "Вас нет ни в одной гильдии\n"
                    f"Список гильдий: `{pr}top`"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        else:
            sg = get_subguild(result, ctx.author.id)
            if sg["role_id"] is None:
                reply = discord.Embed(
                    title = "❌ Упс",
                    description = "У Вашей гильдии не настроена роль для участников",
                    color = mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                if sg["role_id"] not in [r.id for r in ctx.author.roles]:
                    await give_join_role(ctx.author, sg["role_id"])
                    reply = discord.Embed(
                        title = "♻ Выполнено",
                        description = f"Вам была выдана роль гильдии",
                        color = mmorpg_col("clover")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)
                
                else:
                    reply = discord.Embed(
                        title = "❌ Ошиблись",
                        description = f"У Вас уже есть роль гильдии - <@&{sg['role_id']}>",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["guilds"])
    async def top(self, ctx, filtration = "exp", *, extra = "пустую строку"):
        pr = ctx.prefix
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
                    f"> `{pr}top exp`\n"
                    f"> `{pr}top mentions`\n"
                    f"> `{pr}top members`\n"
                    f"> `{pr}top reputation`\n"
                    f"> `{pr}top rating`\n"
                    f"> `{pr}top roles`\n"
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
            server = Server(result["subguilds"])
            del result

            if filtration == "rating":
                desc = "Фильтрация одновременно **по опыту и репутации** - рейтинг гильдий"
                stats = server.rating_pairs()
            
            elif filtration == "exp":
                desc = "Фильтрация **по количеству опыта**"
                stats = server.xp_pairs()
                
            elif filtration == "roles":
                desc = f"Фильтрация **по количеству участников, имеющих роль <@&{role.id}>**"
                stats = []
                for subguild in server.guilds:
                    total = 0
                    for key in subguild["members"]:
                        user_id = int(key)
                        member = ctx.guild.get_member(user_id)
                        if member != None and role in member.roles:
                            total += 1
                    stats.append((subguild["name"], total))
                
            elif filtration == "mentions":
                desc = "Фильтрация **по количеству упоминаний**"
                stats = server.mentions_pairs()

            elif filtration == "members":
                desc = "Фильтрация **по количеству участников**"
                stats = server.member_count_pairs()

            elif filtration == "reputation":
                desc = "Фильтрация **по репутации**"
                stats = server.reputation_pairs()
            
            del server
            lb = Leaderboard(stats)
            lb.sort_values()
            pos = 0

            table = ""
            for pair in lb.pairs:
                pos += 1
                guild_name = anf(pair[0])
                table += f"**{pos})** {guild_name} • **{pair[1]}** {filters[filtration]}\n"
            
            lb = discord.Embed(
                title = f"⚔ Гильдии сервера {ctx.guild.name}",
                description = (
                    f"{desc}\n"
                    f"Подробнее о гильдии: `{pr}guild-info Название`\n"
                    f"Вступить в гильдию: `{pr}join-guild Название`\n\n"
                    f"{table}"
                ),
                color = mmorpg_col("pancake")
            )
            lb.set_thumbnail(url = f"{ctx.guild.icon_url}")
            await ctx.send(embed = lb)

    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["global-top", "globaltop", "glt"])
    async def global_top(self, ctx, page="1"):
        collection = db["subguilds"]

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

            if result is None or "subguilds" not in result:
                reply = discord.Embed(
                    title = f"🌐 Топ всех участников гильдий сервера\n{ctx.guild.name}",
                    description = f"Гильдий нет, топа нет :(",
                    color = mmorpg_col("sky")
                )
                reply.set_thumbnail(url = f"{ctx.guild.icon_url}")
                await ctx.send(embed=reply)
            
            else:
                pairs = Server(result["subguilds"]).all_member_pairs()
                del result
                lb = Leaderboard(pairs, 15)
                del pairs
                lb.sort_values()

                if page > lb.total_pages or page < 1:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = f"Страница не найдена. Всего страниц: **{lb.total_pages}**",
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                
                else:
                    place = lb.pair_index(ctx.author.id)
                    if place is None:
                        auth_desc = "Вас нет в этом топе, так как Вы не состоите ни в одной гильдии"
                    else:
                        auth_desc = f"Ваше место в топе: **{place+1} / {lb.length}**"
                    
                    my_page, pos = lb.get_page(page)
                    total_pages = lb.total_pages
                    del lb
                    desc = ""
                    for pair in my_page:
                        pos += 1
                        user = ctx.guild.get_member(pair[0])
                        desc += f"**{pos})** {anf(user)} • **{pair[1]}** ✨\n"
                    
                    reply = discord.Embed(
                        title = f"🌐 Топ всех участников гильдий сервера\n{ctx.guild.name}",
                        description = f"{auth_desc}\n\n{desc}",
                        color = mmorpg_col("sky")
                    )
                    reply.set_thumbnail(url = f"{ctx.guild.icon_url}")
                    reply.set_footer(text=f"Стр. {page}/{total_pages} | {ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["guild-info", "guildinfo", "gi"])
    async def guild_info(self, ctx, *, search=None):
        pr = ctx.prefix
        collection = db["subguilds"]

        result = collection.find_one({"_id": ctx.guild.id})
        server_lim = get_field(result, "member_limit", default=member_limit)

        if search is None:
            subguild = get_subguild(result, ctx.author.id)
            error_text = (
                "Вас нет в какой-либо гильдии, однако, можно посмотреть профиль конкретной гильдии:\n"
                f"`{pr}guild-info Название гильдии`\n"
                f"Список гильдий: `{pr}top`"
            )
        else:
            guild_name = await search_and_choose(get_field(result, "subguilds"), search, ctx.message, ctx.prefix, self.client)
            if guild_name not in [None, 1337]:
                subguild = get_subguild(result, guild_name)
            else:
                subguild = guild_name

            error_text = (
                f"По поиску **{search}** не было найдено гильдий\n"
                f"Список гильдий: `{pr}top`"
            )
            
        if subguild is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = error_text,
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif subguild == 1337:
            pass

        else:
            local_lim = get_field(subguild, "limit", default=server_lim)
            subguild = Guild(subguild)

            total_mes = subguild.xp()
            total_memb = len(subguild.members)
            
            reply = discord.Embed(
                title = subguild.name,
                description = (
                    f"{subguild.description}\n"
                    f"**->** Топ участников: `{pr}guild-top 1 {subguild.name}`"
                ),
                color = mmorpg_col("sky")
            )
            reply.set_thumbnail(url = subguild.avatar_url)
            if subguild.leader_id != None:
                leader = ctx.guild.get_member(subguild.leader_id)
                reply.add_field(name = "💠 Владелец", value = f"> {anf(leader)}", inline=False)
            if subguild.helper_id != None:
                helper = ctx.guild.get_member(subguild.helper_id)
                reply.add_field(name = "🔰 Помощник", value = f"> {anf(helper)}", inline=False)
            reply.add_field(name = "👥 Всего участников", value = f"> {total_memb} из {local_lim}", inline=False)
            reply.add_field(name = "✨ Всего опыта", value = f"> {total_mes}", inline=False)
            reply.add_field(name = "🔅 Репутация", value = f"> {subguild.reputation}", inline=False)
            if subguild.mentions > 0:
                reply.add_field(name = "📯 Упоминаний", value = f"> {subguild.mentions}", inline=False)
            if subguild.role_id != None:
                reply.add_field(name = "🎗 Роль", value = f"> <@&{subguild.role_id}>", inline=False)
            if subguild.private:
                reply.add_field(name = "🔒 Приватность", value = "> Вступление по заявкам")
            await ctx.send(embed = reply)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["guild-members", "guildmembers", "gm", "guild-top", "gt"])
    async def guild_top(self, ctx, page_num="1", *, search=None):
        pr = ctx.prefix
        collection = db["subguilds"]
        interval = 15

        if not page_num.isdigit():
            reply = discord.Embed(
                title = "💢 Неверный аргумент",
                description = (
                    f"**{page_num}** должно быть целым числом\n"
                    f"Команда: `{pr}{ctx.command.name} Номер_страницы Гильдия`"
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
            subguild = None
            if search is None:
                subguild = get_subguild(result, ctx.author.id)
                error_text = (
                    "Вас нет в какой-либо гильдии. Можно посмотреть топ конкретной гильдии:\n"
                    f"`{pr}guild-top Страница Название`\n"
                    f"Список гильдий: `{pr}top`"
                )
            else:
                guild_name = await search_and_choose(get_field(result, "subguilds"), search, ctx.message, ctx.prefix, self.client)
                if guild_name not in [None, 1337]:
                    subguild = get_subguild(result, guild_name)
                else:
                    subguild = guild_name

                error_text = (
                    f"По поиску **{search}** не было найдено гильдий\n"
                    f"Список гильдий: `{pr}top`"
                )

            if subguild is None:
                reply = discord.Embed(
                    title = "💢 Упс",
                    description = error_text,
                    color = mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            elif subguild == 1337:
                pass

            else:
                subguild = Guild(subguild)
                total_memb = len(subguild.members)
                if total_memb > 0 and interval * (page_num - 1) >= total_memb:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = f"Страница не найдена. Всего страниц: **{(total_memb - 1)//interval + 1}**"
                    )
                    await ctx.send(embed = reply)
                else:
                    if total_memb == 0:
                        page_num = 1
                    pairs = subguild.members_as_pairs()
                    subguild.forget_members()
                    lb = Leaderboard(pairs, 15)
                    del pairs
                    lb.sort_values()
                    
                    my_page, pos = lb.get_page(page_num)
                    total_pages = lb.total_pages
                    del lb
                    desc = ""
                    for pair in my_page:
                        pos += 1
                        user = ctx.guild.get_member(pair[0])
                        desc += f"**{pos}.** {anf(user)} • **{pair[1]}** ✨\n"
                    
                    lb = discord.Embed(
                        title = f"👥 Участники гильдии {subguild.name}",
                        description = desc,
                        color = mmorpg_col("clover")
                    )
                    lb.set_footer(text=f"Стр. {page_num}/{total_pages}")
                    lb.set_thumbnail(url = subguild.avatar_url)
                    await ctx.send(embed = lb)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["user-guild", "userguild", "ug", "user-info", "userinfo", "ui"])
    async def user_guild(self, ctx, user_s = None):
        pr = ctx.prefix
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
                    description = f"Вы можете посмотреть список гильдий здесь: `{pr}guilds`",
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

    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["count-roles", "countroles", "cr"])
    async def count_roles(self, ctx, *, text_data):
        pr = ctx.prefix
        collection = db["subguilds"]

        search, text = sep_args(text_data)
        raw_roles = text.split()
        
        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={
                "master_role_id": True,
                "subguilds.name": True,
                "subguilds.members": True,
                "subguilds.leader_id": True,
                "subguilds.helper_id": True
            }
        )
        guild_name = await search_and_choose(get_field(result, "subguilds"), search, ctx.message, ctx.prefix, self.client)

        if guild_name is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = f"По поиску **{search}** не найдено гильдий",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif guild_name == 1337:
            pass
        
        else:
            roles = [detect.role(ctx.guild, s) for s in raw_roles]
            if None in roles or roles == []:
                reply = discord.Embed(
                    title = f"💢 Ошибка",
                    description = (
                        f"В качестве ролей укажите их **@Упоминания** или **ID**\n"
                        f'**Пример:** `{pr}count-roles [{guild_name}] {ctx.guild.default_role.id}`'
                    )
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            else:
                subguild = get_subguild(result, guild_name)
                del result

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
    
    #--------- Errors ----------
    @join_guild.error
    async def join_guild_error(self, ctx, error):
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

    @count_roles.error
    async def count_roles_error(self, ctx, error):
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

def setup(client):
    client.add_cog(guild_use(client))