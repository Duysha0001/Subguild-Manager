owner_ids = [301295716066787332]


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
    perms_owned = dict(member.guild_permissions)
    total_needed = len(perm_array)
    for perm in perm_array:
        if perms_owned[perm]:
            total_needed -= 1
    return total_needed == 0


def has_any_permission(member, perm_array):
    perms_owned = dict(member.guild_permissions)
    out = False
    for perm in perm_array:
        if perms_owned[perm]:
            out = True
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