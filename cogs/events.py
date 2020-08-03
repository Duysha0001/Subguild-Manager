import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio, os, datetime

import pymongo
from pymongo import MongoClient

app_string = str(os.environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

import os, json

#---------- Variables ------------
xo_award = 1
xol_award = 3

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

def isnested(section, array):
    i = 0; v = 0; res = False
    slen = len(section); alen = len(array)
    while i < alen:
        if v < slen:
            if array[i] == section[v]:
                v += 1
            else:
                v = 0
        if v >= slen:
            res = True
            break
        i += 1
    return res

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


class XO_universal:
    def __init__(self, rows=3, columns=3, req=3):
        self.matrix = [[0 for j in range(columns)] for i in range(rows)]
        self.moves = 0
        self.max_moves = rows * columns
        self.rows = rows; self.columns = columns
        self.req = req
    
    def display(self):
        shapes = ["⬜", "❎", ":o2:"]
        row_num_textures = [":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:", ":keycap_ten:"]
        col_letter_textures = [f":regional_indicator_{l}:" for l in ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]]
        left_upper_corner = ":arrow_lower_right:"
        output = f"{left_upper_corner}{''.join(col_letter_textures[:self.columns])}\n"
        for row, line in enumerate(self.matrix):
            display_line = str(row_num_textures[row])
            for value in line:
                display_line += shapes[value]
            output += display_line + "\n"
        return output[:-1]
    
    def get_looser(self):
        if self.moves < 2:
            return 0
        else:
            return 1 if self.moves % 2 > 0 else 2

    def to_tuple(self, chess_formated):
        # 1 letter is required. Not more and mot less
        chess_formated = chess_formated.lower()
        letters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        # Check
        def check(l, d):
            if l in letters and d.isdigit():
                col = letters.index(l)
                row = int(d) - 1
                if (0 <= col < self.columns) and (0 <= row < self.rows):
                    return (row, col)
        # Check Letter|Digits
        res = check(chess_formated[0], chess_formated[1:])
        if res is None:
            # Check Digits|Letter
            return check(chess_formated[-1:], chess_formated[:-1])
        else:
            return res
    
    def put(self, coords, value):
        if len(coords) >= 2:
            if isinstance(coords, str):
                coords = self.to_tuple(coords)
            if coords is not None and self.matrix[coords[0]][coords[1]] == 0:
                self.matrix[coords[0]][coords[1]] = value
                self.moves += 1
    
    def find_winners(self):
        res = 0
        lds = []; rds = []; cols = []
        ldcs = []; rdcs = []
        xrow = self.req * [1]; orow = self.req * [2]

        def check(sec):
            if isnested(xrow, sec):
                return 1
            elif isnested(orow, sec):
                return 2
            else:
                return 0

        for r, row in enumerate(self.matrix):
            # Row check
            res = check(row)
            if res > 0:
                break

            for c, cell in enumerate(row):
                # Filling columns
                if c >= len(cols) and self.rows >= self.req:
                    cols.append([cell])
                else:
                    cols[c].append(cell)
                
                # Filling left diagonals
                try:
                    n = ldcs.index((r, c))
                except Exception:
                    if self.columns - c >= self.req and self.rows - r >= self.req:
                        ldcs.append((r + 1, c + 1))
                        lds.append([cell])
                else:
                    ldcs[n] = (r + 1, c + 1)
                    lds[n].append(cell)
                
                # Filling right diagonals
                try:
                    n = rdcs.index((r, c))
                except Exception:
                    if c + 1 >= self.req and self.rows - r >= self.req:
                        rdcs.append((r + 1, c - 1))
                        rds.append([cell])
                else:
                    rdcs[n] = (r + 1, c - 1)
                    rds[n].append(cell)
            
        # Columns check
        if res > 0:
            return res
        else:
            del ldcs, rdcs
            for s in cols:
                res = check(s)
                if res > 0:
                    break
            del cols
            # Left diagonals check
            if res > 0:
                return res
            else:
                for s in lds:
                    res = check(s)
                    if res > 0:
                        break
                del lds
                # Right diagonals check
                if res > 0:
                    return res
                else:
                    for s in rds:
                        res = check(s)
                        if res > 0:
                            break
                    del rds
                    # Final return
                    if res > 0:
                        return res
                    elif self.moves >= self.max_moves:
                        return 0
                    else:
                        return None


