import dbl
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot
import asyncio

import json, os, datetime

import pymongo
from pymongo import MongoClient

dbl_token = str(os.environ.get("dbl_token"))
app_string = str(os.environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

#------- Variables --------

vote_reward = 1

#------- Functions --------
from functions import get_field

def array(date_time):
    return list(date_time.timetuple())[:-3]

def dt(array):
    return datetime.datetime(*array)

async def post_log(guild, channel_id, log):
    if channel_id is not None:
        channel = guild.get_channel(channel_id)
        if channel is not None:
            await channel.send(embed=log)

class LocalGuildData:
    def __init__(self, folder_name):
        self.folder_name = folder_name
        self.opened_data = None

    def get_bucket(self, guild_id):
        bucket = str(guild_id >> 22)[:-10]
        if bucket == "":
            bucket = "0"
        return bucket

    def open_for(self, guild_id):
        bucket = self.get_bucket(guild_id)
        filename = f"{self.folder_name}_{bucket}.json"
        if self.folder_name in os.listdir("."):
            if filename in os.listdir(f"{self.folder_name}"):
                with open(f"{self.folder_name}/{filename}", "r", encoding="utf8") as fff:
                    self.opened_data = json.load(fff)
            else:
                self.opened_data = {}
        else:
            self.opened_data = {}
    
    def update(self, guild_id, user_id, value):
        g, u = str(guild_id), str(user_id)
        if g not in self.opened_data:
            self.opened_data[g] = {u: value}
        else:
            self.opened_data[g][u] = value

    def save_changes_for(self, guild_id):
        if self.opened_data is not None:
            bucket = self.get_bucket(guild_id)
            filename = f"{self.folder_name}/{self.folder_name}_{bucket}.json"
            if self.folder_name not in os.listdir("."):
                os.mkdir(self.folder_name)
            with open(filename, "w", encoding="utf8") as fff:
                json.dump(self.opened_data, fff)
            self.opened_data = None

class dbl_actions(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.token = dbl_token

    def cog_unload(self):
        self.update_stats.cancel()

    #-------- Tasks --------

    @tasks.loop(minutes=30.0)
    async def update_stats(self):
        try:
            await self.dblpy.post_guild_count()
            # print("Successfully updated stats")
        except Exception as e:
            print(f"Failed to update stats due to exception: {e}")
    
    #--------- Events ---------
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> DBL cog is loaded")
        self.dblpy = dbl.DBLClient(self.client, self.token)
        # print("--> Logged in DBL")
        self.update_stats.start()
    
    #------- Commands -------
    @commands.cooldown(1, 30, commands.BucketType.member)
    @commands.command(aliases=["i-voted", "I-voted", "iv", "claim-vote"])
    async def i_voted(self, ctx):
        pr = ctx.prefix
        now = datetime.datetime.now()
        _12_hours = datetime.timedelta(hours=12)

        memory = LocalGuildData("DBL_votes")
        memory.open_for(ctx.guild.id)
        last_time = get_field(memory.opened_data, str(ctx.guild.id), str(ctx.author.id))
        can_go = True

        if last_time is None:
            pass
        elif now - dt(last_time) < _12_hours:
            can_go = False
            reply = discord.Embed(
                title="🕑 Воут уже засчитан",
                description="Вы уже получили бонус за последний воут, приходите позже :)"
            )
            reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
            await ctx.send(embed=reply)
        
        if can_go:
            try:
                voted = await self.dblpy.get_user_vote(ctx.author.id)
            except Exception as e:
                voted = None
                print(f"Failed to get user vote due to exceptopn: {str(e)[:30]}")
            
            if voted is not None:
                if not voted:
                    reply = discord.Embed(
                        title="📭 Вы ещё не голосовали",
                        description=(
                            "Вы сможете получить подарок, если проголосуете -> **[нажмите чтобы перейти](https://top.gg/bot/677976225876017190/vote)**\n"
                            "Если Вы уже проголосовали, заберите награду через 2-3 минуты"
                        )
                    )
                    reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                    await ctx.send(embed=reply)

                else:
                    collection = db["subguilds"]
                    result = collection.find_one_and_update(
                        {"_id": ctx.guild.id, f"subguilds.members.{ctx.author.id}": {"$exists": True}},
                        {"$inc": {"subguilds.$.reputation": vote_reward}},
                        projection={
                            "_id": True,
                            "log_channel": True,
                            f"subguilds.members.{ctx.author.id}": True,
                            "subguilds.name": True
                        }
                    )
                    if result is None:
                        reply = discord.Embed(
                            title="🔎 Вы не в гильдии",
                            description=(
                                f"Ваш голос засчитан, но Вас нет в гильдии и я не могу начислить {vote_reward} репутации.\n"
                                f"Зайти в гильдию: `{pr}join-guild Название`"
                            )
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)
                    
                    else:
                        reply = discord.Embed(
                            title="💛 Спасибо за воут!",
                            description=f"Вашей гильдии добавлено {vote_reward} очков репутации, но это не последний раз! Приходите через 12 часов :)",
                            color=discord.Color.gold()
                        )
                        reply.set_footer(text=str(ctx.author), icon_url=str(ctx.author.avatar_url))
                        await ctx.send(embed=reply)
                        
                        memory.open_for(ctx.guild.id)
                        memory.update(ctx.guild.id, ctx.author.id, array(now))
                        memory.save_changes_for(ctx.guild.id)

                        g_name = None
                        for sg in result["subguilds"]:
                            if get_field(sg, "members", f"{ctx.author.id}") is not None:
                                g_name = sg["name"]
                                break
                        log = discord.Embed(
                            title="🎁 Подарочная репутация",
                            description=(
                                f"**Пользователь:** {ctx.author}\n"
                                f"**Гильдия:** {g_name}\n"
                                f"**Кол-во:** {vote_reward}"
                            ),
                            color=discord.Color.gold()
                        )
                        lc_id = get_field(result, "log_channel")
                        await post_log(ctx.guild, lc_id, log)

def setup(client):
    client.add_cog(dbl_actions(client))