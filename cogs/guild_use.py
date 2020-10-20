import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os, datetime


#----------------------------+
#         Constants          |
#----------------------------+
from functions import cool_servers, CustomColors
from db_models import guild_limit, member_limit
colors = CustomColors()

#----------------------------+
#         Exceptions         |
#----------------------------+
from custom_converters import IsNotSubguild
from functions import EmergencyExit

#----------------------------+
#         Functions          |
#----------------------------+
from functions import find_alias, abr, anf, vis_num, give_join_role, remove_join_role, ask_to_choose, is_command
from db_models import Server, Guild
from custom_converters import IntConverter


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


async def trysend(messageable, *args, **kwargs):
    try:
        await messageable.send(*args, **kwargs)
    except:
        pass


class PseudoParam:
    def __init__(self, name):
        self.name = name

#-----------------------------------+
#               Cog                 |
#-----------------------------------+
class guild_use(commands.Cog):
    def __init__(self, client):
        self.client = client


    #----------------------------+
    #           Events           |
    #----------------------------+
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Guild & Stats cog is loaded")
    
    
    #----------------------------+
    #          Commands          |
    #----------------------------+
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        aliases=["join-guild", "joinguild", "jg", "join"],
        description="вход в гильдию",
        usage="Название гильдии",
        brief="Цари морей" )
    async def join_guild(self, ctx, *, search=None):
        pr = ctx.prefix
        sconf = Server(ctx.guild.id, {"subguilds.name": True, "auto_join": True, f"subguilds.members.{ctx.author.id}": True})
        # In case member's in guild
        g = sconf.get_guild(ctx.author.id)
        if g is not None:
            reply = discord.Embed(color=discord.Color.dark_red())
            reply.title = "❌ | Притормозите"
            reply.description = (
                f"Вы уже состоите в гильдии **{anf(g.name)}**\n"
                f"Вы можете выйти из неё, потеряв весь свой опыт: `{pr}leave`\n"
                f"После выхода Вы сможете зайти куда хочется."
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        #
        # In case auto join is enabled
        #
        elif sconf.auto_join:
            sconf = Server(ctx.guild.id, {
                "subguilds.members": True, "subguilds.limit": True, "member_limit": True, "subguilds.leader_id": True,
                "subguilds.requests": True, "subguilds.private": True, "subguilds.name": True, "subguilds.helper_id": True})
            spare_guild = None
            spare_private_guild = None
            # Performing guild analisys
            for g in sconf.guilds:
                if g.member_count + g.request_count < g.limit:
                    if not g.private: # Searching a spare non-private guild
                        if spare_guild is None:
                            spare_guild = g
                        elif g.member_count < spare_guild.member_count:
                            spare_guild = g
                    else: # Searching a spare private guild
                        if spare_private_guild is None:
                            spare_private_guild = g
                        elif g.member_count < spare_private_guild.member_count:
                            spare_private_guild = g
            g.__guilds = []
            # If there's a non-private spare guild
            if spare_guild is not None:
                spare_guild.join(ctx.author.id)
                # Response
                reply = discord.Embed(color=colors.gold)
                reply.title = "⚔ | Добро пожаловать"
                reply.description = (
                    "**Администрация включила авто-распределение.**\n"
                    f"Вы автоматически стали участником **{anf(spare_guild.name)}**."
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
            # Worst cases
            else:
                # If there isn't even a spare private guild
                if spare_private_guild is None:
                    reply = discord.Embed(color=discord.Color.dark_red())
                    reply.title = "❌ | Свободных гильдий не осталось"
                    reply.description = "Попробуйте в другой раз."
                    reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=reply)
                # If there's a spare private guild
                else:
                    spare_private_guild.request_join(ctx.author.id)
                    # Say to guild leader
                    if ctx.author.id not in spare_private_guild.requests:
                        notif = discord.Embed()
                        notif.title = f"📥 | Запрос на вступление | {ctx.guild.name}"
                        notif.description = (
                            f"**В гильдию** {anf(spare_private_guild.name)}\n"
                            f"**Отправил:** {anf(ctx.author)}\n"
                            f"**->** [Перейти]({ctx.message.jump_url})\n\n"
                            f"**Все запросы:** `{pr}requests 1 {spare_private_guild.name}`"
                        )
                        leader = ctx.guild.get_member(spare_private_guild.leader_id)
                        await trysend(leader, embed=notif)
                        if spare_private_guild.helper_id is not None:
                            helper = ctx.guild.get_member(spare_private_guild.helper_id)
                            await trysend(helper, embed=notif)
                    # Explain what does joining a private guild mean
                    reply = discord.Embed(color=colors.paper)
                    reply.title = "🛠 | Ваш запрос отправлен главе"
                    reply.description = (
                        "**Администрация включила автоматическое распределение.**\n"
                        f"Мест в открытых гильдиях не осталось, поэтому Ваш запрос отправлен в **{anf(spare_private_guild.name)}**.\n"
                        "Это закрытая гильдия, дождитесь рассмотрения Вашей заявки."
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=reply)
        #
        # Free join
        #
        elif search is None:
            raise commands.MissingRequiredArgument(PseudoParam("search"))
        else:
            guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, pr)
            if guild_name is None:
                raise IsNotSubguild(search)
            elif isinstance(guild_name, EmergencyExit):
                pass
            else:
                g = Guild(ctx.guild.id, name=guild_name, attrs_projection={
                    "private": True, "limit": True, "leader_id": True, "helper_id": True,
                    "members": True, "requests": True, "name": True
                })
                g.__members = []
                # Joining an opened guild
                if not g.private:
                    if g.member_count + g.request_count >= g.limit:
                        reply = discord.Embed(color=discord.Color.dark_red())
                        reply.title = "❌ | Переполнение"
                        reply.description = f"В этой гильдии запросов и участников не может быть больше **{g.limit}**"
                        reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                        await ctx.send(embed=reply)
                    else:
                        g.join(ctx.author.id)
                        # response
                        reply = discord.Embed(color=colors.gold)
                        reply.title = "⚔ | Добро пожаловать"
                        reply.description = f"Теперь Вы участник **{anf(g.name)}**."
                        reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                        await ctx.send(embed=reply)
                # Joining a private guild
                else:
                    g.request_join(ctx.author.id)
                    # Say to guild leader
                    if ctx.author.id not in g.requests:
                        notif = discord.Embed()
                        notif.title = f"📥 | Запрос на вступление | {ctx.guild.name}"
                        notif.description = (
                            f"**В гильдию** {anf(g.name)}\n"
                            f"**Отправил:** {anf(ctx.author)}\n"
                            f"**->** [Перейти]({ctx.message.jump_url})\n\n"
                            f"**Все запросы:** `{pr}requests 1 {g.name}`"
                        )
                        leader = ctx.guild.get_member(g.leader_id)
                        await trysend(leader, embed=notif)
                        if g.helper_id is not None:
                            helper = ctx.guild.get_member(g.helper_id)
                            await trysend(helper, embed=notif)
                    # Explain what does joining a private guild mean
                    reply = discord.Embed(color=colors.paper)
                    reply.title = "🛠 | Ваш запрос отправлен главе"
                    reply.description = (
                        f"Ваш запрос в гильдию **{anf(g.name)}** был отправлен.\n"
                        "Это закрытая гильдия, дождитесь рассмотрения Вашей заявки."
                    )
                    reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["leave-guild", "leaveguild", "lg", "leave"])
    async def leave_guild(self, ctx):
        sconf = Server(ctx.guild.id, {"subguilds.name": True, "block_leave": True, f"subguilds.members.{ctx.author.id}": True, "subguilds.role_id": True})
        g = sconf.get_guild(ctx.author.id)
        if g is None:
            reply = discord.Embed(color=discord.Color.dark_red())
            reply.title = "❌ | Ошибка"
            reply.description = "Вас нет ни в одной гильдии"
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        
        elif sconf.block_leave and not ctx.author.guild_permissions.administrator:
            reply = discord.Embed(color=colors.paper)
            reply.title = "🔒 | Выход невозможен"
            reply.description = "Администрация сервера запретила выход из гильдий."
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

        else:
            no = ["no", "0", "нет", "n"]
            yes = ["yes", "1", "да", "y"]

            warn_emb = discord.Embed()
            warn_emb.title = "🛠 | Подтверждение"
            warn_emb.description = (
                f"Ваш опыт в гильдии **{anf(g.name)}** обнулится.\nПродолжить?\n"
                f"Напишите `да` или `нет`"
            )
            warn_emb.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            warn = await ctx.send(embed=warn_emb)

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
            user_reply = None
            try:
                msg = await self.client.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.send(f"{ctx.author.mention}, Вы слишком долго не отвечали. Выход отменён.")
            else:
                user_reply = msg.content.lower()
            # Delete warning
            try:
                await warn.delete()
            except:
                pass
            
            if user_reply in no:
                await ctx.send(f"{ctx.author.mention}, действие отменено.")
            elif user_reply in yes:
                g.kick(ctx.author.id)
                await remove_join_role(ctx.author, g.role_id)

                reply = discord.Embed()
                reply.title = "🚪 | Выход"
                reply.description = f"Вы вышли из гильдии **{g.name}**"
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["get-guild-role", "give-guild-role", "ggr", "get-role"])
    async def get_guild_role(self, ctx):
        pr = ctx.prefix
        sconf = Server(ctx.guild.id, {f"subguilds.members.{ctx.author.id}": True, "subguilds.role_id": True})
        g = sconf.get_guild(ctx.author.id)
        if g is None:
            reply = discord.Embed(color=discord.Color.dark_red())
            reply.title = "❌ | Ошибка"
            reply.description = (
                "Вас нет ни в одной гильдии\n"
                f"Список гильдий: `{pr}top`"
            )
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        else:
            if g.role_id is None:
                reply = discord.Embed(color=discord.Color.dark_red())
                reply.title = "❌ | Ошибка"
                reply.description = "У Вашей гильдии не настроена роль для участников"
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
            else:
                if g.role_id not in [r.id for r in ctx.author.roles]:
                    await give_join_role(ctx.author, g.role_id)
                    reply = discord.Embed(color=colors.coral)
                    reply.title = "🎀 | Выполнено"
                    reply.description = f"Вам была выдана роль гильдии: **<@&{g.role_id}>**"
                    reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=reply)
                else:
                    reply = discord.Embed(color=discord.Color.dark_red())
                    reply.title = "❌ | Не жадничайте"
                    reply.description = f"У Вас уже есть роль гильдии - **<@&{g.role_id}>**"
                    reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["guilds"])
    async def top(self, ctx, filtration="exp", *, extra="без названия"):
        pr = ctx.prefix
        filters = {
            "exp": "✨",
            "mentions": "📯",
            "members": "👥",
            "roles": "🎗",
            "reputation": "🔅",
            "rating": "🏆",
            "superpoints": "🪐" # BETA
        }
        filter_aliases = {
            "exp": ["xp", "опыт"],
            "mentions": ["упоминания", "теги", "pings"],
            "members": ["участников", "численности"],
            "roles": ["роли"],
            "reputation": ["репутация"],
            "rating": ["mixed", "рейтинг"]
        }
        # Adding extra filter
        if ctx.guild.id in cool_servers:
            filter_aliases["superpoints"] = ["super-points", "супер-поинты"] # BETA
        
        filtration = find_alias(filter_aliases, filtration)

        if filtration is None:
            reply = discord.Embed()
            reply.title = "❓ | Фильтры топа"
            reply.description = (
                f"> `{pr}top exp`\n"
                f"> `{pr}top mentions`\n"
                f"> `{pr}top members`\n"
                f"> `{pr}top reputation`\n"
                f"> `{pr}top rating`\n"
                f"> `{pr}top roles`\n"
            )
            if ctx.guild.id in cool_servers:
                reply.description += f"> `{pr}top super-points`"
            
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
            return # Escape command
        
        if filtration == "rating":
            stats = Server(ctx.guild.id, {"subguilds.name": True, "subguilds.reputation": True, "subguilds.members": True}).rating_pairs()
            desc = "Фильтрация одновременно **по опыту и репутации** - рейтинг гильдий"
            key = lambda p: p[1]
            namekey = lambda p: p[0]
        
        elif filtration == "exp":
            stats = Server(ctx.guild.id, {"subguilds.name": True, "subguilds.members": True}).guilds
            desc = "Фильтрация **по количеству опыта**"
            key = lambda g: g.xp
            namekey = lambda g: g.name
            
        elif filtration == "roles":
            role = await commands.RoleConverter().convert(ctx, extra)
            guilds = Server(ctx.guild.id, {"subguilds.name": True, "subguilds.members": True}).guilds
            desc = f"Фильтрация **по количеству участников, имеющих роль <@&{role.id}>**"
            stats = []
            for g in guilds:
                total = 0
                for m in g.members:
                    member = ctx.guild.get_member(m.id)
                    if member is not None and role in member.roles:
                        total += 1
                stats.append((g.name, total))
            del guilds
            key = lambda p: p[1]
            namekey = lambda p: p[0]
            
        elif filtration == "mentions":
            stats = Server(ctx.guild.id, {"subguilds.name": True, "subguilds.mentions": True}).guilds
            desc = "Фильтрация **по количеству упоминаний**"
            key = lambda g: g.mentions
            namekey = lambda g: g.name

        elif filtration == "members":
            stats = Server(ctx.guild.id, {"subguilds.name": True, "subguilds.members": True}).guilds
            desc = "Фильтрация **по количеству участников**"
            key = lambda g: g.member_count
            namekey = lambda g: g.name

        elif filtration == "reputation":
            stats = Server(ctx.guild.id, {"subguilds.name": True, "subguilds.reputation": True}).guilds
            desc = "Фильтрация **по репутации**"
            key = lambda g: g.reputation
            namekey = lambda g: g.name
        
        elif filtration == "superpoints":
            stats = Server(ctx.guild.id, {"subguilds.name": True, "subguilds.superpoints": True}).guilds
            desc = "Фильтрация **по супер-поинтам**"
            key = lambda g: g.superpoints
            namekey = lambda g: g.name
        
        stats.sort(reverse=True, key=key)

        table = ""
        for i, el in enumerate(stats):
            guild_name = anf(namekey(el))
            table += f"**{i + 1}.** {guild_name} • **{vis_num(key(el))}** {filters[filtration]}\n"
        if table == "": table = "Гильдий нет :("
        
        lb = discord.Embed(color=colors.gold)
        lb.title = f"⚔ | Гильдии сервера {ctx.guild.name}"
        lb.description = (
            f"{desc}\n"
            f"Подробнее о гильдии: `{pr}guild-info Название`\n"
            f"Вступить в гильдию: `{pr}join-guild Название`\n\n"
            f"{table}"
        )
        lb.set_thumbnail(url=f"{ctx.guild.icon_url}")
        await ctx.send(embed=lb)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["global-top", "globaltop", "glt"])
    async def global_top(self, ctx, page: IntConverter=1):
        interv = 15
        members = Server(ctx.guild.id, {"subguilds.members": True}).get_all_members()
        length = len(members)
        if length > 0:
            total_pages = (length - 1) // interv + 1
        else:
            total_pages = 1

        if not (0 < page <= total_pages):
            reply = discord.Embed(color=discord.Color.dark_red())
            reply.title = "💢 Упс"
            reply.description = f"Страница не найдена. Всего страниц: **{total_pages}**"
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        
        else:
            members.sort(reverse=True, key=lambda m: m.xp)
            place = None
            for i, m in enumerate(members):
                if m.id == ctx.author.id:
                    place = i + 1
                    break
            if place is None:
                auth_desc = "Вас нет в этом топе, так как Вы не состоите ни в одной гильдии"
            else:
                auth_desc = f"Ваше место в топе: **{place} / {length}**"
            
            lowerb = (page - 1) * interv
            upperb = min(length, page * interv)
            desc = ""
            for i in range(lowerb, upperb):
                m = members[i]
                user = ctx.guild.get_member(m.id)
                desc += f"**{i + 1})** {anf(user)} • **{vis_num(m.xp)}** ✨\n"
            del members
            
            reply = discord.Embed(color=colors.sky)
            reply.title = f"🌐 Топ всех участников гильдий сервера\n{ctx.guild.name}"
            reply.description = f"{auth_desc}\n\n{desc}"
            reply.set_thumbnail(url=f"{ctx.guild.icon_url}")
            reply.set_footer(text=f"Стр. {page}/{total_pages} | {ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["guild-info", "guildinfo", "gi"])
    async def guild_info(self, ctx, *, search=None):
        pr = ctx.prefix
        g = None
        if search is None:
            sconf = Server(ctx.guild.id, {"subguilds": True}, {f"subguilds.members.{ctx.author.id}": {"$exists": True}})
            g = sconf.get_guild(ctx.author.id)
            del sconf
            if g is None:
                reply = discord.Embed(color=discord.Color.dark_red())
                reply.title = "❌ | Ошибка"
                reply.description = (
                    "Поскольку Вы не состоите ни в одной гильдии, придётся уточнить гильдию:\n"
                    f"`{pr}guild-info Название гильдии`\n"
                    f"Список гильдий: `{pr}top`"
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
                
        else:
            sconf = Server(ctx.guild.id, {"subguilds.name": True})
            guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, pr)
            if guild_name is None:
                raise IsNotSubguild(search)
            elif isinstance(guild_name, EmergencyExit):
                g = None
            else:
                g = Guild(ctx.guild.id, name=guild_name)
            del sconf
            
        if g is not None:
            g.__members = []
            g.requests = []

            reply = discord.Embed(color=colors.sky)
            reply.title = anf(g.name)
            reply.description = (
                f"{g.description}\n"
                f"**->** Топ участников: `{pr}guild-top 1 {g.name}`"
            )
            reply.set_thumbnail(url=g.avatar_url)
            if g.leader_id is not None:
                leader = ctx.guild.get_member(g.leader_id)
                reply.add_field(name="💠 Владелец", value=f"> {anf(leader)}", inline=False)
            if g.helper_id is not None:
                helper = ctx.guild.get_member(g.helper_id)
                reply.add_field(name="🔰 Помощник", value=f"> {anf(helper)}", inline=False)
            reply.add_field(name="👥 Всего участников", value=f"> {g.member_count} из {g.limit}", inline=False)
            reply.add_field(name="✨ Всего опыта", value=f"> {vis_num(g.xp)}", inline=False)
            reply.add_field(name="🔅 Репутация", value=f"> {vis_num(g.reputation)}", inline=False)
            if g.mentions > 0:
                reply.add_field(name="📯 Упоминаний", value=f"> {vis_num(g.mentions)}", inline=False)
            if g.role_id is not None:
                reply.add_field(name="🎗 Роль", value=f"> <@&{g.role_id}>", inline=False)
            if g.private:
                reply.add_field(name="🔒 Приватность", value=f"> Вступление по заявкам\n> Заявок на рассмотрении: **{g.request_count}**")
            await ctx.send(embed=reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["guild-members", "guildmembers", "gm", "guild-top", "gt"])
    async def guild_top(self, ctx, page: IntConverter=1, *, search=None):
        pr = ctx.prefix
        interval = 15

        g = None
        if search is None:
            sconf = Server(ctx.guild.id, {"subguilds.name": True, "subguilds.members": True}, {f"subguilds.members.{ctx.author.id}": {"$exists": True}})
            g = sconf.get_guild(ctx.author.id)
            del sconf
            if g is None:
                reply = discord.Embed(color=discord.Color.dark_red())
                reply.title = "❌ | Ошибка"
                reply.description = (
                    "Поскольку Вы не состоите ни в одной гильдии, придётся уточнить гильдию:\n"
                    f"`{pr}guild-info Название гильдии`\n"
                    f"Список гильдий: `{pr}top`"
                )
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
                
        else:
            sconf = Server(ctx.guild.id, {"subguilds.name": True})
            guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, pr)
            if guild_name is None:
                raise IsNotSubguild(search)
            elif isinstance(guild_name, EmergencyExit):
                g = None
            else:
                g = Guild(ctx.guild.id, name=guild_name, attrs_projection={"members": True, "name": True})
            del sconf
            
        if g is not None:
            total_pages = 1
            if g.member_count > 0:
                total_pages = (g.member_count - 1) // interval + 1
            if not (0 < page <= total_pages):
                reply = discord.Embed()
                reply.title = "🔎 | Страница не найдена"
                reply.description = f"Страница не найдена. Всего страниц: **{total_pages}**"
                await ctx.send(embed=reply)
            else:
                members = sorted(g.members, reverse=True, key=lambda m: m.xp)
                g.__members = []
                lowerb = (page - 1) * interval
                upperb = min(g.member_count, page * interval)
                desc = ""
                for i in range(lowerb, upperb):
                    m = members[i]
                    user = ctx.guild.get_member(m.id)
                    desc += f"**{i + 1}.** {anf(user)} • **{vis_num(m.xp)}** ✨\n"
                if desc == "": desc = "Тут пусто! :("
                
                lb = discord.Embed(color=colors.caramel)
                lb.title = f"👥 | Участники гильдии {g.name}"
                lb.description = desc
                lb.set_footer(text=f"Стр. {page}/{total_pages}")
                lb.set_thumbnail(url=g.avatar_url)
                await ctx.send(embed=lb)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["user-guild", "userguild", "ug", "user-info", "userinfo", "ui"])
    async def user_guild(self, ctx, *, user: discord.Member=None):
        if user is None: user = ctx.author
        
        sconf = Server(ctx.guild.id, {"subguilds.name": True, "subguilds.members": True}, {f"subguilds.members.{user.id}": {"$exists": True}})
        g = sconf.get_guild(user.id)
        del sconf
        if g is None:
            if user.id == ctx.author.id:
                desc = "Вы не состоите в гильдии, а потому у Вас нет своего профиля."
            else:
                desc = f"Пользователь **{anf(user)}** не состоит в гильдии."
            reply = discord.Embed(color=discord.Color.dark_red())
            reply.title = "❌ | Ошибка"
            reply.description = desc
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

        else:
            m = g.get_member(user.id)
            members = sorted(g.members, reverse=True, key=lambda m: m.xp)
            g.__members = []
            place = 0
            for i, mm in enumerate(members):
                if m.id == mm.id:
                    place = i + 1
                    break
            del members

            stat_emb = discord.Embed(color=colors.coral)
            stat_emb.add_field(name="🛡 Гильдия", value=anf(g.name), inline = False)
            stat_emb.add_field(name="✨ Заработано опыта", value=f"{vis_num(m.xp)}", inline=False)
            stat_emb.add_field(name="🏅 Место", value=f"{place} / {g.member_count}", inline=False)
            stat_emb.set_author(name=f"Профиль 🔎 {user}", icon_url=f"{user.avatar_url}")
            stat_emb.set_thumbnail(url=g.avatar_url)
            await ctx.send(embed=stat_emb)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        aliases=["count-roles", "countroles", "cr"],
        description="подсчитать кол-во перечисленных ролей в существующих гильдиях\n",
        usage="[Гильдия] @роль1 @роль2 ...\n",
        brief="[Короли Жизни] @Модератор @Участник" )
    async def count_roles(self, ctx, *, text_data):
        pr = ctx.prefix

        search, text = sep_args(text_data)
        rconv = commands.RoleConverter()
        roles = []
        for rr in text.split():
            try:
                r = await rconv.convert(ctx, rr)
                roles.append(r)
            except:
                pass
        if roles == []:
            reply = discord.Embed(color=discord.Color.dark_red())
            reply.title = "❌ | Ошибка"
            reply.description = "Среди указанных ролей я не распознал ни одну, увы. Если в названиях ролей более одного слова, то упомяните их."
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        
        else:
            sconf = Server(ctx.guild.id, {"subguilds.name": True})
            guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, pr)
            g = None
            if guild_name is None:
                raise IsNotSubguild(search)
            elif isinstance(guild_name, EmergencyExit):
                g = None
            else:
                g = Guild(ctx.guild.id, name=guild_name, attrs_projection={"members": True, "name": True})
            del sconf

            if g is not None:
                stats = {r.id: 0 for r in roles}
                for m in g.members:
                    user = ctx.guild.get_member(m.id)
                    if user is not None:
                        for r in roles:
                            if r in user.roles:
                                stats[r.id] += 1
                del roles

                desc = ""
                for rid, num in sorted(stats.items(), key=lambda p: p[1]):
                    desc += f"<@&{rid}> • {num} 👥\n"

                reply = discord.Embed(color=colors.pancake)
                reply.title = anf(g.name)
                reply.description = f"**Статистика ролей:**\n{desc}"
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
    

def setup(client):
    client.add_cog(guild_use(client))