# Remembering players that are in games
class XO_Memory:
    def __init__(self, player1=None, player2=None):
        self.path = "XO_Games"

        if None not in [player1, player2]:
            self.guild_id = player1.guild.id
            self.bucket = self.guild_id >> 55
            self.id1 = player1.id
            self.id2 = player2.id
        else:
            self.guild_id = None; self.bucket = None
            self.id1 = None; self.id2 = None
    
    def reset_path(self):
        try:
            if self.path in os.listdir("."):
                os.remove(self.path)
            os.mkdir(self.path)
        except Exception as e:
            print(e)
    
    def save(self):
        try:
            sb = str(self.bucket)
            my_dir = f"{self.path}/{sb}/{self.guild_id}.json"
            if sb in os.listdir(self.path):
                if f"{self.guild_id}.json" in os.listdir(f"{self.path}/{sb}"):
                    with open(my_dir, "r") as _file:
                        data = json.load(_file)
                    
                    if self.id1 in data:
                        return self.id1
                    elif self.id2 in data:
                        return self.id2
                    else:
                        data.extend([self.id1, self.id2])
                        with open(my_dir, "w") as _file:
                            json.dump(data, _file)
                else:
                    with open(my_dir, "w") as _file:
                        json.dump([self.id1, self.id2], _file)
            else:
                os.mkdir(f"{self.path}/{sb}")
                with open(my_dir, "w") as _file:
                    json.dump([self.id1, self.id2], _file)
        except Exception:
            pass
    
    def pop(self):
        if None not in [self.bucket, self.id1]:
            sb = str(self.bucket)
            my_dir = f"{self.path}/{sb}/{self.guild_id}.json"
            if sb in os.listdir(self.path) and f"{self.guild_id}.json" in os.listdir(f"{self.path}/{sb}"):
                with open(my_dir, "r") as _file:
                    data = json.load(_file)
                try:
                    data.remove(self.id1)
                    data.remove(self.id2)
                except Exception:
                    pass
                with open(my_dir, "w") as _file:
                    json.dump(data, _file)


