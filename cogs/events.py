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
xo_award = 1

#---------- Functions ------------
from functions import has_permissions, detect, get_field, Leaderboard, read_message, trigger_reaction, is_command

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

async def post_log(guild, channel_id, log):
    if channel_id is not None:
        channel = guild.get_channel(channel_id)
        if channel is not None:
            await channel.send(embed=log)

class XO_field:
    def __init__(self, rows=3, columns=3):
        self.matrix = [[0 for j in range(columns)] for i in range(rows)]
        self.moves = 0
        self.max_moves = rows * columns
    
    def display(self):
        shapes = [":white_large_square:", ":negative_squared_cross_mark:", ":o2:"]
        row_num_textures = [":one:", ":two:", ":three:"]
        output = ":arrow_lower_right::regional_indicator_a::regional_indicator_b::regional_indicator_c:\n"
        for row, line in enumerate(self.matrix):
            display_line = str(row_num_textures[row])
            for value in line:
                display_line += shapes[value]
            output += display_line + "\n"
        return output[:-1]
    
    def get_looser(self):
        d = self.moves % 2 
        return 1 if d > 0 else 2

    def to_tuple(self, chess_formated):
        digits = [str(i) for i in range(10)]
        row = None
        if chess_formated[0] in digits:
            row = int(chess_formated[0]) - 1
            col = chess_formated[1]
        elif chess_formated[1] in digits:
            row = int(chess_formated[1]) - 1
            col = chess_formated[0]
        
        if row is not None:
            if col in ["a", "b", "c"] and abs(row - 1) <= 1:
                col = ["a", "b", "c"].index(col)
                return (row, col)
    
    def put(self, coords, value):
        if len(coords) >= 2:
            if isinstance(coords, str):
                coords = self.to_tuple(coords)
            if coords is not None and self.matrix[coords[0]][coords[1]] == 0:
                self.matrix[coords[0]][coords[1]] = value
                self.moves += 1
    
    def find_winners(self):
        lcross, rcross = [], []
        col_count_1, col_count_2 = [0, 0, 0], [0, 0, 0]
        for num, row in enumerate(self.matrix):
            if row.count(1) == 3:
                return 1
            elif row.count(2) == 3:
                return 2
            for col, v in enumerate(row):
                if v == 1:
                    col_count_1[col] += 1
                elif v == 2:
                    col_count_2[col] += 1
            lcross.append(row[num])
            rcross.append(row[2 - num])
        
        if lcross.count(1) == 3 or rcross.count(1) == 3 or 3 in col_count_1:
            return 1
        elif lcross.count(2) == 3 or rcross.count(2) == 3 or 3 in col_count_2:
            return 2
        elif self.moves >= self.max_moves:
            return 0
        else:
            return None


