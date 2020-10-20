from pymongo import MongoClient
from os import environ

#----------------------------+
#        Connecting          |
#----------------------------+
app_string = str(environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

#----------------------------+
#         Constants          |
#----------------------------+
guild_limit = 30
member_limit = 500
default_avatar_url = "https://cdn.discordapp.com/attachments/664230839399481364/677534213418778660/default_image.png"
default_prefix = "."

#----------------------------+
#         Functions          |
#----------------------------+


#----------------------------+
#          Classes           |
#----------------------------+
class Member:
    def __init__(self, _id: int, data: dict={}):
        """data = {xp: 123}"""
        self.id = int(_id)
        self.xp = data.get("messages", 0)
        del data


class Guild:
    def __init__(self, server_id: int, data: dict={}, local_member_limit=member_limit, name: str=None, attrs_projection: dict=None):
        """Initializes Guild instance.
        !!! ONLY SPECIFY [name (str)] and [attrs_projection (dict)] if you want to request it from db !!!"""
        self.server_id = server_id
        # Requesting data in case [name] is specified
        if name is not None:
            if attrs_projection is not None:
                attrs_projection = {f"subguilds.{attr}": value for attr, value in attrs_projection.items()}
                if list(attrs_projection.values())[0]: attrs_projection["member_limit"] = True
            collection = db["subguilds"]
            result = collection.find_one(
                {"_id": self.server_id, "subguilds.name": {"$exists": True}},
                projection=attrs_projection
            )
            del attrs_projection
            if result is not None:
                for g in result.get("subguilds", []):
                    if g.get("name") == name:
                        data = g
                        break
                local_member_limit = result.get("member_limit", member_limit)
            del name, result
        # Wrapping data
        self.__members = data.get("members", {})
        self.__xp = None
        self.requests = data.get("requests", [])
        self.name = data.get("name", "")
        self.description = data.get("description", "Без описания")
        self.avatar_url = data.get("avatar_url", default_avatar_url)
        self.leader_id = data.get("leader_id")
        self.helper_id = data.get("helper_id")
        self.role_id = data.get("role_id")
        self.limit = data.get("limit", local_member_limit)
        self.member_count = len(self.__members)
        self.request_count = len(self.requests)
        self.private = data.get("private", False)
        self.reputation = data.get("reputation", 100)
        self.mentions = data.get("mentions", 0)
        self.superpoints = data.get("superpoints", 0)
        del data
    @property
    def members(self):
        if isinstance(self.__members, dict):
            self.__members = [Member(_id_, d) for _id_, d in self.__members.items()]
        return self.__members
    @property
    def xp(self):
        if self.__xp is None:
            total = 0
            if isinstance(self.__members, dict):
                for d in self.__members.values():
                    total += d.get("messages", 0)
            else:
                for m in self.__members:
                    total += m.xp
            self.__xp = total
        return self.__xp
    
    def get_member(self, member_id: int):
        if isinstance(self.__members, dict):
            member_id = str(member_id)
            for _id_, data in self.__members.items():
                if _id_ == member_id:
                    return Member(_id_, data)
        else:
            for member in self.__members:
                if member.id == member_id:
                    return member

    def join(self, member_id: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$set": {f"subguilds.$.members.{member_id}": {"messages": 0}}}
        )
        collection.update_one(
            {"_id": self.server_id},
            {"$pull": {"subguilds.$[].requests": member_id}},
        )
    
    def kick(self, *member_ids: list):
        if len(member_ids) > 0:
            to_unset = {f"subguilds.$.members.{ID}": "" for ID in member_ids}
            del member_ids
            collection = db["subguilds"]
            collection.update_one(
                {"_id": self.server_id, "subguilds.name": self.name},
                {"$unset": to_unset}
            )

    def request_join(self, member_id: int):
        if self.private:
            collection = db["subguilds"]
            collection.update_one(
                {"_id": self.server_id, "subguilds.name": self.name},
                {"$addToSet": {"subguilds.$.requests": member_id}}
            )

    def accept_requests(self, member_id: int=None):
        if self.request_count > 0:
            collection = db["subguilds"]
            # Deciding what to pull
            if member_id is None:
                to_pull = {"$in": self.requests}
            else:
                to_pull = member_id
            # Pulling
            collection.update_one(
                {"_id": self.server_id},
                {"$pull": {"subguilds.$[].requests": to_pull}},
            )
            del to_pull
            #--------------------------
            # Deciding what to set
            if member_id is None:
                new_data = {f"subguilds.$.members.{ID}": {"messages": 0} for ID in self.requests}
            else:
                new_data = {f"subguilds.$.members.{member_id}": {"messages": 0}}
            # Setting
            collection.update_one(
                {"_id": self.server_id, "subguilds.name": self.name},
                {"$set": new_data}
            )

    def decline_requests(self, member_ids: list=None):
        if self.request_count > 0:
            collection = db["subguilds"]
            # Deciding what to pull
            if member_ids is None:
                to_pull = {"$in": self.requests}
            else:
                to_pull = {"$in": member_ids}
            # Pulling
            collection.update_one(
                {"_id": self.server_id, "subguilds.name": self.name},
                {"$pull": {"subguilds.$.requests": to_pull}},
            )
    # Customizing the guild
    def edit_name(self, new_name: str):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$set": {f"subguilds.$.name": new_name}}
        )
        self.name = new_name
    
    def edit_description(self, new_description: str):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$set": {f"subguilds.$.description": new_description}}
        )
        self.description = new_description
    
    def edit_avatar_url(self, new_url: str):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$set": {f"subguilds.$.avatar_url": new_url}}
        )
        self.avatar_url = new_url
    
    def edit_leader_id(self, new_leader_id: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$set": {f"subguilds.$.leader_id": new_leader_id}}
        )
        self.leader_id = new_leader_id
    
    def edit_helper_id(self, new_helper_id: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$set": {f"subguilds.$.helper_id": new_helper_id}}
        )
        self.helper_id = new_helper_id
    
    def edit_role_id(self, new_role_id: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$set": {f"subguilds.$.role_id": new_role_id}}
        )
        self.role_id = new_role_id
    
    def edit_limit(self, new_limit: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$set": {f"subguilds.$.limit": new_limit}}
        )
        self.limit = new_limit
    
    def edit_privacy(self, new_privacy: bool):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$set": {f"subguilds.$.private": new_privacy}}
        )
        self.private = new_privacy

    def add_reputation(self, amount: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.server_id, "subguilds.name": self.name},
            {"$inc": {f"subguilds.$.reputation": amount}}
        )
        self.reputation += amount