class events(commands.Cog):
    def __init__(self, client):
        self.client = client

    #========== Events ===========
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Events cog is loaded")
        xom = XO_Memory()
        xom.reset_path()
    
    #========= Command-like functions==========
    async def xo_organizer(self, ctx, string, xou_args=[3, 3, 3]):
        mode_desc = f"{xou_args[0]}x{xou_args[1]}"
        if xou_args[0] < 10:
            xoaward = xo_award
        else:
            xoaward = xol_award
        
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
                xom = XO_Memory(ctx.author, opponent)  # Prepairing game memory
                _id = xom.save()   #Trying to save the game
                free = False
                if _id == ctx.author.id:
                    desc = f"Вы не можете снова бросать вызов, пока вы в игре."
                elif _id == opponent.id:
                    desc = f"Ваш противник уже в игре."
                else:
                    free = True
                if not free:
                    reply = discord.Embed(
                        title="❌ Ошибка",
                        description=desc,
                        color=mmorpg_col("vinous")
                    )
                    reply.set_footer(text = f"{ctx.author}", icon_url = f"{ctx.author.avatar_url}")
                    await ctx.send(embed = reply)

                else:
                    request_emb = discord.Embed(
                        title=f"{anf(ctx.author)} бросил Вам вызов | {mode_desc}",
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

                        players = (ctx.author, opponent)
                        sign = ["❎", ":o2:"]
                        xo = XO_universal(*xou_args)
                        winner = None

                        game_info = discord.Embed(
                            title=f"🔰 Раунд | {mode_desc}",
                            description=f"**{anf(players[0])}** vs **{anf(players[1])}**\n\n{xo.display()}",
                            color=discord.Color.blue()
                        )
                        game_info.add_field(name="**Сейчас ходит:**", value=f"{sign[0]} | {anf(players[0])}")
                        game_info.set_footer(text="Выйти: quit | Предложить ничью: draw")
                        screen = await ctx.send(embed=game_info)

                        while winner is None:
                            ipl = xo.moves % 2
                            player = players[ipl]
                            msg = await read_message(ctx.channel, player, 60, self.client)
                            if msg is None:
                                winner = xo.get_looser()
                            elif "draw" in msg.content.lower():
                                notif = discord.Embed(
                                    title=f"🤝 | {anf(player)} предлагает ничью",
                                    description="Написать `да` - согласиться\nНаписать `нет` - продолжить игру",
                                    color=discord.Color.gold()
                                )
                                notif.set_footer(text='У Вас есть 60 секунд, после чего будет засчитано "нет"')
                                player2 = players[(ipl + 1) % 2]
                                bot_msg = await ctx.send(content=str(player2.mention), embed=notif)

                                msg2 = await read_message(ctx.channel, player2, 60, self.client)
                                if msg2 is not None and msg2.content.lower() in ["да", "yes"]:
                                    winner = 0
                                else:
                                    try:
                                        await bot_msg.delete()
                                    except Exception:
                                        pass

                            elif "quit" in msg.content.lower():
                                winner = xo.get_looser()
                            else:
                                prev_moves = xo.moves
                                xo.put(msg.content.lower(), ipl + 1)
                                # Check if coords were correct
                                if xo.moves > prev_moves:
                                    ipl = (ipl + 1) % 2
                                    winner = xo.find_winners()

                                    if winner in [1, 2]:
                                        game_info.set_field_at(0, name="🏆 | **Победитель:**", value=f"{sign[winner - 1]} | {anf(players[winner - 1])}")
                                    else:
                                        game_info.set_field_at(0, name="**Сейчас ходит:**", value=f"{sign[ipl]} | {anf(players[ipl])}")
                                    game_info.description = f"**{anf(players[0])}** vs **{anf(players[1])}**\n\n{xo.display()}"
                                    await screen.edit(embed=game_info)

                                    try:
                                        await msg.delete()
                                    except Exception:
                                        pass
                        
                        if winner is not None:
                            if winner == 0:
                                reply = discord.Embed(
                                    title=f"⚖ | {mode_desc} | Ничья",
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
                                    {"$inc": {f"subguilds.$.reputation": -xoaward}}
                                )
                                collection.update_one(
                                    {
                                        "_id": ctx.guild.id,
                                        "subguilds.name": guild_names[winner.id],
                                        f"subguilds.members.{winner.id}": {"$exists": True}
                                    },
                                    {"$inc": {f"subguilds.$.reputation": xoaward}}
                                )

                                reply = discord.Embed(
                                    title=f"🏆 | {mode_desc} | Выиграл {winner}",
                                    color=discord.Color.gold()
                                )
                                reply.add_field(name="**Игрок 1**", value=f"+{xoaward} 🔅 | {anf(winner)}\nГильдия: {guild_names[winner.id]}")
                                reply.add_field(name="**Игрок 2**", value=f"-{xoaward} 🔅 | {anf(looser)}\nГильдия: {guild_names[looser.id]}")
                                await ctx.send(embed=reply)

                                await post_log(ctx.guild, log_channel, reply)
                    
                    xom.pop()  # Clearing game memory

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
        await self.xo_organizer(ctx, string)

    @commands.cooldown(1, 3, commands.BucketType.member)
    @commands.command(aliases=["xo-large", "xol", "xo-big"])
    async def xo_large(self, ctx, *, string):
        await self.xo_organizer(ctx, string, [10, 10, 5])

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