class events(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Events cog is loaded")
    
    #========= Commands ==========
    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["enable-event", "ee"])
    async def enable(self, ctx):
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
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"games_allowed": True}},
                upsert=True
            )
            reply = discord.Embed(
                title="✅ Выполнено",
                description="Теперь ивент активен на сервере",
                color=mmorpg_col("clover")
            )
            reply.set_footer(text = str(ctx.author), icon_url = str(ctx.author.avatar_url))
            await ctx.send(embed = reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["disable-event", "de"])
    async def disable(self, ctx):
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
            collection = db["subguilds"]
            collection.update_one(
                {"_id": ctx.guild.id},
                {"$set": {"games_allowed": False}},
                upsert=True
            )
            reply = discord.Embed(
                title="✅ Выполнено",
                description="Ивент выключен",
                color=mmorpg_col("clover")
            )
            reply.set_footer(text = str(ctx.author), icon_url = str(ctx.author.avatar_url))
            await ctx.send(embed = reply)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["ttt", "XO", "tic-tac-toe"])
    async def xo(self, ctx, *, string):
        p = ctx.prefix
        opponent = detect.member(ctx.guild, string)
        if opponent is None:
            reply = discord.Embed(
                title="💢 Упс",
                description=f"Не могу найти пользователя по запросу **{string}**",
                color=mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

        elif opponent.id == ctx.author.id:
            reply = discord.Embed(
                title="❓ С собой играть нельзя",
                description="Найдите себе соперника, с собой Вы не поиграете, увы.",
                color=mmorpg_col("vinous")
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)
        
        else:
            collection = db["subguilds"]
            result = collection.find_one(
                {"_id": ctx.guild.id},
                projection={
                    f"subguilds.members.{opponent.id}": True,
                    f"subguilds.members.{ctx.author.id}": True,
                    "subguilds.name": True,
                    "games_allowed": True,
                    "log_channel": True
                }
            )
            auth_guild = get_subguild(result, ctx.author.id)
            oppo_guild = get_subguild(result, opponent.id)
            games_allowed = get_field(result, "games_allowed", default=False)
            log_channel = get_field(result, "log_channel")
            guild_names = {
                ctx.author.id: get_field(auth_guild, "name"),
                opponent.id: get_field(oppo_guild, "name")
            }
            del result

            if not games_allowed:
                reply = discord.Embed(
                    title="❌ На этом сервере ивент выключен",
                    description=f"Включить: `{p}enable-event`",
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            elif auth_guild is None or oppo_guild is None:
                if auth_guild is None:
                    title = "Вы не в гильдии"
                    desc = f"Для вступления в гильдию напишите `{p}join Название гильдии`"
                else:
                    title = f"{anf(opponent)} не в гильдии"
                    desc = "Поищите другого оппонента"
                
                reply = discord.Embed(
                    title=title,
                    description=desc,
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)
            
            elif auth_guild == oppo_guild:
                reply = discord.Embed(
                    title="❌ Ошибка",
                    description="Противник должен быть из другой гильдии",
                    color=mmorpg_col("vinous")
                )
                reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                await ctx.send(embed = reply)

            else:
                request_emb = discord.Embed(
                    title=f"{anf(ctx.author)} бросил Вам вызов",
                    description="✅ - принять\n\n❌ - отказаться",
                    color=ctx.author.color
                )
                request = await ctx.send(f"{opponent.mention}", embed=request_emb)
                await request.add_reaction("✅")
                await request.add_reaction("❌")

                payload = await trigger_reaction(request, ["✅", "❌"], opponent, 60, self.client)
                if payload is None:
                    request_emb = discord.Embed(description=f"Вызов от {anf(ctx.author)} был проигнорирован участником **{anf(opponent)}** (прошло 60 секунд)")
                    await request.edit(embed=request_emb)
                elif payload[0].emoji == "❌":
                    request_emb = discord.Embed(
                        description=f"**{anf(opponent)}** отказался от вызова **{anf(ctx.author)}**",
                        color=discord.Color.dark_red()
                    )
                    await request.edit(embed=request_emb)
                else:
                    await request.delete()
                    game_info = discord.Embed(
                        title="🔰 Об игре",
                        color=discord.Color.blue()
                    )
                    game_info.add_field(name="**(:negative_squared_cross_mark:) Первый ходит:**", value=str(ctx.author), inline=False)
                    game_info.add_field(name="**(:o2:) Второй ходит:**", value=str(opponent), inline=False)
                    await ctx.send(embed=game_info)

                    players = (ctx.author, opponent)
                    xo = XO_field()
                    screen = await ctx.send(xo.display())
                    winner = None

                    while winner is None:
                        player = players[xo.moves % 2]
                        msg = await read_message(ctx.channel, player, 60, self.client)
                        if msg is None:
                            winner = xo.get_looser()
                        elif "quit" in msg.content.lower():
                            winner = xo.get_looser()
                        elif is_command(msg.content, ctx.prefix, self.client):
                            winner = xo.get_looser()
                        else:
                            xo.put(msg.content.lower(), xo.moves % 2 + 1)
                            winner = xo.find_winners()
                            await screen.edit(content=xo.display())

                            try:
                                await msg.delete()
                            except Exception:
                                pass
                    
                    if winner is not None:
                        if winner == 0:
                            reply = discord.Embed(
                                title="⚖ Ничья",
                                color=discord.Color.orange()
                            )
                            reply.add_field(name="**Игрок 1**", value=str(players[0]))
                            reply.add_field(name="**Игрок 2**", value=str(players[1]))
                            await ctx.send(embed=reply)

                        else:
                            looser = players[winner % 2]
                            winner = players[winner - 1]

                            collection.update_one(
                                {
                                    "_id": ctx.guild.id,
                                    "subguilds.name": guild_names[looser.id],
                                    f"subguilds.members.{looser.id}": {"$exists": True}
                                },
                                {"$inc": {f"subguilds.$.reputation": -xo_award}}
                            )
                            collection.update_one(
                                {
                                    "_id": ctx.guild.id,
                                    "subguilds.name": guild_names[winner.id],
                                    f"subguilds.members.{winner.id}": {"$exists": True}
                                },
                                {"$inc": {f"subguilds.$.reputation": xo_award}}
                            )

                            reply = discord.Embed(
                                title=f"🏆 Выиграл {winner}",
                                color=discord.Color.gold()
                            )
                            reply.add_field(name="**Игрок 1**", value=f"+{xo_award} 🔅 | {anf(winner)}\nГильдия: {guild_names[winner.id]}")
                            reply.add_field(name="**Игрок 2**", value=f"-{xo_award} 🔅 | {anf(looser)}\nГильдия: {guild_names[looser.id]}")
                            await ctx.send(embed=reply)

                            await post_log(ctx.guild, log_channel, reply)

    #======= Errors ========
    @xo.error
    async def exile_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            p = ctx.prefix
            cmd = ctx.command.name
            reply = discord.Embed(
                title = f"❓ Об аргументах `{p}{cmd}`",
                description = (
                    "**Описание:** начинает игру в крестики-нолики\n"
                    f"**Использование:** `{p}{cmd} @Участник`\n"
                    f"**Пример:** `{p}{cmd} @User#1234`"
                )
            )
            reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
            await ctx.send(embed = reply)

def setup(client):
    client.add_cog(events(client))