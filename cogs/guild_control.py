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
from functions import guild_limit, default_avatar_url

p = "."
param_desc = {
    "name": {
        "usage": f'`{p}edit-guild name [Старое название] Новое название`',
        "example": f'`{p}edit-guild name [Моя гильдия] Лучшая гильдия`'
    },
    "description": {
        "usage": f'`{p}edit-guild description [Гильдия] Новое описание`',
        "example": f'`{p}edit-guild description [Моя гильдия] Для тех, кто любит общаться`'
    },
    "avatar_url": {
        "usage": f'`{p}edit-guild avatar [Гильдия] Ссылка`',
        "example": f'`{p}edit-guild avatar [Моя гильдия] https://discordapp.com/.../image.png`'
    },
    "leader_id": {
        "usage": f'`{p}edit-guild leader [Гильдия] @Пользователь`',
        "example": f'`{p}edit-guild leader [Моя гильдия] @Пользователь`'
    },
    "helper_id": {
        "usage": f'`{p}edit-guild helper [Гильдия] @Пользователь`',
        "example": f'`{p}edit-guild helper [Моя гильдия] @Пользователь`'
    },
    "role_id": {
        "usage": f'`{p}edit-guild role [Гильдия] @Роль (или delete)`',
        "example": f'`{p}edit-guild role [Моя гильдия] delete`'
    },
    "private": {
        "usage": f'`{p}edit-guild privacy [Гильдия] on / off`',
        "example": f'`{p}edit-guild privacy [Моя гильдия] on`'
    }
}

#---------- Functions ------------
from functions import has_roles, has_permissions, get_field, detect, find_alias, carve_int, search_and_choose

# Other
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

def add_sign(Int):
    if str(Int)[0] == "-":
        return str(Int)
    else:
        return f"+{Int}"

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
        role = discord.utils.get(member.guild.roles, id=role_id)
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

