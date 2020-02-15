import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import os

import pymongo
from pymongo import MongoClient

prefix = "^"
client = commands.Bot(command_prefix=prefix)
client.remove_command("help")
owner_ids = [301295716066787332]

token = str(os.environ.get("guild_manager_token"))
app_string = str(os.environ.get("cluster_app_string"))
default_avatar_url = "https://cdn.discordapp.com/attachments/664230839399481364/677534213418778660/default_image.png"

cluster = MongoClient(app_string)
db = cluster["guild_data"]

def carve_int(string):
    nums = [str(i) for i in range(10)]
    out = ""
    found = False
    for letter in string:
        if letter in nums:
            found = True
            out += letter
        elif found:
            break
    if out == "":
        out = None
    else:
        out = int(out)
    return out

def get_subguild(collection_part, subguild_name):
    out = None
    subguilds = collection_part["subguilds"]
    for subguild in subguilds:
        if subguild["name"] == subguild_name:
            out = subguild
            break
    return out

def perms_for(role):
    owned = {
    "create_instant_invite": role.permissions.create_instant_invite,
    "kick_members": role.permissions.kick_members,
    "ban_members": role.permissions.ban_members,
    "administrator": role.permissions.administrator,
    "manage_channels": role.permissions.manage_channels,
    "manage_roles": role.permissions.manage_roles,
    "manage_guild": role.permissions.manage_guild,
    "view_audit_log": role.permissions.view_audit_log,
    "change_nickname": role.permissions.change_nickname,
    "manage_nicknames": role.permissions.manage_nicknames,
    "manage_webhooks": role.permissions.manage_webhooks,
    "manage_messages": role.permissions.manage_messages,
    "manage_emojis": role.permissions.manage_emojis,
    "mention_everyone": role.permissions.mention_everyone
    }
    return owned

def has_permissions(member, perm_array):
    to_have = len(perm_array)
    if member.id == member.guild.owner_id:
        return True
    else:
        found_num = 0
        found = []
        for role in member.roles:
            owned = perms_for(role)
            if owned["administrator"]:
                found_num = to_have
            else:
                for perm in perm_array:
                    if not perm in found and owned[perm]:
                        found.append(perm)
                        found_num += 1
            if found_num >= to_have:
                break
                    
        return True if found_num >= to_have else False

def has_any_permission(member, perm_array):
    if member.id == member.guild.owner_id:
        return True
    else:
        has = False
        for perm in perm_array:
            for role in member.roles:
                role_perms = perms_for(role)
                if role_perms["administrator"] or role_perms[perm]:
                    has = True
                    break
            if has:
                break
        return has

def has_roles(member, role_array):
    has_them = True
    if not has_permissions(member, ["administrator"]):
        for role in role_array:
            if not role in member.roles:
                has_them = False
                break
    return has_them

async def read_message(channel, user, t_out):
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

async def give_join_role(member, role_id):
    if role_id != None:
        role = discord.utils.get(member.guild.roles, id = role_id)
        if role != None:
            await member.add_roles(role)
    return

class detect:
    @staticmethod
    def member(guild, search):
        ID = carve_int(search)
        if ID == None:
            ID = 0
        member = discord.utils.get(guild.members, id=ID)
        return member
    
    @staticmethod
    def channel(guild, search):
        ID = carve_int(search)
        if ID == None:
            ID = 0
        channel = discord.utils.get(guild.channels, id=ID)
        return channel
    
    @staticmethod
    def role(guild, search):
        ID = carve_int(search)
        if ID == None:
            ID = 0
        role = discord.utils.get(guild.roles, id=ID)
        return role

@client.event
async def on_ready():
    print(
        ">> Bot is ready\n"
        f">> Prefix is {prefix}\n"
        f">> Bot user: {client.user}"
    )
#=========Commands==========
@client.command()
async def logout(ctx):
    if ctx.author.id in owner_ids:
        await ctx.send("Logging out...")
        await client.logout()

@client.command()
async def help(ctx):
    p = prefix
    cmd_desc = (
        f"**{p}join-guild [**Гильдия**]** - *зайти в гильдию*\n"
        f"**{p}leave-guild** - *выйти из текущей гильдии*\n"
        f"**{p}guilds** - *топ гильдий сервера*\n"
        f"**{p}guild-info [**Гильдия**]** - *посмотреть подробности гильдии*\n"
        f"**{p}create-guild [**Название**]** - *создаёт гильдию*\n"
        f'**{p}edit-guild [**Параметр**] "**Гильдия**" [**Новое значение**]** - *подробнее: {p}edit-guild*\n'
        f"**{p}delete-guild [**Гильдия**]** - *удаляет гильдию*"
    )
    help_emb = discord.Embed(
        title = f"📰 Список команд",
        description = cmd_desc,
        color = discord.Color.from_rgb(150, 150, 150)
    )
    await ctx.send(embed = help_emb)

