import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot
import asyncio
import json, os, datetime

import pymongo
from pymongo import MongoClient

app_string = str(os.environ.get("cluster_app_string"))
cluster = MongoClient(app_string)
db = cluster["guild_data"]

from functions import owner_ids

class ghost_cog(commands.Cog):
    def __init__(self, client):
        self.client = client
    
    #--------- Events ---------
    @commands.Cog.listener()
    async def on_ready(self):
        print(">> Ghost cog is loaded")
    
    #------- Commands -------
    @commands.cooldown(1, 1, commands.BucketType.member)
    @commands.command()
    async def call(self, ctx):
        if ctx.author.id in owner_ids:
            # INSERT_START

            await ctx.send("Test 2")
# INSERT_END

def setup(client):
    client.add_cog(ghost_cog(client))