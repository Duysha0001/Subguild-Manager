from discord import Embed, Color
import asyncio
import os, json
from datetime import datetime, timedelta


#----------------------------+
#         Constants          |
#----------------------------+
owner_ids = [
    301295716066787332,
    462517800817131555
]
cool_servers = [
    422784396425297930,
    575770784673300491
]
guild_limit = 30
member_limit = 500
default_avatar_url = "https://cdn.discordapp.com/attachments/664230839399481364/677534213418778660/default_image.png"

perms_tr = {
    "administrator": "Администратор",
    "manage_roles": "Управлять ролями",
    "guild_master": "Мастер гильдий",
    "guild_creator": "Создатель гильдий",
    "guild_leader": "Глава этой гильдии",
    "guild_helper": "Помощник в этой гильдии"
}


#----------------------------+
#         Functions          |
#----------------------------+
def display_perms(missing_perms):
    out = ""
    for perm in missing_perms:
        out += f"> {perms_tr.get(perm, perm)}\n"
    return out


def abr(num):
    names = ["K", "M", "B", "T"]
    p = 0
    while num // 1000 > 0 and p < len(names):
        mant = round(num / 1000, 1)
        num //= 1000
        p += 1
    if p > 0:
        return f"{mant} {names[p - 1]}"
    else:
        return str(num)


def anf(user):
    fsymbs = ">`*_~|"
    out = ""
    for s in str(user):
        if s in fsymbs:
            out += "\\"
        out += s
    return out


def vis_num(number, sep=" ", step=3):
    number = str(number)
    length = len(number)
    out = ""
    if length < step:
        out = number
    else:
        for i in range(length, 0, -step):
            out = sep + number[i - step:i] + out
        out = out.lstrip(sep)
    return out if length % step == 0 or length < step else f"{number[:i]}{sep}{out}"


def find_alias(dict_of_aliases, search):
    out, search = None, search.lower()
    for key in dict_of_aliases:
        aliases = dict_of_aliases[key]
        aliases.append(key)
        for al in aliases:
            if al.startswith(search):
                out = key
                break
        if out is not None:
            break
    return out


def is_command(text, prefix, client):
    cmds = client.commands
    del client
    _1st_word = text.split(maxsplit=1)
    if len(_1st_word) < 1:
        return False
    _1st_word = _1st_word[0]
    if _1st_word.startswith(prefix):
        _1st_word = _1st_word[len(prefix):]
        for cmd in cmds:
            if cmd.name == _1st_word or _1st_word in cmd.aliases:
                return True
    return False


async def give_join_role(member, role_id):
    if role_id is not None:
        role = member.guild.get_role(role_id)
        if role is not None and role not in member.roles:
            try:
                await member.add_roles(role)
            except:
                pass


async def remove_join_role(member, role_id):
    if role_id is not None:
        role = member.guild.get_role(role_id)
        if role in member.roles:
            try:
                await member.remove_roles(role)
            except:
                pass


async def try_delete(obj):
    try:
        await obj.delete()
    except Exception:
        pass


async def read_message(channel, user, t_out, client):
    try:
        msg = await client.wait_for("message", check=lambda message: user.id==message.author.id and channel.id==message.channel.id, timeout=t_out)
    except asyncio.TimeoutError:
        reply = Embed(
            title="🕑 Вы слишком долго не писали",
            description=f"Таймаут: {t_out} сек.",
            color=3867684
        )
        await channel.send(content=user.mention, embed=reply)
        return None
    else:
        return msg


