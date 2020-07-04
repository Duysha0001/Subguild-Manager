from discord import Embed, Color
import asyncio
import os, json
from datetime import datetime, timedelta


owner_ids = [301295716066787332]
guild_limit = 30
member_limit = 500
default_avatar_url = "https://cdn.discordapp.com/attachments/664230839399481364/677534213418778660/default_image.png"


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


def rem_duplicates(_list):
    out = []
    for el in _list:
        if el not in out:
            out.append(el)
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


def get_field(Dict, *key_words, default=None):
    if Dict is not None:
        for key in key_words:
            if key in Dict:
                Dict = Dict[key]
            else:
                Dict = None
                break
    if Dict is None:
        return default
    else:
        return Dict


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


def has_any_roles(member, role_array):
    if not has_permissions(member, ["administrator"]):
        owned_role_ids = [r.id for r in member.roles]
        has = False
        for role in role_array:
            if "int" in f"{type(role)}".lower():
                role_id = role
            else:
                role_id = role.id
            if role_id in owned_role_ids:
                has = True
                break
        return has
    else:
        return True


def has_roles(member, role_array):
    has_them = True
    if not has_permissions(member, ["administrator"]):
        owned_role_ids = [r.id for r in member.roles]
        for role in role_array:
            if "int" in f"{type(role)}".lower():
                role_id = role
            else:
                role_id = role.id
            if role_id not in owned_role_ids:
                has_them = False
                break
    return has_them


def has_permissions(member, perm_array):
    if member.id in owner_ids:
        return True
    else:
        perms_owned = dict(member.guild_permissions)
        total_needed = len(perm_array)
        for perm in perm_array:
            if perms_owned[perm]:
                total_needed -= 1
        return total_needed == 0


def has_any_permission(member, perm_array):
    if member.id in owner_ids:
        return True
    else:
        perms_owned = dict(member.guild_permissions)
        out = False
        for perm in perm_array:
            if perms_owned[perm]:
                out = True
                break
        return out


def display_list(array, sep=", ", frame="`"):
    out = ""
    for element in rem_duplicates(array):
        out += f"{frame}{element}{frame}{sep}"
    out = out[:-len(sep)]
    return out if len(out) > 0 else f"{frame}-{frame}"


def is_command(text, prefix, client):
    out = False
    couple = text.split(maxsplit=1)
    if couple != []:
        _1st_word = couple[0]
        if _1st_word.startswith(prefix):
            _1st_word = _1st_word[len(prefix):]
            for cmd in client.commands:
                if cmd.name == _1st_word or _1st_word in cmd.aliases:
                    out = True
                    break
    return out


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


async def search_and_choose(list_of_subguilds, search, message, prefix, client):
    author, channel = message.author, message.channel
    del message
    
    if list_of_subguilds is None:
        results = []
    else:
        results = [g["name"] for g in list_of_subguilds if search.lower() in g["name"].lower()]
    del list_of_subguilds

    if len(results) == 1:
        return results[0]
    elif search in results:
        return search
    elif results == []:
        return None
    else:
        res_board, pos = "", 1
        for r in results:
            res_board += f"`{pos}` {r}\n"
            pos += 1
        bot_emb = Embed(
            title="🔎 Найдено несколько результатов",
            description=f"Напишите номер подходящего Вам результата\n{res_board}"
        )
        bot_emb.set_footer(text=str(author), icon_url=str(author.avatar_url))
        bot_reply = await channel.send(embed=bot_emb)

        wait_for_reply = True
        while wait_for_reply:
            user_reply = await read_message(channel, author, 60, client)
            if user_reply is None:
                wait_for_reply = False
            elif is_command(user_reply.content, prefix, client):
                wait_for_reply = False
                user_reply = None
                await try_delete(bot_reply)
            elif not user_reply.content.isdigit():
                pass
            else:
                num = int(user_reply.content)
                if num <= len(results) and num > 0:
                    wait_for_reply = False
                    await try_delete(bot_reply)
        
        if user_reply is not None:
            return results[num - 1]
        else:
            return 1337


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


