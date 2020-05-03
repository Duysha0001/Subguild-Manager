owner_ids = [301295716066787332]
guild_limit = 30
member_limit = 500
default_avatar_url = "https://cdn.discordapp.com/attachments/664230839399481364/677534213418778660/default_image.png"


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


def has_roles(member, role_array):
    has_them = True
    if not has_permissions(member, ["administrator"]):
        for role in role_array:
            if "int" in f"{type(role)}".lower():
                role = member.guild.get_role(role)
            if not role in member.roles:
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


def is_command(word, client):
    out = False
    for cmd in client.commands:
        group = cmd.aliases
        group.append(cmd.name)
        if word in group:
            out = True
            break
    return out


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


class Server:
    def __init__(self, data_list):
        self.guilds = data_list
    
    def get_guilds(self):
        return [Guild(sg) for sg in self.guilds]
    
    def guild_with_name(self, name):
        out = None
        for g in self.guilds:
            if name == g["name"]:
                out = Guild(g)
                break
        return out

    def search_guilds(self, string):
        string = string.lower()
        return [Guild(g) for g in self.guilds if string in g["name"].lower()]
    
    def guild_with_member(self, ID):
        out = None
        for g in self.guilds:
            if f"{ID}" in g["members"]:
                out = Guild(g)
                break
        return out
    
    def search_guild(self, string):
        out, string = None, string.lower()
        for g in self.guilds:
            if string in g["name"].lower():
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