class Server:
    def __init__(self, _id: int, projection=None, extra_query={}, dont_request_bd=False):
        self.no_data_found = False
        self.id = _id
        if not dont_request_bd:
            collection = db["subguilds"]
            result = collection.find_one({"_id": self.id, **extra_query}, projection=None)
            if result is None:
                result = {}
                self.no_data_found = True
        else:
            result = {}
        self.__guilds = result.get("subguilds", [])
        self.guild_count = len(self.__guilds)
        self.master_roles = result.get("master_roles", [])
        self.creator_roles = result.get("creator_roles", [])
        self.ignore_channels = result.get("ignore_chats", [])
        self.log_channel = result.get("log_channel")
        self.mentioner_id = result.get("mentioner_id")
        self.guild_limit = result.get("guild_limit", guild_limit)
        self.member_limit = result.get("member_limit", member_limit)
        self.creator_limit = result.get("creator_limit", self.guild_limit)
        self.auto_join = result.get("auto_join", False)
        self.xp_locked = result.get("xp_locked", False)
        self.block_leave = result.get("block_leave", False)
        self.games_allowed = result.get("games_allowed", False)
        del result
    @property
    def guilds(self):
        if self.guild_count > 0 and isinstance(self.__guilds[0], dict):
            self.__guilds = [Guild(self.id, _d_, self.member_limit) for _d_ in self.__guilds]
        return self.__guilds

    def rating_pairs(self):
        total_xp = 0
        total_rep = 0
        for g in self.guilds:
            total_xp += g.xp
            total_rep += g.reputation
        if total_rep == 0:
            k = total_xp
        else:
            k = total_xp / total_rep
        return [(g.name, g.reputation + int(g.xp / k)) for g in self.guilds]

    def get_all_members(self):
        res = []
        if self.guild_count < 1:
            return []
        elif isinstance(self.__guilds[0], dict):
            for g in self.__guilds:
                g = g.get("members", {})
                for ID, data in g.items():
                    res.append(Member(int(ID), data))
        else:
            for g in self.__guilds:
                g = g.members
                if isinstance(g, dict):
                    for ID, data in g.items():
                        res.append(Member(int(ID), data))
                else:
                    res.extend(g)
        return res

    def names_matching(self, query: str):
        query = query.lower()
        res = []
        if self.guild_count > 0 and isinstance(self.__guilds[0], dict):
            for g in self.__guilds:
                g = g.get("name", "")
                if query in g.lower():
                    res.append(g)
        else:
            for g in self.__guilds:
                g = g.name
                if query in g.lower():
                    res.append(g)
        return res

    def get_guild(self, member_id: int):
        if self.guild_count > 0 and isinstance(self.__guilds[0], dict):
            member_id = str(member_id)
            for g in self.__guilds:
                for _id_ in g.get("members", {}):
                    if _id_ == member_id:
                        return Guild(self.id, g, self.member_limit)
        else:
            for g in self.__guilds:
                if g.get_member(member_id) is not None:
                    return g

    def get_guild_named(self, name: str):
        if self.guild_count > 0 and isinstance(self.__guilds[0], dict):
            for g in self.__guilds:
                if g.get("name") == name:
                    return Guild(self.id, g, self.member_limit)
        else:
            for g in self.__guilds:
                if g.name == name:
                    return g

    def is_in_guild(self, member_id: int):
        """Works exactly like .get_guild(...) but returns True or False"""
        if self.guild_count > 0 and isinstance(self.__guilds[0], dict):
            member_id = str(member_id)
            for g in self.__guilds:
                g = g.get("members", {})
                for _id_ in g:
                    if _id_ == member_id:
                        return True
        else:
            for g in self.__guilds:
                if g.get_member(member_id) is not None:
                    return True
        return False

    def add_xp(self, member_id: int, amount: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id, f"subguilds.members.{member_id}": {"$exists": True}},
            {"$inc": { f"subguilds.$.members.{member_id}.messages": amount}}
        )

    def add_auto_xp(self, member_id: int):
        if self.guild_count < 1:
            pass
        else:
            g_found = False; lever = False
            XP = -1; M = -1
            if isinstance(self.__guilds[0], dict):
                member_id = str(member_id)
                for g in self.__guilds:
                    g = g.get("members", {}).items()
                    total_xp = 0; m_count = 0
                    for _id_, _xp_ in g:
                        m_count += 1
                        total_xp += _xp_.get("messages", 0)
                        if not g_found and _id_ == member_id:
                            g_found = True
                            lever = True
                    if lever:
                        XPi = total_xp; Mi = m_count
                        lever = False
                    if total_xp > XP:
                        XP = total_xp; M = m_count
            else:
                for g in self.__guilds:
                    m_count = g.member_count
                    g = g.__members
                    total_xp = 0
                    if isinstance(g, dict):
                        for _id_, _xp_ in g:
                            total_xp += _xp_.get("messages", 0)
                            if not g_found and int(_id_) == member_id:
                                g_found = True
                                lever = True
                    else:
                        for m in g:
                            total_xp += m.xp
                            if not g_found and m.id == member_id:
                                g_found = True
                                lever = True
                    if lever:
                        XPi = total_xp; Mi = m_count
                        lever = False
                    if total_xp > XP:
                        XP = total_xp; M = m_count
            if g_found:
                income = round(10 * (((M+10) / (Mi+10))**(1/4) * ((XP+10) / (XPi+10))**(1/2)))
                collection = db["subguilds"]
                collection.update_one(
                    {"_id": self.id,
                    f"subguilds.members.{member_id}": {"$exists": True}},
                    {"$inc": {f"subguilds.$.members.{member_id}.messages": income}}
                )

    def add_mentions(self, who_mentioned: int, member_ids: list):
        collection = db["subguilds"]

        proj = {f"subguilds.members.{ID}": True for ID in member_ids}
        proj["subguilds.name"] = True

        result = collection.find_one(
            {"_id": self.id, "mentioner_id": who_mentioned},
            projection=proj
        )
        del proj
        
        if result is not None:
            for sg in result.get("subguilds", []):
                name = sg.get("name")
                total_mentioned = len(sg.get("members", {}))
                del sg
                if total_mentioned > 0:
                    collection.update_one(
                        {"_id": self.id, "subguilds.name": name},
                        {"$inc": {"subguilds.$.mentions": total_mentioned}}
                    )

    def add_reputation(self, name: str, amount: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id, "subguilds.name": name},
            {"$inc": {"subguilds.$.reputation": amount}}
        )

    def set_reputation(self, name: str, amount: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id, "subguilds.name": name},
            {"$set": {"subguilds.$.reputation": amount}}
        )

    def reset_xp(self, start_value: int=0):
        if self.guild_count < 1:
            return
        collection = db["subguilds"]
        if isinstance(self.__guilds[0], dict):
            for g in self.__guilds:
                zero_mms = {f"subguilds.$.members.{ID}": {"messages": start_value} for ID in g.get("members", {})}
                if len(zero_mms) > 0:
                    collection.update_one(
                        {"_id": self.id, "subguilds.name": g.get("name")},
                        {"$set": zero_mms}
                    )
        else:
            for g in self.__guilds:
                name = g.name
                g = g.__members
                if isinstance(g, dict):
                    zero_mms = {f"subguilds.$.members.{ID}": {"messages": start_value} for ID in g}
                else:
                    zero_mms = {f"subguilds.$.members.{m.id}": {"messages": start_value} for m in g}
                if len(zero_mms) > 0:
                    collection.update_one(
                        {"_id": self.id, "subguilds.name": name},
                        {"$set": zero_mms}
                    )

    def reset_reputation(self, start_value: int=100):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"subguilds.$[].reputation": start_value}}
        )
    
    def reset_mentions(self, start_value: int=0):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"subguilds.$[].mentions": start_value}}
        )

    def smart_reset(self):
        """Returns [(Name, Superpoints), ...]"""
        if self.guild_count < 1:
            return
        triplets = [] # (Name, XP, ZeroData)
        if isinstance(self.__guilds[0], dict):
            for g in self.__guilds:
                if g.get("name") is not None:
                    zero_data = {}
                    total_xp = 0
                    for _id_, data in g.get("members", {}).items():
                        total_xp += data.get("messages", 0)
                        zero_data[f"subguilds.$.members.{_id_}"] = {"messages": 0}
                    triplets.append((g["name"], total_xp, zero_data))
        else:
            for g in self.__guilds:
                if g.name is not None:
                    zero_data = {}
                    total_xp = 0
                    for m in g.members:
                        total_xp += m.xp
                        zero_data[f"subguilds.$.members.{m.id}"] = {"messages": 0}
                    triplets.append((g["name"], total_xp, zero_data))
        triplets.sort(key=lambda t: t[1])
        collection = db["subguilds"]
        for i, t in enumerate(triplets):
            collection.update_one(
                {"_id": self.id, "subguilds.name": t[0]},
                {
                    "$set": t[2],
                    "$inc": {"subguilds.$.superpoints": i + 1}
                }
            )
        return [(t[0], i + 1) for i, t in enumerate(triplets)]

    def create_guild(self, name: str, owner_id: int):
        gdata = {"name": name, "leader_id": owner_id}
        if not self.is_in_guild(owner_id):
            gdata["members"] = {f"{owner_id}": {"messages": 0}}
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$addToSet": {"subguilds": gdata}},
            upsert=True
        )

    def delete_guild(self, name: str):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$pull": {"subguilds": {"name": name}}}
        )
    
    def delete_all_guilds(self):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"subguilds": ""}}
        )
    # Settings
    def add_master_role(self, role_id: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$addToSet": {"master_roles": role_id}},
            upsert=True
        )
    
    def remove_master_roles(self, *role_ids: list):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$pull": {"master_roles": {"$in": role_ids}}}
        )
    
    def add_creator_role(self, role_id: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$addToSet": {"creator_roles": role_id}},
            upsert=True
        )
    
    def remove_creator_roles(self, *role_ids: list):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$pull": {"creator_roles": {"$in": role_ids}}}
        )

    def set_ignore_channels(self, channel_ids: list):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"ignore_chats": channel_ids}},
            upsert=True
        )

    def set_log_channel(self, channel_id: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"log_channel": channel_id}},
            upsert=True
        )

    def set_mentioner_id(self, user_id: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"mentioner_id": user_id}},
            upsert=True
        )
    
    def set_guild_limit(self, new_guild_limit: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"guild_limit": new_guild_limit}},
            upsert=True
        )
    
    def set_member_limit(self, new_member_limit: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"member_limit": new_member_limit}},
            upsert=True
        )
    
    def set_creator_limit(self, new_creator_limit: int):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"creator_limit": new_creator_limit}},
            upsert=True
        )

    def set_auto_join(self, on_off: bool):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"auto_join": on_off}},
            upsert=True
        )

    def set_xp_lock(self, on_off: bool):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"xp_locked": on_off}},
            upsert=True
        )
    
    def set_block_leave(self, on_off: bool):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"block_leave": on_off}},
            upsert=True
        )

    def allow_games(self, on_off: bool):
        collection = db["subguilds"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"games_allowed": on_off}},
            upsert=True
        )
    # Self destruct
    def delete(self):
        collection = db["subguilds"]
        collection.delete_one({"_id": self.id})


