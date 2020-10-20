import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import os, datetime


#----------------------------+
#         Constants          |
#----------------------------+
from db_models import guild_limit, default_avatar_url, member_limit
from functions import EmergencyExit


#----------------------------+
#         Functions          |
#----------------------------+
from functions import find_alias, ask_to_choose, anf
from custom_converters import IntConverter, IsNotSubguild
from db_models import Server, Guild

# Other
def add_sign(Int):
    if str(Int)[0] == "-":
        return str(Int)
    else:
        return f"+{Int}"


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


def role_gte(role, member):
    return member.id != member.guild.owner_id and role.position >= member.top_role.position


def image_link(string):
    return string.startswith("https://")


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


async def give_join_role(member, role_id):
    if role_id is not None and member is not None:
        role = discord.utils.get(member.guild.roles, id=role_id)
        if role != None and role not in member.roles:
            try:
                await member.add_roles(role)
            except Exception:
                pass
    return


async def remove_join_role(member, role_id):
    if role_id is not None and member is not None:
        role = member.guild.get_role(role_id)
        if role is not None and role in member.roles:
            try:
                await member.remove_roles(role)
            except Exception:
                pass
    return


async def post_log(guild, channel_id, log):
    if channel_id is not None:
        channel = guild.get_channel(channel_id)
        if channel is not None:
            await channel.send(embed=log)