#------------ Cog ----------
class guild_control(commands.Cog):
    def __init__(self, client):
        self.client = client

    #---------- Events -----------
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Guild controller cog is loaded")
    
    #---------- Commands ----------
    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["rep"])
    async def reputation(self, ctx, param, value=None, *, text_data=None):
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
            reply = discord.Embed(
                title = "📑 Неверный параметр",
                description = (
                    f"Вы ввели: `{param}`\n"
                    f"Доступные параметры:\n"
                    f"> `{pr}rep change`\n"
                    f"> `{pr}rep set`\n"
                    f"Подробнее: `{pr}rep`"
                ),
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif value is None or text_data is None:
            param_desc = params[param]
            reply = discord.Embed(
                title = f"❓ {pr}rep {param}",
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
            
            # GoT event: guild_name check-for-night-watch
            if guild_name.lower() == "ночной дозор":
                query = {"_id": ctx.guild.id, "night_watch": {"$exists": True}}
                result = collection.find_one(
                    query,
                    projection={
                        "master_role_id": True,
                        "log_channel": True
                    }
                )
                update_pair = {"night_watch.reputation": int(value)}

            else:
                result = collection.find_one(
                    {"_id": ctx.guild.id},
                    projection={
                        "subguilds.name": True,
                        "master_role_id": True,
                        "log_channel": True
                    }
                )
                if "subguilds" not in result:
                    guild_name = None
                else:
                    guild_name = await search_and_choose(result["subguilds"], guild_name, ctx.message, ctx.prefix, self.client)
                
                if guild_name is None:
                    reply = discord.Embed(
                        title = "💢 Упс",
                        description = (
                            f"На сервере нет гильдий с названием **{guild_name}**\n"
                            f"Список гильдий: `{pr}guilds`"
                        ),
                        color = mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)
                elif guild_name == 1337:
                    guild_name = None
                else:
                    query = {"_id": ctx.guild.id, "subguilds.name": guild_name}
                    update_pair = {"subguilds.$.reputation": int(value)}
            # ----------
            
            if guild_name is not None:
                lc_id = result.get("log_channel")
                mr_id = result.get("master_role_id")
                
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
                    if param == "change":
                        changes = add_sign(int(value))
                        to_update = {"$inc": update_pair}
                    elif param == "set":
                        changes = f"установлена на {int(value)}"
                        to_update = {"$set": update_pair}
                    
                    collection.find_one_and_update(
                        query,
                        to_update,
                        upsert=True
                    )

                    reply = discord.Embed(
                        title = "✅ Выполнено",
                        description = f"Репутация изменена.",
                        color = mmorpg_col("clover")
                    )
                    await ctx.send(embed = reply)

                    log = discord.Embed(
                        title="🔅 Изменена репутация",
                        description=(
                            f"**Модератор:** {ctx.author}\n"
                            f"**Гильдия:** {guild_name}\n"
                            f"**Действие:** {changes}\n"
                            f"**Причина:** {text}"
                        ),
                        color=mmorpg_col("pancake")
                    )
                    await post_log(ctx.guild, lc_id, log)

    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["create-guild", "createguild", "cg"])
    async def create_guild(self, ctx, *, guild_name):
        pr = ctx.prefix
        collection = db["subguilds"]
        guild_name = guild_name[:+30].replace("[", "")
        guild_name = guild_name.replace("]", "")

        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={
                "_id": True,
                "subguilds.name": True,
                "master_role_id": True,
                "creator_role": True,
                "log_channel": True
            }
        )
        lc_id = get_field(result, "log_channel")
        mr_id = get_field(result, "master_role_id")
        cr_id = get_field(result, "creator_role")

        if not has_permissions(ctx.author, ["administrator"]) and not has_roles(ctx.author, [mr_id]) and not has_roles(ctx.author, [cr_id]):
            reply = discord.Embed(
                title = "💢 Недостаточно прав",
                description = (
                    "Требуемые права:\n"
                    "> Администратор\n"
                    "Или иметь одну из ролей\n"
                    f"> Мастер гильдий\n"
                    f"> Создатель гильдий"
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
                        f"Удалить гильдию: `{pr}delete-guild Гильдия`"
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
                            f"Отредактировать гильдию: `{pr}edit-guild`\n"
                            f"Профиль гильдии: `{pr}guild-info {guild_name}`\n"
                            f"Зайти в гильдию `{pr}join-guild {guild_name}`"
                        ),
                        color = mmorpg_col("clover")
                    )
                    reply.set_thumbnail(url = default_avatar_url)
                    await ctx.send(embed = reply)

                    log = discord.Embed(
                        title="♻ Создана гильдия",
                        description=(
                            f"**Создатель:** {ctx.author}\n"
                            f"**Название:** {guild_name}\n"
                        ),
                        color=mmorpg_col("clover")
                    )
                    await post_log(ctx.guild, lc_id, log)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["edit-guild", "editguild", "eg", "edit"])
    async def edit_guild(self, ctx, param, *, text_data = None):
        pr = ctx.prefix
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
                    f"**Подробнее:** `{pr}{ctx.command.name}`\n"
                    f'**Использование:** `{pr}{ctx.command.name} Параметр [Название гильдии] Новое значение`\n'
                    f'**Пример:** `{pr}{ctx.command.name} name [Моя гильдия] Хранители`\n'
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        else:
            if text_data is None:
                reply = discord.Embed(
                    title = f"🛠 Использование {pr}edit-guild {param}",
                    description = (
                        f"**Использование:** {param_desc[parameter]['usage']}\n"
                        f"**Пример:** {param_desc[parameter]['example']}"
                    )
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                search, text = sep_args(text_data)

                result = collection.find_one(
                    filter={"_id": ctx.guild.id},
                    projection={
                        "subguilds.members": False,
                        "subguilds.requests": False,
                        "subguilds.description": False
                    }
                )
                guild_name = await search_and_choose(get_field(result, "subguilds"), search, ctx.message, ctx.prefix, self.client)

                if result is None:
                    reply = discord.Embed(
                        title = "💢 Ошибка",
                        description = f"По запросу **{search}** не было найдено гильдий",
                        color = mmorpg_col("vinous")
                    )
                    await ctx.send(embed = reply)
                
                elif result == 1337:
                    pass

                else:
                    subguild = get_subguild(result, guild_name)
                    leader_id = get_field(subguild, "leader_id")
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
                            value = text.replace("[", "")
                            value = value.replace("]", "")
                            if value == "":
                                correct_arg = False
                                desc = "Вы не можете назвать гильдию пустой строкой"

                            elif value in [sg["name"] for sg in result["subguilds"]]:
                                correct_arg = False
                                desc = f"Гильдия с названием {anf(value)} уже есть"
                            
                            if not correct_arg:
                                reply = discord.Embed(
                                    title = "❌ Ошибка",
                                    description = desc,
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
                            atts = ctx.message.attachments
                            if atts != []:
                                value = atts[0].url
                            else:
                                value = text
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
                                description = f"**->** Профиль гильдии: `{pr}guild-info {subguild['name']}`",
                                color = mmorpg_col("clover")
                            )
                            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                            await ctx.send(embed = reply)

    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["delete-guild", "deleteguild", "dg"])
    async def delete_guild(self, ctx, *, guild_name):
        pr = ctx.prefix
        collection = db["subguilds"]
        result = collection.find_one(
            {"_id": ctx.guild.id, "subguilds.name": guild_name},
            projection={
                "subguilds.name": True,
                "subguilds.leader_id": True,
                "master_role_id": True,
                "log_channel": True
            }
        )

        if result is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = (
                    f"На сервере нет гильдий с названием **{guild_name}**\n"
                    f"Список гильдий: `{pr}guilds`"
                ),
                color = mmorpg_col("vinous")
            )
            await ctx.send(embed = reply)
        else:
            lc_id = get_field(result, "log_channel")
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

                log = discord.Embed(
                    title="💥 Удалена гильдия",
                    description=(
                        f"**Удалил:** {ctx.author}\n"
                        f"**Название:** {guild_name}\n"
                    ),
                    color=mmorpg_col("vinous")
                )
                await post_log(ctx.guild, lc_id, log)

    @commands.cooldown(1, 5, commands.BucketType.member)
    @commands.command(aliases = ["req", "request"])
    async def requests(self, ctx, page, *, search):
        pr = ctx.prefix
        collection = db["subguilds"]
        interval = 20

        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={
                "subguilds.members": False,
                "subguilds.description": False
            }
        )
        guild_name = await search_and_choose(get_field(result, "subguilds"), search, ctx.message, ctx.prefix, self.client)
        
        if guild_name is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = f"По запросу **{search}** не найдено гильдий"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif guild_name == 1337:
            pass
        
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
                    title = f"🛠 Гильдия {guild_name} не приватна",
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
                        title = f"📜 Список запросов в {guild_name} пуст"
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
                            f"**Принять запрос:** `{pr}accept Номер_запроса {guild_name}`\n"
                            f"**Отклонить запрос:** `{pr}decline Номер_запроса {guild_name}`\n\n"
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
    @commands.command(aliases = ["ac"])
    async def accept(self, ctx, num, *, search):
        collection = db["subguilds"]

        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={
                "subguilds.members": False,
                "subguilds.description": False
            }
        )
        guild_name = await search_and_choose(get_field(result, "subguilds"), search, ctx.message, ctx.prefix, self.client)

        if guild_name is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = f"По запросу **{search}** не найдено гильдий"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif guild_name == 1337:
            pass
        
        else:
            mr_id = get_field(result, "master_role_id")
            subguild = get_subguild(result, guild_name)
            del result

            length = len(subguild["requests"])

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
                    title = f"🛠 Гильдия {guild_name} не приватна",
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
                    new_data = {f"subguilds.$.members.{ID}": {"messages": 0} for ID in subguild["requests"]}

                    collection.find_one_and_update(
                        {"_id": ctx.guild.id, "subguilds.name": guild_name},
                        {"$set": new_data}
                    )
                    collection.find_one_and_update(
                        {"_id": ctx.guild.id},
                        {"$pull": {"subguilds.$[].requests": {"$in": subguild["requests"]}}},
                    )
                    desc = "Все заявки приняты."
                    
                else:
                    user_id = subguild["requests"][num - 1]

                    collection.find_one_and_update(
                        {"_id": ctx.guild.id, "subguilds.name": guild_name},
                        {"$set": {f"subguilds.$.members.{user_id}": {"messages": 0}}}
                    )
                    collection.find_one_and_update(
                        {"_id": ctx.guild.id},
                        {"$pull": {"subguilds.$[].requests": {"$in": [user_id]}}},
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
    @commands.command(aliases = ["dec"])
    async def decline(self, ctx, num, *, search):
        collection = db["subguilds"]

        result = collection.find_one(
            {"_id": ctx.guild.id},
            projection={
                "subguilds.members": False,
                "subguilds.description": False
            }
        )
        guild_name = await search_and_choose(get_field(result, "subguilds"), search, ctx.message, ctx.prefix, self.client)

        if guild_name is None:
            reply = discord.Embed(
                title = "💢 Упс",
                description = f"По запросу **{search}** не найдено гильдий"
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif guild_name == 1337:
            pass
        
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
                    title = f"🛠 Гильдия {guild_name} не приватна",
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
    @commands.command()
    async def kick(self, ctx, parameter, value = None, *, search = None):
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
        
        elif value is None or search is None:
            reply = discord.Embed(
                title = f"🛠 {pr}kick {parameter}",
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
                {"_id": ctx.guild.id},
                projection={
                    "subguilds.members": False,
                    "subguilds.description": False
                }
            )
            guild_name = await search_and_choose(get_field(result, "subguilds"), search, ctx.message, ctx.prefix, self.client)

            if guild_name is None:
                reply = discord.Embed(
                    title = "💢 Упс",
                    description = f"По запросу **{search}** не найдено гильдий"
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            elif guild_name == 1337:
                pass
            
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
                        res = collection.find_one_and_update(
                            {
                                "_id": ctx.guild.id,
                                "subguilds.name": guild_name,
                                f"subguilds.members.{user.id}": {"$exists": True}
                            },
                            {"$unset": {f"subguilds.$.members.{user.id}": ""}},
                            projection={"_id": True}
                        )
                        if res is not None:
                            reply = discord.Embed(
                                title = "✅ Выполнено",
                                description = f"{anf(user)} был исключён из гильдии **{guild_name}**",
                                color = mmorpg_col("clover")
                            )
                        else:
                            reply = discord.Embed(
                                title = "❌ Ошибка",
                                description = f"{anf(user)} не является членом гильдии **{guild_name}**",
                                color = mmorpg_col("vinous")
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
                                self.client.loop.create_task(remove_join_role(ctx.guild.get_member(ID), subguild["role_id"]))
                    
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
                                self.client.loop.create_task(remove_join_role(ctx.guild.get_member(ID), subguild["role_id"]))
                    
                    await ctx.send(embed = reply)

    #========== Errors ==========
    @create_guild.error
    async def create_guild_error(self, ctx, error):
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
    async def edit_guild_error(self, ctx, error):
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

    @delete_guild.error
    async def delete_guild_error(self, ctx, error):
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

    @requests.error
    async def requests_error(self, ctx, error):
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
    async def accept_error(self, ctx, error):
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
                    f"**Список заявок:** `{p}requests Страница Гильдия`"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @decline.error
    async def decline_error(self, ctx, error):
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
                    f"**Список заявок:** `{p}requests Страница Гильдия`"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @kick.error
    async def kick_error(self, ctx, error):
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
    async def reputation_error(self, ctx, error):
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


def setup(client):
    client.add_cog(guild_control(client))