class ResponseConfig:
    def __init__(self, server_id: int, projection=None, dont_request_bd=False):
        self.id = server_id
        if not dont_request_bd:
            collection = db["cmd_channels"]
            result = collection.find_one({"_id": self.id}, projection=projection)
            if result is None: result = {}
        else:
            result = {}
        del server_id, projection
        self.prefix = result.get("prefix", default_prefix)
        self.cmd_channels = result.get("channels", [])
        del result
    
    def set_cmd_channels(self, channel_ids: list):
        collection = db["cmd_channels"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"channels": channel_ids}},
            upsert=True
        )

    def add_cmd_channels(self, channel_ids: list):
        collection = db["cmd_channels"]
        collection.update_one(
            {"_id": self.id},
            {"$push": {"channels": {"$each": channel_ids}}},
            upsert=True
        )
    
    def remove_cmd_channels(self, channel_ids: list):
        collection = db["cmd_channels"]
        collection.update_one(
            {"_id": self.id},
            {"$pull": {"channels": {"$in": channel_ids}}}
        )
    
    def remove_all_cmd_channels(self):
        collection = db["cmd_channels"]
        collection.update_one(
            {"_id": self.id},
            {"$unset": {"channels": ""}}
        )

    def set_prefix(self, new_prefix: str):
        new_prefix = new_prefix.split(maxsplit=1)[0]
        collection = db["cmd_channels"]
        collection.update_one(
            {"_id": self.id},
            {"$set": {"prefix": new_prefix}},
            upsert=True
        )
    # Self destruct
    def delete(self):
        collection = db["cmd_channels"]
        collection.delete_one({"_id": self.id})


#----------------------------+
#          Bro hi            |
#----------------------------+