async def ask_to_choose(list_of_options, channel, author, client, prefix):
    total_options = len(list_of_options)
    if total_options < 1:
        return None
    elif total_options < 2:
        return list_of_options[0]
    else:
        res_board = ""
        for i, option in enumerate(list_of_options):
            res_board += f"`{i + 1}` {option}\n"
        bot_emb = Embed(
            title="🔎 | Найдено несколько результатов",
            description=f"Напишите номер подходящего Вам результата\n{res_board}"
        )
        bot_emb.set_footer(text=str(author), icon_url=str(author.avatar_url))
        bot_reply = await channel.send(embed=bot_emb)

        def check(msg):
            if msg.author.id != author.id or msg.channel.id != channel.id:
                return False
            text = msg.content
            del msg
            if text.isdigit() and 0 < int(text) <= total_options:
                return True
            return is_command(text, prefix, client)
        
        try:
            user_reply = await client.wait_for("message", check=check, timeout=60)
        except:
            reply = Embed(color=Color.blurple())
            reply.title = "🕑 | Превышено время ожидания"
            reply.description = f"{anf(author)}, Вы слишком долго не отвечали"
            await channel.send(embed=reply)
            return EmergencyExit()
        else:
            text = user_reply.content
            del user_reply
            if not text.isdigit():
                # Means it only can be a command
                await try_delete(bot_reply)
                return EmergencyExit()
            # All other cases are what we need
            return list_of_options[int(text) - 1]


async def trigger_reaction(message, emojis, user_to_check, timeout, client):

    def check(reaction, user):
        return (
            message.id == reaction.message.id and
            user_to_check.id == user.id and
            reaction.emoji in emojis
        )
    
    try:
        reaction, user = await client.wait_for("reaction_add", check=check, timeout=timeout)
    
    except asyncio.TimeoutError:
        return None
    
    else:
        return (reaction, user)


#----------------------------+
#        Exceptions          |
#----------------------------+
class EmergencyExit(Exception):
    pass


#----------------------------+
#          Classes           |
#----------------------------+
class Leaderboard:
    def __init__(self, pair_array, interval=10):
        self.pairs = pair_array
        self.interval = interval
        self.length = len(self.pairs)
        self.total_pages = (self.length - 1) // self.interval + 1
    
    def sort_values(self, reverse=True):
        self.pairs.sort(key=lambda pair: pair[1], reverse=reverse)

    def get_page(self, page):
        lower_bound = (page - 1) * self.interval
        upper_bound = min(lower_bound + self.interval, self.length)
        return (self.pairs[lower_bound:upper_bound], lower_bound)
    
    def pair_index(self, _1st_element):
        out = None
        for i in range(self.length):
            if self.pairs[i][0] == _1st_element:
                out = i
                break
        return out


class XP_gateway:
    def __init__(self, path):
        self.path = path
    
    def set_path(self):
        current_dir = "."
        for folder in self.path.split("/"):
            listdir = os.listdir(current_dir)
            if folder not in listdir:
                os.mkdir(self.path)
                break
            else:
                current_dir += "/" + folder
    
    def bucket_name(self, user_id):
        bucket = str(user_id >> 22)[:-10]
        if bucket == "":
            bucket = "0"
        return bucket

    def process(self, user_id):
        now = datetime.utcnow()
        bname = self.bucket_name(user_id)
        # In case the file dosen't exist:
        if f"{bname}.json" not in os.listdir(self.path):
            open(f"{self.path}/{bname}.json", "w").write("{}")
        
        # Loading data
        with open(f"{self.path}/{bname}.json", "r") as _file:
            data = json.load(_file)
        
        # Checking if the cooldown is passed
        time_array = data.get(str(user_id))
        passed = True
        if time_array is not None:
            last_time = datetime(*time_array)
            _delta = timedelta(seconds=30)     # XP earcn cooldown
            if now - last_time < _delta:
                passed = False
        
        if passed:
            data[str(user_id)] = list(now.timetuple())[:6]
            with open(f"{self.path}/{bname}.json", "w") as _file:
                json.dump(data, _file)
            return True
        else:
            return False
        del data


class CustomColors:
    def rgb_to_hex(self, *rgb):
        r, g, b = rgb
        return hex(r)[-2:] + hex(g)[-2:] + hex(b)[-2:]

    def rgb_to_dec(self, *rgb):
        return int(self.rgb_to_hex(*rgb), 16)

    def __init__(self):
        self.gold = int("ffce4b", 16)
        self.coral = self.rgb_to_dec(255, 101, 113)
        self.caramel = self.rgb_to_dec(255, 147, 94)
        self.paper = self.rgb_to_dec(163, 139, 101)
        self.sky = self.rgb_to_dec(131, 171, 198)
        self.pancake = self.rgb_to_dec(211, 150, 65)

# o_O