@client.command(aliases = ["create-guild", "createguild", "cg"])
async def create_guild(ctx, *, guild_name):
    collection = db["subguilds"]

    if not has_permissions(ctx.author, ["administrator"]):
        reply = discord.Embed(
            title = "💢 Недостаточно прав",
            description = (
                "Требуемые права:\n"
                "> Администратор"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    
    else:
        result = collection.find_one({"_id": ctx.guild.id, "subguilds.name": guild_name}, projection={"_id": True})
        if result != None:
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
                            "role_id": None,
                            "members": {
                                f"{ctx.author.id}": {
                                    "id": ctx.author.id,
                                    "messages": 0
                                }
                            }
                        }
                    }
                },
                upsert=True
            )

            reply = discord.Embed(
                title = f"✅ Гильдия **{guild_name}** создана",
                description = (
                    f"Отредактировать гильдию: `{prefix}edit-guild`\n"
                    "**-> Описание:** Без описания"
                ),
                color = discord.Color.green()
            )
            reply.set_thumbnail(url = default_avatar_url)
            reply.add_field(name = "Владелец", value = f"{ctx.author}")
            reply.add_field(name = "Кол-во участников", value = "1")
            await ctx.send(embed = reply)

@client.command(aliases = ["edit-guild", "editguild", "eg"])
async def edit_guild(ctx, parameter, *, text_data):
    collection = db["subguilds"]
    parameter = parameter.lower()
    parameters = {
        "name": "name",
        "description": "description",
        "avatar": "avatar_url",
        "leader": "leader_id",
        "role": "role_id"
    }
    guild_name = ""
    i = 0
    if parameter not in parameters:
        reply = discord.Embed(
            title = "📑 Доступные параметры настроек",
            description = (
                "> `name`\n"
                "> `description`\n"
                "> `avatar`\n"
                "> `leader`\n"
                "> `role`\n"
                f'**Использование:** `{prefix}{ctx.command.name} Параметр "Название гильдии" [Новое значение]`\n'
                f'**Пример:** `{prefix}{ctx.command.name} name "Дамы и господа" Хранители`\n'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        if not text_data.startswith('"'):
            while text_data[i] != " ":
                guild_name += text_data[i]
                i += 1
        else:
            i = 1
            while text_data[i] != '"':
                guild_name += text_data[i]
                i += 1
        text = text_data[+i+1:].lstrip()

        result = collection.find_one(
            filter={"_id": ctx.guild.id, "subguilds.name": guild_name},
            projection={"subguilds.members": False}
        )
        if result == None:
            reply = discord.Embed(
                title = "💢 Ошибка",
                description = f"Гильдии с названием **{guild_name}** нет на сервере",
                color = discord.Color.from_rgb(40, 40, 40)
            )
            await ctx.send(embed = reply)
        
        else:
            subguild = get_subguild(result, guild_name)
            leader_id = subguild["leader_id"]

            if ctx.author.id != leader_id and not has_permissions(ctx.author, ["administrator"]):
                reply = discord.Embed(
                    title = "❌ Недостаточно прав",
                    description = f"Вы не являетесь главой гильдии **{guild_name}** или администратором.",
                    color = discord.Color.dark_red()
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                correct_arg = True
                value = text
                if parameter == "leader":
                    value = detect.member(ctx.guild, text)
                    if value == None:
                        correct_arg = False

                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Вы ввели {text}, подразумевая участника, но он не был найден",
                            color = discord.Color.from_rgb(40, 40, 40)
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)
                    else:
                        value = value.id
                elif parameter == "role":
                    value = detect.role(ctx.guild, text)
                    if text.lower() == "delete":
                        value = None
                    elif value == None:
                        correct_arg = False

                        reply = discord.Embed(
                            title = "💢 Ошибка",
                            description = f"Вы ввели {text}, подразумевая роль, но она не была найдена",
                            color = discord.Color.from_rgb(40, 40, 40)
                        )
                        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                        await ctx.send(embed = reply)
                    else:
                        value = value.id
                
                if correct_arg:
                    subguild[parameters[parameter]] = value

                    collection.find_one_and_update(
                        {"_id": ctx.guild.id, "subguilds.name": guild_name},
                        {"$set": {f"subguilds.$.{parameters[parameter]}": value}}
                    )

                    reply = discord.Embed(
                        title = "✅ Настроено",
                        description = f"**->** Профиль гильдии: `{prefix}guild-info {subguild['name']}`",
                        color = discord.Color.green()
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

@client.command(aliases = ["delete-guild", "deleteguild", "dg"])
async def delete_guild(ctx, *, guild_name):
    collection = db["subguilds"]
    result = collection.find_one(
        {"_id": ctx.guild.id, "subguilds.name": guild_name},
        projection={"subguilds.name": True, "subguilds.leader_id": True}
    )
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{prefix}guilds`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        await ctx.send(embed = reply)
    else:
        subguild = get_subguild(result, guild_name)
        del result

        if ctx.author.id != subguild["leader_id"] and not has_permissions(ctx.author, ["administrator"]):
            reply = discord.Embed(
                title = "❌ Недостаточно прав",
                description = f"Вы не являетесь главой гильдии **{guild_name}** или администратором",
                color = discord.Color.dark_red()
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
                description = f"Вы удалили гильдию **{guild_name}**",
                color = discord.Color.from_rgb(40, 40, 40)
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

@client.command(aliases = ["join-guild", "joinguild", "jg"])
async def join_guild(ctx, *, guild_name):
    collection = db["subguilds"]

    result = collection.find_one(
        {
            "_id": ctx.guild.id,
            "subguilds.name": guild_name
        },
        projection={"subguilds.name": True, "subguilds.members": True, "subguilds.role_id": True}
    )
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{prefix}guilds`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        await ctx.send(embed = reply)
    else:
        subguild = get_subguild(result, guild_name)
        guild_role_id = subguild["role_id"]
        del subguild

        result = result["subguilds"]
        user_guild = None
        for subguild in result:
            if f"{ctx.author.id}" in subguild["members"]:
                user_guild = subguild["name"]
                break
        del result

        if guild_name == user_guild:
            reply = discord.Embed(
                title = "❌ Ошибка",
                description = f"Вы уже являетесь членом гильдии **{guild_name}**",
                color = discord.Color.dark_red()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        elif user_guild != None:
            reply = discord.Embed(
                title = "🛠 О смене гильдий",
                description = (
                    f"В данный момент Вы являетесь членом гильдии **{user_guild}**.\n"
                    f"Для того, чтобы войти в другую гильдию, Вам нужно выйти из текущей, однако, **не забывайте**:\n"
                    f"**->** Счётчик сообщений участника обнуляется при выходе.\n"
                    f"Команда для выхода: `{prefix}leave-guild`"
                ),
                color = discord.Color.from_rgb(40, 40, 40)
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        else:
            collection.find_one_and_update(
                {"_id": ctx.guild.id, "subguilds.name": guild_name},
                {
                    "$set": {
                        f"subguilds.$.members.{ctx.author.id}": {
                            "id": ctx.author.id,
                            "messages": 0
                        }
                    }
                }
            )

            await give_join_role(ctx.author, guild_role_id)

            reply = discord.Embed(
                title = "✅ Добро пожаловать",
                description = f"Вы вступили в гильдию **{guild_name}**",
                color = discord.Color.green()
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

@client.command(aliases = ["leave-guild", "leaveguild", "lg"])
async def leave_guild(ctx):
    collection = db["subguilds"]

    result = collection.find_one(
        {
            "_id": ctx.guild.id,
            f"subguilds.members.{ctx.author.id}.id": ctx.author.id
        },
        projection={"subguilds.name": True, "subguilds.members": True}
    )
    if result == None:
        reply = discord.Embed(
            title = "❌ Ошибка",
            description = f"Вас нет ни в одной гильдии",
            color = discord.Color.dark_red()
        )
        reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)
    else:
        result = result["subguilds"]
        for subguild in result:
            if f"{ctx.author.id}" in subguild["members"]:
                guild_name = subguild["name"]
                break
        del result

        no = ["no", "0", "нет"]
        yes = ["yes", "1", "да"]

        warn_emb = discord.Embed(
            title = "🛠 Подтверждение",
            description = (
                f"**->** Ваш счётчик сообщений обнулится, как только Вы покинете гильдию **{guild_name}**.\nПродолжить?\n"
                f"Напишите `да` или `нет`"
            )
        )
        warn_emb.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
        warn = await ctx.send(embed = warn_emb)

        msg = await read_message(ctx.channel, ctx.author, 60)
        await warn.delete()

        if msg != "Timeout":
            user_reply = msg.content.lower()
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

                reply = discord.Embed(
                    title = "🚪 Выход",
                    description = f"Вы вышли из гильдии **{guild_name}**"
                )
                reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

@client.command()
async def guilds(ctx):
    collection = db["subguilds"]

    result = collection.find_one({"_id": ctx.guild.id})
    if result == None:
        lb = discord.Embed(
            title = f"Гильдии сервера {ctx.guild.name}",
            description = "Отсутствуют",
            color = discord.Color.blue()
        )
        lb.set_thumbnail(url = f"{ctx.guild.icon_url}")
        await ctx.send(embed = lb)
    else:
        subguilds = result["subguilds"]

        stats = []
        for subguild in subguilds:
            total_mes = 0
            for str_id in subguild["members"]:
                memb = subguild["members"][str_id]
                total_mes += memb["messages"]

            pair = (f"{subguild['name']}", total_mes)
            stats.append(pair)
        del result
        stats.sort(key=lambda i: i[1])
        stats.reverse()

        desc = ""
        for i in range(len(stats)):
            guild_name = stats[i][0]
            total_mes = stats[i][1]
            desc += f"**{i+1})** {guild_name} • **{total_mes}** `💬`\n"
        
        lb = discord.Embed(
            title = f"Гильдии сервера {ctx.guild.name}",
            description = desc,
            color = discord.Color.dark_blue()
        )
        lb.set_thumbnail(url = f"{ctx.guild.icon_url}")
        await ctx.send(embed = lb)

@client.command(aliases = ["guild-info", "guildinfo", "gi"])
async def guild_info(ctx, *, guild_name):
    collection = db["subguilds"]

    result = collection.find_one({"_id": ctx.guild.id, "subguilds.name": guild_name})
    if result == None:
        reply = discord.Embed(
            title = "💢 Упс",
            description = (
                f"На сервере нет гильдий с названием **{guild_name}**\n"
                f"Список гильдий: `{prefix}guilds`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        await ctx.send(embed = reply)
    else:
        subguild = get_subguild(result, guild_name)
        del result

        total_mes = 0
        total_memb = 0
        for str_id in subguild["members"]:
            memb = subguild["members"][str_id]
            total_mes += memb["messages"]
            total_memb += 1
        subguild["members"] = None
        leader = client.get_user(subguild["leader_id"])
        
        reply = discord.Embed(
            title = subguild["name"],
            description = subguild["description"],
            color = discord.Color.green()
        )
        reply.set_thumbnail(url = subguild["avatar_url"])
        reply.add_field(name = "🔰 Владелец", value = f"{leader}", inline=False)
        reply.add_field(name = "👥 Всего участников", value = f"{total_memb}", inline=False)
        reply.add_field(name = "`💬` Всего сообщений", value = f"{total_mes}", inline=False)
        if subguild["role_id"] != None:
            reply.add_field(name = "🎗 Роль", value = f"<@&{subguild['role_id']}>", inline = False)
        await ctx.send(embed = reply)

#========Events========
@client.event
async def on_message(message):
    await client.process_commands(message)
    collection = db["subguilds"]

    if not message.author.bot:
        collection.find_one_and_update(
            {
                "_id": message.guild.id,
                f"subguilds.members.{message.author.id}.id": message.author.id
                },
            {
                "$inc": {
                    f"subguilds.$.members.{message.author.id}.messages": 1
                }
            }
        )

#========Errors==========
@create_guild.error
async def create_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "🛠 Недостаточно аргументов",
            description = (
                f"**Использование:** `{prefix}{ctx.command.name} [Название гильдии]`\n"
                f"**Пример:** `{prefix}{ctx.command.name} Дамы и господа`"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@edit_guild.error
async def edit_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Об аргументах",
            description = (
                "> `name`\n"
                "> `description`\n"
                "> `avatar`\n"
                "> `leader`\n"
                "> `role`\n"
                f'**Использование:** `{prefix}{ctx.command.name} Параметр "Название гильдии" [Новое значение]`\n'
                f'**Пример:** `{prefix}{ctx.command.name} name "Дамы и господа" Хранители`\n'
                f'**Примечания:**\n'
                f'-> Если в названии гильдии есть пробелы, то название нужно указать **"в кавычках"**\n'
                f"-> Если настраиваете владельца или роль гильдии, укажите **@упоминание** или **ID**\n"
                f"-> Если нужно убрать роль гильдии, напишите **delete** в качестве нового значения\n"
                f"-> Если хотите поставить новый аватар гильдии, то в качестве аргумента введите ссылку на картинку\n"
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@join_guild.error
async def join_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Название гильдии`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@delete_guild.error
async def delete_guild_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Название гильдии`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

@guild_info.error
async def guild_info_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        reply = discord.Embed(
            title = "📑 Недостаточно аргументов",
            description = (
                f'**Использование:** `{prefix}{ctx.command.name} Название гильдии`'
            ),
            color = discord.Color.from_rgb(40, 40, 40)
        )
        reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
        await ctx.send(embed = reply)

client.run(token)
