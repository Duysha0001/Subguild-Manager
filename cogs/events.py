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

#---------- Functions ------------
from functions import has_permissions, detect, get_field, Leaderboard

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

class events(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Events cog is loaded")
    
    #========= Commands ==========
    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["deploy-night-watch", "dnw"])
    async def deploy_night_watch(self, ctx):
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
            structure = {
                "members": {},
                "reputation": 100,
                "mentions": 0
            }

            collection = db["subguilds"]
            result = collection.find_one(
                {"_id": ctx.guild.id, "night_watch": {"$exists": False}},
                projection={"subguilds": False}
            )
            if result is None:
                reply = discord.Embed(
                    title="❌ Ошибка",
                    description="Ночной Дозор уже развёрнут",
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                collection.find_one_and_update(
                    {"_id": ctx.guild.id},
                    {"$set": {"night_watch": structure}}
                )
                reply = discord.Embed(
                    title="☄ Выполнено",
                    description="Ночной Дозор развёрнут",
                    color=3430312
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

    @commands.cooldown(1, 10, commands.BucketType.member)
    @commands.command(aliases = ["end-night-watch", "enw"])
    async def end_night_watch(self, ctx):
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
            collection = db["subguilds"]
            result = collection.find_one_and_update(
                {"_id": ctx.guild.id, "night_watch": {"$exists": True}},
                {"$unset": {"night_watch": ""}},
                projection={"subguilds": False}
            )
            if result is None:
                reply = discord.Embed(
                    title="❌ Ошибка",
                    description="Ночной Дозор не развёрнут",
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                reply = discord.Embed(
                    title="☄ Выполнено",
                    description="Ночной Дозор отозван",
                    color=3430312
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases = ["ex"])
    async def exile(self, ctx, *, member_s):
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
            member = detect.member(ctx.guild, member_s)
            if member is None:
                reply = discord.Embed(
                    title="💢 Упс",
                    description=f"Не могу найти пользователя по поиску **{member_s}**",
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                collection = db["subguilds"]
                result = collection.find_one(
                    {"_id": ctx.guild.id, "night_watch": {"$exists": True}},
                    projection={"subguilds": False}
                )
                if result is None:
                    reply = discord.Embed(
                        title="❌ Ошибка",
                        description="Ночной Дозор не развёрнут",
                        color=mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)
                
                elif f"{member.id}" in result["night_watch"]["members"]:
                    reply = discord.Embed(
                        title="❌ Полегче",
                        description=f"{member} уже сослан в Ночной Дозор",
                        color=mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

                else:
                    collection.find_one_and_update(
                        {"_id": ctx.guild.id},
                        {
                            "$set": {f"night_watch.members.{member.id}": 0},
                            "$unset": {f"subguilds.$[].members.{member.id}": ""},
                            "$pull": {"subguilds.$[].requests": {"$in": [member.id]}}
                        }
                    )
                    reply = discord.Embed(
                        title="🌑 Участник сослан",
                        description=f"**{member}** был сослан в Ночной Дозор.",
                        color=1517644
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command()
    async def pick(self, ctx, *, member_s):
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
            member = detect.member(ctx.guild, member_s)
            if member is None:
                reply = discord.Embed(
                    title="💢 Упс",
                    description=f"Не могу найти пользователя по поиску **{member_s}**",
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                collection = db["subguilds"]
                result = collection.find_one(
                    {"_id": ctx.guild.id, "night_watch": {"$exists": True}},
                    projection={"subguilds": False}
                )
                if result is None:
                    reply = discord.Embed(
                        title="❌ Ошибка",
                        description="Ночной Дозор не развёрнут",
                        color=mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)
                
                elif f"{member.id}" not in result["night_watch"]["members"]:
                    reply = discord.Embed(
                        title="❌ Ошибка",
                        description=f"{member} нет в Ночном Дозоре",
                        color=mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

                else:
                    collection.find_one_and_update(
                        {"_id": ctx.guild.id},
                        {"$unset": {f"night_watch.members.{member.id}": ""}}
                    )
                    reply = discord.Embed(
                        title="🌑 Участник вызволен",
                        description=f"**{member}** уходит из Ночного Дозора.",
                        color=1517644
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["night-watch", "nw"])
    async def night_watch(self, ctx, page="1"):
        if not page.isdigit():
            reply = discord.Embed(
                title = "💢 Упс",
                description = f"Номер страницы ({page}) должен быть целым числом, например `1`",
                color = mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
            await ctx.send(embed=reply)

        else:
            page = int(page)
            collection = db["subguilds"]
            result = collection.find_one(
                {"_id": ctx.guild.id, "night_watch": {"$exists": True}},
                projection={"subguilds": False}
            )
            nightw = get_field(result, "night_watch")
            if nightw is None:
                reply = discord.Embed(
                    title="❌ Упс",
                    description="Ночной Дозор не развёрнут",
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            else:
                pairs, total_xp = [], 0
                for key in nightw["members"]:
                    _xp = nightw["members"][key]
                    pairs.append((int(key), _xp))
                    total_xp += _xp

                lb = Leaderboard(pairs)
                del pairs
                total_pages = lb.total_pages
                passed_page_check = True
                if total_pages == 0:
                    desc = "Ночной Дозор пустует"
                    total_pages += 1

                elif page > lb.total_pages or page < 1:
                    passed_page_check = False
                    reply = discord.Embed(
                        title = "📖 Страница не найдена",
                        description = f"Всего страниц: {total_pages}"
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url=f"{ctx.author.avatar_url}")
                    await ctx.send(embed=reply)
                
                else:
                    lb.sort_values()
                    my_page, pos = lb.get_page(page)
                    del lb
                    desc = ""
                    for pair in my_page:
                        pos += 1
                        member = ctx.guild.get_member(pair[0])
                        desc += f"`{pos}.` {anf(member)} • **{pair[1]}** `🌀`\n"
                
                if passed_page_check:
                    reply = discord.Embed(
                        title="🌑 Ночной Дозор",
                        description=(
                            "`🌀` **Всего опыта:**\n"
                            f"> {total_xp}\n\n"
                            "`🔮` **Репутация:**\n"
                            f"> {nightw['reputation']}\n\n"
                            "`📜` **Упоминаний:**\n"
                            f"> {nightw['mentions']}\n\n"
                        ),
                        color=1517644
                    )
                    reply.add_field(
                        name=f"⚔ **Лидеры** (стр. {page}/{total_pages})",
                        value=desc
                    )
                    reply.set_thumbnail(url="https://cdn.discordapp.com/attachments/607184612476583946/705815261101424700/igra-prestolov-game-of-7317.jpg")
                    await ctx.send(embed=reply)

    #======= Errors ========
    @exile.error
    async def exile_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** ссылает участника сервера в Ночной Дозор\n"
                    f"**Использование:** `{p}{cmd} @Участник`\n"
                    f"**Пример:** `{p}{cmd} @User#1234`"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

    @pick.error
    async def pick_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** забирает участника сервера из Ночного Дозора\n"
                    f"**Использование:** `{p}{cmd} @Участник`\n"
                    f"**Пример:** `{p}{cmd} @User#1234`"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

def setup(client):
    client.add_cog(events(client))