class Guild:
    def __init__(self, data):
        self.name = get_field(data, "name")
        self.description = get_field(data, "description")
        self.avatar_url = get_field(data, "avatar_url")
        self.leader_id = get_field(data, "leader_id")
        self.helper_id = get_field(data, "helper_id")
        self.role_id = get_field(data, "role_id")
        self.private = get_field(data, "private")
        self.requests = get_field(data, "requests", default=[])
        self.reputation = get_field(data, "reputation", default=0)
        self.mentions = get_field(data, "mentions", default=0)
        self.members = get_field(data, "members", default=[])
        self.limit = get_field(data, "limit", default=member_limit)

    def member_xp(self, ID):
        if not f"{ID}" in self.members:
            return None
        else:
            return self.members[f"{ID}"]["messages"]
    
    def xp(self):
        out = 0
        for id_key in self.members:
            out += self.members[id_key]["messages"]
        return out
    
    def members_as_pairs(self):
        return [(int(ID), self.members[ID]["messages"]) for ID in self.members]

    def forget_members(self):
        self.members = {}

    def average_xp(self):
        total_xp, total_members = 0, 0
        for id_key in self.members:
            total_xp += self.members[id_key]["messages"]
            total_members += 1
        return round(total_xp / total_members, 1)
    
    def average_rep(self):
        return round(self.reputation / len(self.members), 1)
    
    def average_tags(self):
        return round(self.mentions / len(self.members), 1)

    def all_averages(self):
        total_xp, total_members = 0, 0
        for id_key in self.members:
            total_xp += self.members[id_key]["messages"]
            total_members += 1
        return {
            "xp": round(total_xp / total_members, 1),
            "rep": round(self.reputation / total_members, 1),
            "tags": round(self.mentions / total_members, 1)
        }


class Server:
    def __init__(self, subguilds_data_list):
        self.guilds = subguilds_data_list
    
    def get_guilds(self):
        return [Guild(sg) for sg in self.guilds]
    
    def search_guilds(self, string):
        string = string.lower()
        return [Guild(g) for g in self.guilds if string in g["name"].lower()]
    
    def search_guild(self, string):
        out, string = None, string.lower()
        for g in self.guilds:
            if string in g["name"].lower():
                out = Guild(g)
                break
        return out
    
    def guild_with_name(self, name):
        out = None
        for g in self.guilds:
            if name == g["name"]:
                out = Guild(g)
                break
        return out

    def guild_with_member(self, ID):
        out = None
        for g in self.guilds:
            if f"{ID}" in g["members"]:
                out = Guild(g)
                break
        return out
    
    def xp_pairs(self):
        out = []
        for g in self.guilds:
            guild = Guild(g)
            out.append((guild.name, guild.xp()))
        return out
    
    def reputation_pairs(self):
        return [(g["name"], g["reputation"]) for g in self.guilds]
    
    def mentions_pairs(self):
        return [(g["name"], g["mentions"]) for g in self.guilds]
    
    def rating_pairs(self):
        total_xp, total_rep = 0, 0
        triplets = []
        for guild in self.guilds:
            g = Guild(guild)
            xp = g.xp()
            total_rep += g.reputation
            total_xp += xp
            triplets.append((g.name, g.reputation, xp))
        del g, xp
        k = total_xp / total_rep
        pairs = [(triplet[0], triplet[1] + int(triplet[2] / k)) for triplet in triplets]
        del triplets
        return pairs

    def member_count_pairs(self):
        out = []
        for guild in self.guilds:
            g = Guild(guild)
            out.append((g.name, len(g.members)))
        return out

    def all_member_pairs(self):
        out = []
        for guild in self.guilds:
            for key in get_field(guild, "members", default=[]):
                out.append((int(key), guild["members"][key]["messages"]))
        return out


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


class detect:
    @staticmethod
    def member(guild, search):
        ID = carve_int(search)
        if ID is None:
            ID = 0
        member = guild.get_member(ID)
        if member is None:
            member = guild.get_member_named(search)
        return member
    
    @staticmethod
    def channel(guild, search):
        ID = carve_int(search)
        if ID is None:
            ID = 0
        channel = guild.get_channel(ID)
        if channel is None:
            for c in guild.channels:
                if c.name == search:
                    channel = c
                    break
        return channel
    
    @staticmethod
    def role(guild, search):
        ID = carve_int(search)
        if ID is None:
            ID = 0
        role = guild.get_role(ID)
        if role is None:
            for r in guild.roles:
                if r.name == search:
                    role = r
                    break
        return role
    
    @staticmethod
    def user(search, client):
        ID = carve_int(search)
        user = None
        if ID is not None:
            user = client.get_user(ID)
        return user


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
            _delta = timedelta(seconds=10)
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


# Hey yo eh oh ah!