class guild_control(commands.Cog):
    def __init__(self, client):
        self.client = client

    #----------------------------+
    #           Events           |
    #----------------------------+
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Guild controller cog is loaded")
    
    
    #----------------------------+
    #          Commands          |
    #----------------------------+
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        aliases=["rep"],
        description="изменяет репутацию гильдии\n",
        usage="change Число [Гильдия] Причина (по желанию)\nset Число [Гильдия] Причина (по желанию)",
        brief="change -10 Короли Участник был наказан\nset 100 [Короли воров] Начнём с чистого листа" )
    async def reputation(self, ctx, param, value: IntConverter=None, *, text_data=None):
        pr = ctx.prefix
        param = param.lower()
        params = {
            "change": {
                "usage": f"`{pr}rep change Кол-во Гильдия`",
                "example": f"`{pr}rep change 10 Гильдия`",
                "info": "Изменяет репутацию гильдии на указанное кол-во очков",
                "log": "Изменено"
            },
            "set": {
                "usage": f"`{pr}rep set Кол-во Гильдия`",
                "example": f"`{pr}rep set 70 Гильдия`",
                "info": "Устанавливает у гильдии указанную репутацию",
                "log": "Установлено"
            }
        }

        if not param in params:
            reply = discord.Embed(color=mmorpg_col("vinous"))
            reply.title = "📑 Неверный параметр"
            reply.description = (
                    f"Вы ввели: `{param}`\n"
                    f"Доступные параметры:\n"
                    f"> `{pr}rep change`\n"
                    f"> `{pr}rep set`\n"
                    f"Подробнее: `{pr}rep`"
                )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif value is None or text_data is None:
            param_desc = params[param]
            reply = discord.Embed()
            reply.title = f"❓ | {pr}rep {param}"
            reply.description = (
                    f"**Использование:** {param_desc['usage']}\n"
                    f"**Пример:** {param_desc['example']}\n"
                    f"-> {param_desc['info']}"
                )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            search, text = sep_args(text_data)
            if text == "":
                text = "Не указана"
            
            sconf = Server(ctx.guild.id, {"subguilds.name": True, "log_channel": True, "master_roles": True})
            
            guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, ctx.prefix)
            
            if guild_name is None:
                raise IsNotSubguild(search)

            elif isinstance(guild_name, EmergencyExit):
                guild_name = None
                
            # ----------
            if guild_name is not None:
                if not any([r.id in sconf.master_roles for r in ctx.author.roles]) and not ctx.author.guild_permissions.administrator:
                    raise commands.MissingPermissions(["administrator", "guild_master"])

                else:
                    if param == "change":
                        changes = add_sign(value)
                        sconf.add_reputation(guild_name, value)
                    elif param == "set":
                        changes = f"установлена на {value}"
                        sconf.set_reputation(guild_name, value)

                    reply = discord.Embed(color = mmorpg_col("clover"))
                    reply.title = f"✅ | {anf(guild_name)}"
                    reply.description = f"Репутация: {changes}"
                    await ctx.send(embed=reply)

                    log = discord.Embed(
                        title="🔅 | Изменена репутация",
                        description=(
                            f"**Модератор:** {anf(ctx.author)}\n"
                            f"**Гильдия:** {anf(guild_name)}\n"
                            f"**Действие:** {changes}\n"
                            f"**Причина:** {text}"
                        ),
                        color=mmorpg_col("pancake")
                    )
                    await post_log(ctx.guild, sconf.log_channel, log)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        aliases=["create-guild", "createguild", "cg", "create"],
        description=("создаёт гильдию. Доступно администраторам, обладателям мастер-ролей или ролей создателя гильдий. "
        "Последние могут быть ограничены в количестве создаваемых гильдий (подробнее в `help settings`)"),
        usage="Название гильдии",
        brief="Короли" )
    async def create_guild(self, ctx, *, guild_name):
        guild_name = guild_name[:32].replace("$", "")
        pr = ctx.prefix
        created = False
        sconf = Server(ctx.guild.id, {
            "subguilds.name": True, "subguilds.leader_id": True,
            "log_channel": True, "master_roles": True, "creator_roles": True,
            "guild_limit": True, "creator_limit": True
        })
        if sconf.guild_count >= sconf.guild_limit:
            reply = discord.Embed(color=discord.Color.dark_red())
            reply.title = "❌ | Слишком много гильдий"
            reply.description = f"На этом сервере нельзя создавать гильдии, если их не меньше **{sconf.guild_limit}**."
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
            return
        elif guild_name in [g.name for g in sconf.guilds]:
            reply = discord.Embed(color=discord.Color.dark_red())
            reply.title = "❌ | Одноимённая гильдия"
            reply.description = f"На этом сервере уже есть гильдия с названием **{guild_name}**."
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
            return
        
        if ctx.author.guild_permissions.administrator or any([r.id in sconf.master_roles for r in ctx.author.roles]):
            created = True
        elif any([r.id in sconf.creator_roles for r in ctx.author.roles]):
            total_owned = 0
            for g in sconf.guilds:
                if g.leader_id == ctx.author.id:
                    total_owned += 1
            if total_owned >= sconf.creator_limit:
                reply = discord.Embed(color=discord.Color.dark_red())
                reply.title = "❌ | Вам больше нельзя создавать гильдии"
                reply.description = f"**{sconf.creator_limit}** - это максимум гильдий, которым Вы можете владеть."
                reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
                return
            else:
                created = True
        else:
            raise commands.MissingPermissions(["administrator", "guild_master", "guild_creator"])

        if created:
            sconf.create_guild(guild_name, ctx.author.id)

            reply = discord.Embed(color=mmorpg_col("clover"))
            reply.title = f"✅ | Гильдия **{guild_name}** создана"
            reply.description = (
                    f"Отредактировать гильдию: `{pr}edit-guild`\n"
                    f"Профиль гильдии: `{pr}guild-info {guild_name}`\n"
                    f"Зайти в гильдию `{pr}join-guild {guild_name}`"
                )
            reply.set_thumbnail(url=default_avatar_url)
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

            log = discord.Embed(color=mmorpg_col("clover"))
            log.title = "♻ | Создана гильдия"
            log.description = (
                f"**Создатель:** {anf(ctx.author)}\n"
                f"**Название:** {anf(guild_name)}\n"
            )
            await post_log(ctx.guild, sconf.log_channel, log)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        aliases=["edit-guild", "editguild", "eg", "edit", "ред"],
        description="изменяет разные параметры гильдии. Все параметры указаны ниже.",
        usage=("Параметр [Название гильдии] Новое значение\n"
            "name\n"
            "description\n"
            "avatar\n"
            "leader\n"
            "helper\n"
            "role\n"
            "privacy\n"
            "limit\n"
        ),
        brief="role [Короли Воров] @Роль Королей" )
    async def edit_guild(self, ctx, param, *, text_data = None):
        pr = ctx.prefix
        param_desc = {
            "name": {
                "usage": f'`{pr}edit-guild name [Старое название] Новое название`',
                "example": f'`{pr}edit-guild name [Моя гильдия] Лучшая гильдия`'
            },
            "description": {
                "usage": f'`{pr}edit-guild description [Гильдия] Новое описание`',
                "example": f'`{pr}edit-guild description [Моя гильдия] Для тех, кто любит общаться`'
            },
            "avatar_url": {
                "usage": f'`{pr}edit-guild avatar [Гильдия] Ссылка`',
                "example": f'`{pr}edit-guild avatar [Моя гильдия] https://discordapp.com/.../image.png`'
            },
            "leader_id": {
                "usage": f'`{pr}edit-guild leader [Гильдия] @Пользователь`',
                "example": f'`{pr}edit-guild leader [Моя гильдия] @Пользователь`'
            },
            "helper_id": {
                "usage": f'`{pr}edit-guild helper [Гильдия] @Пользователь`',
                "example": f'`{pr}edit-guild helper [Моя гильдия] @Пользователь`'
            },
            "role_id": {
                "usage": f'`{pr}edit-guild role [Гильдия] @Роль (или delete)`',
                "example": f'`{pr}edit-guild role [Моя гильдия] delete`'
            },
            "private": {
                "usage": f'`{pr}edit-guild privacy [Гильдия] on / off`',
                "example": f'`{pr}edit-guild privacy [Моя гильдия] on`'
            },
            "limit": {
                "usage": f"`{pr}edit-guild limit [Гильдия] Число`",
                "example": f"`{pr}edit-guild limit Короли 15`"
            }
        }

        parameters = {
            "name": ["название"],
            "description": ["описание"],
            "avatar_url": ["аватарка"],
            "leader_id": ["глава", "owner"],
            "helper_id": ["помощник", "заместитель"],
            "role_id": ["роль"],
            "private": ["приватность", "privacy"],
            "limit": ["лимит", "максимум", "max"]
        }
        parameter = find_alias(parameters, param)

        if parameter is None:
            reply = discord.Embed(
                title = f"❓ | Не найден параметр `{param}`",
                description = (
                    "Попробуйте с одним из этих:\n"
                    f"> `{pr}edit-guild name`\n"
                    f"> `{pr}edit-guild description`\n"
                    f"> `{pr}edit-guild avatar`\n"
                    f"> `{pr}edit-guild leader`\n"
                    f"> `{pr}edit-guild helper`\n"
                    f"> `{pr}edit-guild role`\n"
                    f"> `{pr}edit-guild privacy`\n"
                    f"> `{pr}edit-guild limit`\n"
                    f"**Подробнее:** `{pr}edit-guild`\n"
                    f'**Использование:** `{pr}edit-guild Параметр [Название гильдии] Новое значение`\n'
                    f'**Пример:** `{pr}edit-guild name [Моя гильдия] Хранители`\n'
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            if text_data is None:
                reply = discord.Embed()
                reply.title = f"🛠 | Подробнее о {pr}edit-guild {param}"
                reply.description = (
                        f"**Использование:** {param_desc[parameter]['usage']}\n"
                        f"**Пример:** {param_desc[parameter]['example']}")
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                search, text = sep_args(text_data)
                sconf = Server(ctx.guild.id, {
                    "subguilds.name": True, "subguilds.leader_id": True,
                    "master_roles": True, "log_channel": True
                })
                guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, pr)
                if guild_name is None:
                    raise IsNotSubguild(search)
                
                elif isinstance(guild_name, EmergencyExit):
                    guild_name = None
                    return

                else:
                    g = sconf.get_guild_named(guild_name)

                    if (ctx.author.id != g.leader_id and not any([r.id in sconf.master_roles for r in ctx.author.roles])
                    and not ctx.author.guild_permissions.administrator):
                        raise commands.MissingPermissions(["administrator", "guild_master", "guild_leader"])
                    
                    else:
                        correct_arg = True
                        if parameter == "name":
                            value = text.replace("$", "")
                            if value == "":
                                correct_arg = False
                                desc = "Вы не можете назвать гильдию пустой строкой"
                            elif sconf.get_guild_named(value) is not None:
                                correct_arg = False
                                desc = f"Гильдия с названием {anf(value)} уже есть"
                            else:
                                g.edit_name(value)
                                desc = f"Гильдия переименована в **{anf(value)}**"
                        
                        elif parameter == "description":
                            value = text.replace("$", "")[:256]
                            g.edit_description(value)
                            desc = f"Добавлено новое описание: {value}"
    
                        elif parameter in ["leader_id", "helper_id"]:
                            if text.lower() == "delete" and parameter == "helper_id":
                                g.edit_helper_id(None)
                                desc = "В гильдии больше нет помощника."
                            else:
                                value = await commands.MemberConverter().convert(ctx, text)
                                # Error will be raised in case member wasn't found
                                if value.id == g.leader_id:
                                    correct_arg = False
                                    desc = f"**{anf(value)}** уже является главой этой гильдии."
                                else:
                                    if parameter == "leader_id":
                                        g.edit_leader_id(value.id)
                                        desc = f"Владение гильдией передано в руки **{anf(value)}**."
                                    else:
                                        g.edit_helper_id(value.id)
                                        desc = f"Назначен новый помощник: **{anf(value)}**."
                            
                        elif parameter == "role_id":
                            if text.lower() == "delete":
                                g.edit_role_id(None)
                                desc = "Роль гильдии была удалена."
                            else:
                                value = await commands.RoleConverter().convert(ctx, text)
                                if not ctx.author.guild_permissions.manage_roles or value.position >= ctx.author.top_role.position:
                                    correct_arg = False
                                    desc = f"Роль <@&{value.id}> не ниже Вашей или у Вас нет прав на управление ролями."
                                elif not ctx.guild.me.guild_permissions.manage_roles or value.position >= ctx.guild.me.top_role.position:
                                    correct_arg = False
                                    desc = f"У меня нет прав. Роль <@&{value.id}> не ниже моей или у меня нет прав на управление ролями."
                                else:
                                    g.edit_role_id(value.id)
                                    desc = (f"Теперь **<@&{value.id}>** - это роль гильдии. "
                                    f"Новобранцы получат её автоматически, а текущим участникам нужно прописать `{pr}get-guild-role`")

                        elif parameter == "avatar_url":
                            atts = ctx.message.attachments
                            if atts != []:
                                value = atts[0].url
                            else:
                                value = text
                                correct_arg = text.startswith("https://")
                            if not correct_arg:
                                desc = f"Не удаётся найти картинку по ссылке {text}"
                            else:
                                g.edit_avatar_url(value)
                                desc = f"Установлен новый аватар."

                        elif parameter == "private":
                            on = ["on", "вкл", "1"]
                            off = ["off", "выкл", "0"]
                            if text.lower() in on:
                                g.edit_privacy(True)
                                desc = f"Включен вход по заявкам."
                            elif text.lower() in off:
                                g.edit_privacy(False)
                                desc = f"Выключен вход по заявкам."
                            else:
                                correct_arg = False
                                desc = f"Входной аргумент {text} должен быть `on` или `off`"
                        
                        elif parameter == "limit":
                            value = await IntConverter().convert(ctx, text)
                            # Error will be raised in case it's not int
                            if value > sconf.member_limit:
                                correct_arg = False
                                desc = f"На этом сервере не разрешены гильдии с численностью больше, чем **{sconf.member_limit}**."
                            else:
                                g.edit_limit(value)
                                desc = f"Новый лимит участников. Теперь, если в гильдии участников и заявок больше, чем **{value}**, то в неё никто не сможет зайти."
                        
                        if correct_arg:
                            reply = discord.Embed(color=mmorpg_col("clover"))
                            reply.title = f"✅ | {anf(g.name)}: изменения"
                            reply.description = f"{desc}\n\n**Профиль гильдии:** `{pr}guild-info {g.name}`"
                            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                            await ctx.send(embed=reply)
                            # Logging
                            log = discord.Embed(color=discord.Color.blurple())
                            log.title = "📝 | Гильдия изменена"
                            log.description = (
                                f"**Название:** {g.name}\n"
                                f"**Изменение:** {desc}\n"
                                f"**Изменил:** {anf(ctx.author)}"
                            )
                            await post_log(ctx.guild, sconf.log_channel, log)
                        else:
                            reply = discord.Embed(color=discord.Color.dark_red())
                            reply.title = "❌ | Ошибка"
                            reply.description = desc
                            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                            await ctx.send(embed=reply)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        aliases=["delete-guild", "deleteguild", "dg", "delete"],
        description="удаляет гильдию",
        usage="Название гильдии",
        brief="Короли" )
    async def delete_guild(self, ctx, *, guild_search):
        pr = ctx.prefix
        sconf = Server(ctx.guild.id, {
            "log_channel": True, "master_roles": True,
            "subguilds.name": True, "subguilds.leader_id": True})
        
        guild_name = await ask_to_choose(sconf.names_matching(guild_search), ctx.channel, ctx.author, self.client, pr)

        if guild_name is None:
            raise IsNotSubguild(guild_search)
        elif isinstance(guild_name, EmergencyExit):
            pass
        else:
            g = sconf.get_guild_named(guild_name)
            del guild_name, guild_search
            if (not ctx.author.guild_permissions.administrator and ctx.author.id != g.leader_id and
            not any([r.id in sconf.master_roles for r in ctx.author.roles]) ):
                raise commands.MissingPermissions(["administrator", "guild_leader", "guild_master"])
            else:
                sconf.delete_guild(g.name)
                
                reply = discord.Embed(
                    title = "🗑 | Удаление завершено",
                    description = f"Вы удалили гильдию **{g.name}**"
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

                log = discord.Embed(
                    title="💥 | Удалена гильдия",
                    description=(
                        f"**Удалил:** {anf(ctx.author)}\n"
                        f"**Название:** {anf(g.name)}\n"
                    ),
                    color=mmorpg_col("vinous")
                )
                await post_log(ctx.guild, sconf.log_channel, log)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        aliases=["req", "request"],
        description="просмотр списка заявок на вступление в какую-либо гильдию.",
        usage='Страница Гильдия',
        brief="1 Короли" )
    async def requests(self, ctx, page: IntConverter, *, search):
        pr = ctx.prefix
        interval = 20

        sconf = Server(ctx.guild.id, {
            "master_roles": True, "subguilds.helper_id": True, "subguilds.requests": True,
            "subguilds.name": True, "subguilds.leader_id": True, "subguilds.private": True})
        
        guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, pr)
        
        if guild_name is None:
            raise IsNotSubguild(search)
        elif isinstance(guild_name, EmergencyExit):
            pass
        else:
            g = sconf.get_guild_named(guild_name)
            sconf.__guilds = []
            del guild_name, search
            
            # Check rights
            if (ctx.author.id not in [g.leader_id, g.helper_id] and
            not ctx.author.guild_permissions.administrator and not any([r.id in sconf.master_roles for r in ctx.author.roles])):
                raise commands.MissingPermissions(["administrator", "guild_master", "guild_leader", "guild_helper"])
            # Check privacy
            elif not g.private:
                reply = discord.Embed(
                    title = f"🛠 | Гильдия {g.name} не приватна",
                    description = f"Это гильдия с открытым доступом."
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            else:
                bad_ids = []
                req_list = []
                for ID in g.requests:
                    member = ctx.guild.get_member(ID)
                    if member is None:
                        bad_ids.append(ID)
                    else:
                        req_list.append(member)

                length = len(req_list)

                first_num = (page - 1) * interval
                total_pages = (length - 1) // interval + 1
                if first_num >= length:
                    if length == 0:
                        title = f"📜 | Список запросов в {g.name} пуст"
                        desc = "Заходите позже"
                    else:
                        title = "🔎 | Страница не найдена"
                        desc = f"**Всего страниц:** {total_pages}"
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
                        desc += f"**{i + 1})** {anf(req_list[i])}\n"

                    reply = discord.Embed(
                        title = "Запросы на вступление",
                        description = (
                            f"**В гильдию:** {anf(g.name)}\n"
                            f"**Принять запрос:** `{pr}accept Номер_запроса {g.name}`\n"
                            f"**Отклонить запрос:** `{pr}decline Номер_запроса {g.name}`\n\n"
                            f"{desc}"
                        ),
                        color = mmorpg_col("lilac")
                    )
                    reply.set_footer(text = f"Стр. {page}/{total_pages}")
                    await ctx.send(embed = reply)
                
                #======Remove invalid members======
                if bad_ids != []:
                    g.decline_requests(bad_ids)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        aliases=["ac", "acc"],
        description="принять заявку на вступление. Список заявок: `requests`",
        usage='Номер_заявки Гильдия\nall Гильдия  (принять всё)',
        brief="1 Короли\nall Короли" )
    async def accept(self, ctx, num, *, search):
        if num.lower() != "all": num = await IntConverter().convert(ctx, num)
        pr = ctx.prefix

        sconf = Server(ctx.guild.id, {
            "log_channel": True, "master_roles": True, "subguilds.helper_id": True, "subguilds.requests": True,
            "subguilds.name": True, "subguilds.leader_id": True, "subguilds.private": True})
        guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, pr)
        
        if guild_name is None:
            raise IsNotSubguild(search)
        elif isinstance(guild_name, EmergencyExit):
            pass

        else:
            g = sconf.get_guild_named(guild_name)
            g.__guilds = []
            del guild_name, search
            # Check rights
            if (ctx.author.id not in [g.leader_id, g.helper_id] and
            not ctx.author.guild_permissions.administrator and not any([r.id in sconf.master_roles for r in ctx.author.roles])):
                raise commands.MissingPermissions(["administrator", "guild_master", "guild_leader", "guild_helper"])
            # Check privacy
            elif not g.private:
                reply = discord.Embed()
                reply.title = f"❌ | Гильдия {g.name} не приватна"
                reply.description = f"Это гильдия с открытым доступом."
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
            # Check range
            elif num != "all" and not (0 < num <= g.request_count):
                reply = discord.Embed(color=discord.Color.dark_red())
                reply.title = "❌ | Ошибка"
                reply.description = f"**{num}** превышает число запросов"
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)

            else:
                if num == "all":
                    g.accept_requests()
                    desc = f"Принято заявок: **{g.request_count}**"
                else:
                    member = ctx.guild.get_member(g.requests[num - 1])
                    g.accept_requests(member.id)
                    desc = f"Заявка **{anf(member)}** принята"

                    await give_join_role(member, g.role_id)
                
                reply = discord.Embed()
                reply.title = "🛠 | Выполнено"
                reply.description = desc
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
                # Log
                log = discord.Embed(color=discord.Color.blurple())
                log.title = "📥 | Приняты заявки"
                log.description = (
                    f"**Гильдия:** {anf(g.name)}\n"
                    f"**Принял:** {anf(ctx.author)}\n"
                    f"**Подробности:** {desc}"
                )
                await post_log(ctx.guild, sconf.log_channel, log)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        aliases=["dec"],
        description="отклонить заявку на вступление. Список заявок: `requests`",
        usage='Номер_заявки Гильдия\nall Гильдия  (отклонить всё)',
        brief="1 Короли\nall Короли" )
    async def decline(self, ctx, num, *, search):
        if num.lower() != "all": num = await IntConverter().convert(ctx, num)
        pr = ctx.prefix

        sconf = Server(ctx.guild.id, {
            "log_channel": True, "master_roles": True, "subguilds.helper_id": True, "subguilds.requests": True,
            "subguilds.name": True, "subguilds.leader_id": True, "subguilds.private": True})
        guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, pr)
        
        if guild_name is None:
            raise IsNotSubguild(search)
        elif isinstance(guild_name, EmergencyExit):
            pass

        else:
            g = sconf.get_guild_named(guild_name)
            g.__guilds = []
            del guild_name, search
            # Check rights
            if (ctx.author.id not in [g.leader_id, g.helper_id] and
            not ctx.author.guild_permissions.administrator and not any([r.id in sconf.master_roles for r in ctx.author.roles])):
                raise commands.MissingPermissions(["administrator", "guild_master", "guild_leader", "guild_helper"])
            # Check privacy
            elif not g.private:
                reply = discord.Embed()
                reply.title = f"❌ | Гильдия {g.name} не приватна"
                reply.description = f"Это гильдия с открытым доступом."
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
            # Check range
            elif num != "all" and not (0 < num <= g.request_count):
                reply = discord.Embed(color=discord.Color.dark_red())
                reply.title = "❌ | Ошибка"
                reply.description = f"**{num}** превышает число запросов"
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)

            else:
                if num == "all":
                    g.decline_requests()
                    desc = f"Отклонено заявок: **{g.request_count}**"
                else:
                    member = ctx.guild.get_member(g.requests[num - 1])
                    g.decline_requests([member.id])
                    desc = f"Заявка **{anf(member)}** отклонена"
                
                reply = discord.Embed()
                reply.title = f"🛠 | {anf(g.name)}"
                reply.description = desc
                reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
                await ctx.send(embed=reply)
                # Log
                log = discord.Embed(color=discord.Color.blurple())
                log.title = "📤 | Отклонены заявки"
                log.description = (
                    f"**Гильдия:** {anf(g.name)}\n"
                    f"**Отклонил:** {anf(ctx.author)}\n"
                    f"**Подробности:** {desc}"
                )
                await post_log(ctx.guild, sconf.log_channel, log)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(
        description="исключает участника(ов) из гильдии",
        usage="user Участник\nunder Число\nlast Количество",
        brief="user @User#1234\nunder 150\nlast 10" )
    async def kick(self, ctx, param, value=None, *, search=None):
        pr = ctx.prefix
        param_aliases = {
            "user": ["участник", "member", "пользователь"],
            "under": ["lower", "ниже"],
            "last": ["последние"]
        }

        params = {
            "user": {
                "usage": f"`{pr}kick user @Участник Гильдия`",
                "example": f"`{pr}kick user @Участник Моя Гильдия`",
                "info": "Кикнуть конкретного участника"
            },
            "under": {
                "usage": f"`{pr}kick under Планка_опыта Гильдия`",
                "example": f"`{pr}kick under 500 Моя Гильдия`",
                "info": "Кикнуть тех, у кого кол-во опыта меньше заданной планки"
            },
            "last": {
                "usage": f"`{pr}kick last Кол-во Гильдия`",
                "example": f"`{pr}kick last 10 Моя гильдия`",
                "info": "Кикнуть сколько-то последних участников"
            }
        }
        parameter = find_alias(param_aliases, param)
        if parameter is None:
            desc = ""
            for _param in params:
                desc += f"> `{_param}`\n"
            reply = discord.Embed(color=mmorpg_col("vinous"))
            reply.title = "❌ | Неверный параметр"
            reply.description = f"Вы ввели: `{param}`\nДоступные параметры:\n{desc}"
            reply.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
        
        elif value is None or search is None:
            reply = discord.Embed()
            reply.title = f"🛠 | {pr}kick {parameter}"
            reply.description = (
                    f"**Описание:** {params[parameter]['info']}\n"
                    f"**Использование:** {params[parameter]['usage']}\n"
                    f"**Пример:** {params[parameter]['example']}"
                )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        else:
            sconf = Server(ctx.guild.id, {"log_channel": True, "master_roles": True, "subguilds.name": True})
            guild_name = await ask_to_choose(sconf.names_matching(search), ctx.channel, ctx.author, self.client, pr)
            
            if guild_name is None:
                raise IsNotSubguild(search)
            elif isinstance(guild_name, EmergencyExit):
                pass

            else:
                sconf.__guilds = []
                g = Guild(ctx.guild.id, name=guild_name, attrs_projection={"name": True, "members": True, "leader_id": True, "helper_id": True})

                logdesc = None
                # Check rights
                if (ctx.author.id not in [g.leader_id, g.helper_id] and
                not ctx.author.guild_permissions.administrator and not any([r.id in sconf.master_roles for r in ctx.author.roles])):
                    raise commands.MissingPermissions(["administrator", "guild_master", "guild_leader", "guild_helper"])
                
                elif parameter == "user":
                    user = await commands.MemberConverter().convert(ctx, value)
                    desc = None
                    if user.id == g.leader_id:
                        desc = "Вы не можете кикнуть главу гильдии"
                    elif user.id == ctx.author.id:
                        desc = "Вы не можете кикнуть самого себя"
                    elif user.id not in [m.id for m in g.members]:
                        desc = f"Пользователь **{anf(user)}** не состоит в гильдии **{g.name}**"
                    
                    if desc is not None:
                        reply = discord.Embed(color=mmorpg_col("vinous"))
                        reply.title = "❌ | Ошибка"
                        reply.description = desc
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed=reply)

                    else:
                        g.kick(user.id)
                        logdesc = f"{anf(user)} был исключён из гильдии."
                        reply = discord.Embed(color=mmorpg_col("clover"))
                        reply.title = f"✅ | {g.name}"
                        reply.description = logdesc
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed=reply)
                
                elif parameter == "under":
                    value = await IntConverter().convert(ctx, value)
                    to_kick = [m.id for m in g.members if m.xp <= value and m.id != g.leader_id]
                    g.__members = []
                    g.kick(*to_kick)

                    logdesc = f"Исключены участники: **{len(to_kick)}**, у которых было не больше **{value}** опыта."
                    reply = discord.Embed(color=mmorpg_col("clover"))
                    reply.title = f"✅ | {g.name}"
                    reply.description = logdesc
                    reply.set_footer(text = f"{ctx.author}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=reply)

                    if g.role_id is not None:
                        for ID in to_kick:
                            self.client.loop.create_task(remove_join_role(ctx.guild.get_member(ID), g.role_id))

                elif parameter == "last":
                    value = await IntConverter().convert(ctx, value)
                    to_kick = []
                    for m in sorted(g.members, key=lambda m: m.xp):
                        if m.id != g.leader_id:
                            to_kick.append(m.id)
                    g.__memebrs = []
                    g.kick(*to_kick)
                    
                    logdesc = f"Исключены участники: **{len(to_kick)}** с конца."
                    reply = discord.Embed(color=mmorpg_col("clover"))
                    reply.title = f"✅ | {g.name}"
                    reply.description = logdesc
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

                    if g.role_id is not None:
                        for ID in to_kick:
                            self.client.loop.create_task(remove_join_role(ctx.guild.get_member(ID), g.role_id))
                
                if logdesc is not None:
                    # Log
                    log = discord.Embed(color=discord.Color.blurple())
                    log.title = "🛠 | Исключены участники"
                    log.description = (
                        f"**Гильдия:** {anf(g.name)}\n"
                        f"**Исключил:** {anf(ctx.author)}\n"
                        f"**Подробности:** {logdesc}"
                    )
                    await post_log(ctx.guild, sconf.log_channel, log)


    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.has_permissions(administrator=True)
    @commands.command(
        aliases=["add-xp", "change-xp"],
        description="изменяет опыт участника.",
        usage="Опыт Участник",
        brief="123 @User#1234" )
    async def xp(self, ctx, _xp: IntConverter, *, member: discord.Member):
        sconf = Server(ctx.guild.id, {"log_channel": True, "subguilds.name": True, f"subguilds.members.{member.id}": True},
        {f"subguilds.members.{member.id}": {"$exists": True}})
        g = sconf.get_guild(member.id)
        
        if g is None:
            reply = discord.Embed(color=mmorpg_col("vinous"))
            reply.title = "💢 | Пользователь не в гильдии"
            reply.description = f"Чтобы пользователь **{anf(member)}** мог получать опыт, он должен находиться в гильдии."
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)

        else:
            sconf.add_xp(member.id, _xp)
            # Response
            reply = discord.Embed(color=mmorpg_col("clover"))
            reply.title = "♻ Опыт участника изменён"
            reply.description = f"Опыт **{anf(member)}**, участника гильдии **{g.name}**, был изменён на **{add_sign(_xp)}** ✨"
            reply.set_footer(text=str(ctx.author), icon_url=ctx.author.avatar_url)
            await ctx.send(embed=reply)
            # Logging
            log = discord.Embed(color=discord.Color.orange())
            log.title="✨ | Изменён опыт участника"
            log.description=(
                f"**Гильдия:** {anf(g.name)}\n"
                f"**Модератор:** {anf(ctx.author)}\n"
                f"**Участник:** {anf(member)}\n"
                f"**Изменение:** {add_sign(_xp)}"
            )
            await post_log(ctx.guild, sconf.log_channel, log)


def setup(client):
    client.add_cog(guild_control(client))