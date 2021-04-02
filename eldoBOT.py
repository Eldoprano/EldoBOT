print("starting...")
import hashlib
import os
from time import sleep
import time
import discord
from discord import NotFound
from dotenv import load_dotenv
import requests
from requests import Session
from bs4 import BeautifulSoup
import json
from PIL import Image
from io import BytesIO
import io
import random
import re
import mysql.connector
import emoji
import unicodedata
from unidecode import unidecode
from collections import Counter
import operator
import pickle
import cv2
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from datetime import datetime
import imagehash # Image fingerprinting
import urllib.parse # Convert URL
import asyncio
import homoglyphs as hg # Kills those nasty homoglyphs
#import sched # For asynchrone repetitive Tasks
print("Import completed!")

# TraceMOE Limits:
#   10 searches per minute
#   150 searches per day
#   https://soruly.github.io/trace.moe/#/
#
# SauceNAO Limits:
#   10 searches per minute
#   200 searches per day

# More constats to satisfy SonarCloud
ANON_DEFAULT_PFP="https://media.discordapp.net/attachments/647898356311654447/706938410098622555/unknown.png"
PICKLE_OF_CONFIGURATIONS="configurations.pkl"
PICKLE_OF_ANONS="anon_list.pkl"
COLOR_GREEN=1425173
COLOR_BLUE=2190302
COLOR_YELLOW=16776960
COLOR_RED=15597568
STAFF_ROLE=0

TIME_A1=0
MUTE_ROL=0

# TraceMoe variables
tracemoe_session = Session()
tracemoe_session.headers = {
    "Content-Type": "application/json"
}

# Get configurations
configurations = pickle.load(open(PICKLE_OF_CONFIGURATIONS, "rb" ))
activator = "e!"

# What is that???!!!!!
# The informJSON
#informJSON = pickle.load(open("informJSON.pkl", "rb" ))

# Get some secrets from the magic Pickle
keys = pickle.load(open("keys.pkl", "rb" ))

 ## Connect to Database
mydb = mysql.connector.connect(
     host=keys["Database"]["host"],
     user=keys["Database"]["user"],
     passwd=keys["Database"]["passwd"],
     database=keys["Database"]["database"])
mycursor = mydb.cursor()

Discord_TOKEN = keys["Discord_TOKEN"]
sauceNAO_TOKEN = keys["sauceNAO_TOKEN"]
DB_NAME = keys["Database"]["database"]

LOG_CHANNEL = 708648213774598164

# Statistics Token
try: A = pickle.load(open("stats.pkl", "rb" ))
except Exception as e: 
    print(e)
    stats = {}

# Intents! The new thingy of Discord
intents = discord.Intents.default()
intents.members = True

# Initialize client
client = discord.Client(intents=intents)
try:
    anon_list = pickle.load(open(PICKLE_OF_ANONS, "rb" ))
    print("Pickle file loaded")
except Exception as e:
    print(e)
    print("Error, couldn't load Pickle File")
    anon_list = {}

channel_logs=0
report_channel=0

messages_to_react = []
status_messages_to_react = []
spam_detector_list = {}
homoglyphs = hg.Homoglyphs(
    languages={'en'},
    strategy=hg.STRATEGY_LOAD,
    ascii_strategy=hg.STRATEGY_REMOVE,
)

# Load configurations from DB
mySQL_query = "SELECT g.GUILD_ID, TAG FROM "+DB_NAME+".FORBIDDEN_TAGS f inner join  " + \
    DB_NAME+".GUILD g on f.GUILD_ID=g.id;"
mycursor.execute(mySQL_query)
forbidden_tags = mycursor.fetchall()


print("initial configurations completed")
# Notes:
# Hey!! Add https://soruly.github.io/trace.moe/#/ to your bot! It has an easy to use API, and nice limits
# It also gives you information when the saucenao doesn't.

# Don't allow mentions of any type
##allowed_mentions_NONE = discord.AllowedMentions(everyone=False, users=False, roles=False)

async def get_video_frame(attachment):
    with open("temp.mp4", 'wb') as video_file:
        video_file = await attachment.save(video_file)
    cam = cv2.VideoCapture("temp.mp4")
    ret,image_to_search = cam.read()
    #print(type(image_to_search),type(ret),type(cam),type(video_file))
    return image_to_search


@client.event
async def on_guild_join(guild):
    global STAFF_ROLE
    msg_to_send = "Fuimos invitados a un nuevo servidor!! Nombre:", guild.name
    print(msg_to_send)
    await channel_logs.send(msg_to_send)
    if not guild.id in configurations["guilds"]:
        configurations["guilds"][guild.id] = {"general":{},"commands":{"name_channel_set":False,"name_channel":[],"name_ignore_message":""},"others":{}}
        with open(PICKLE_OF_CONFIGURATIONS, 'wb') as pickle_file:
            pickle.dump(configurations,pickle_file)
    STAFF_ROLE = guild.get_role(683787780236902450)
        
    


@client.event
async def on_ready():
    global channel_logs
    global report_channel 
    print(f'{client.user.name} has connected to Discord!')
    # Get channel for logs:
    channel_logs = await client.fetch_channel(LOG_CHANNEL)
    report_channel = await client.fetch_channel(723973823833047111)
    anis_guild = await client.fetch_guild(624079272155414528)
    MUTE_ROL = anis_guild.get_role(627633919939837978)

# Desactivado por mientras...
"""
@client.event
async def on_raw_reaction_add(payload):
    if(str(payload.emoji) == "🔍" or str(payload.emoji) == "🔎"):
        channel = client.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)
        await new_find_name(msg)
"""

temp_busquedas = True
@client.event
async def on_message(msg):
    global channel_logs

    # Ignore messages comming from a bot
    if msg.author.bot:
        # If the bot is nHitomi, then look for forbidden tags  
        if msg.author.id==515386276543725568:
            collected_forbidden_tags = ""
            forbidden_tag_list = [tag[1] for tag in forbidden_tags if tag[0]==str(msg.guild.id)]
            for embed in msg.embeds:
                for field in embed.fields:
                    if field.name.find("Tag")!=-1:
                        for tag in forbidden_tag_list:
                            if field.value.find(tag)!=-1:
                                collected_forbidden_tags += tag + ", "
            if collected_forbidden_tags!="":
                content = "La respuesta del bot fué eliminada porque detectamos el/los siguientes tags:\n`"+collected_forbidden_tags[:-2]+"`"
                await msg.channel.send(content=content, delete_after=10)
                await msg.delete()
        return

    async def command_config():
        if msg.author.permissions_in(msg.channel).manage_channels:
            if msg.content.find("e!conf name ignore_message ")==0:
                name_ignore_message = msg.content.replace("e!conf name ignore_message ","")
                configurations["guilds"][msg.guild.id]["commands"]["name_ignore_message"] = name_ignore_message
                with open(PICKLE_OF_CONFIGURATIONS, 'wb') as pickle_file:
                    pickle.dump(configurations,pickle_file)
                await msg.channel.send(content="Mensaje cambiado correctamente",delete_after=3)
        else:
            await msg.channel.send(content="No tienes permisos suficientes para hacer esto",delete_after=3)

    async def command_config_permName():
        if msg.author.permissions_in(msg.channel).manage_channels:
            configurations["guilds"][msg.guild.id]["commands"]["name_channel_set"] = True
            configurations["guilds"][msg.guild.id]["commands"]["name_channel"].append(msg.channel.id)
            with open(PICKLE_OF_CONFIGURATIONS, 'wb') as pickle_file:
                pickle.dump(configurations,pickle_file)
            await msg.channel.send(content="Ahora se podrá usar el comando **name** en este canal",delete_after=3)
        else:
            await msg.channel.send(content="No tienes permisos suficientes para hacer esto",delete_after=3)

    async def command_config_bloqName():
        if msg.author.permissions_in(msg.channel).manage_channels:
            if msg.channel.id in configurations["guilds"][msg.guild.id]["commands"]["name_channel"]:
                del(configurations["guilds"][msg.guild.id]["commands"]["name_channel"][msg.channel.id])
                with open(PICKLE_OF_CONFIGURATIONS, 'wb') as pickle_file:
                    pickle.dump(configurations,pickle_file)
            await msg.channel.send(content="Ya no se podrá usar el comando **name** en este canal",delete_after=3)
        else:
            await msg.channel.send(content="No tienes permisos suficientes para hacer esto",delete_after=3)



    async def command_guilds():
        msg_to_say = ""
        for guild in client.guilds:
            msg_to_say+=guild.name + "\n"
        await msg.channel.send(msg_to_say)

    def statsAdd(command):
        if(msg.guild.id==646799198167105539):
            return
        date_today = datetime.today().strftime("%d/%m/%Y")

        if not date_today in stats:
            stats[date_today]={}
        if not command in stats[date_today]:
            stats[date_today][command]=0
        stats[date_today][command]+=1

        with open("stats.pkl", 'wb') as pickle_file:
            pickle.dump(stats,pickle_file)

    async def send_report():
        global report_channel
        tmp_channel = msg.channel
        tmp_message = msg.content+"\nEnviado por "+msg.author.display_name
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except discord.NotFound:
            return

        await report_channel.send(content=tmp_message)
        await tmp_channel.send(content="✅ Reporte enviado al Staff", delete_after=7)

    async def command_spoiler():
        if len(msg.attachments)>0:
            tmp_list_images=[]
            statsAdd("spoiler")
            for attachment in msg.attachments:
                tmp_img_bytes = await attachment.read()
                tmp_img_filename = attachment.filename
                tmp_img_bytes = BytesIO(tmp_img_bytes)
                tmp_img = discord.File(tmp_img_bytes, spoiler=True, filename=tmp_img_filename)
                tmp_list_images.append(tmp_img)

            pfp_to_imitate = await msg.author.avatar_url.read()
            # Create Webhook
            webhook_discord = await msg.channel.create_webhook(name=msg.author.display_name, avatar=pfp_to_imitate, reason="EldoBOT: Temp-webhook")
            # Send message
            await webhook_discord.send(content=msg.content, files = tmp_list_images, username = msg.author.display_name)#, allowed_mentions = allowed_mentions_NONE)
            print("Spoiler printed!")
            # Delete webhook
            await webhook_discord.delete()
            await msg.delete()


    async def command_ping():
        await msg.channel.send("pong")

    async def command_emoji_stats():

        async def searchAll(guildToSearch):
            print("Looking for stats data...")
            mySQL_call =  ("SELECT e.EMOJI_ID ")
            mySQL_call += ("FROM "+DB_NAME+".EMOJI e ")
            mySQL_call += ("INNER JOIN ("+DB_NAME+".EMOJI_SENT s INNER JOIN "+DB_NAME+".GUILD g ON s.GUILD_ID=g.ID) ON s.EMOJI_ID=e.ID ")
            mySQL_call += ("WHERE g.GUILD_ID = " + str(guildToSearch) + ";") 


            mycursor.execute(mySQL_call)
            tmp_list_of_emojis = mycursor.fetchall()
            list_of_emojis=[]
            for element in tmp_list_of_emojis:
                list_of_emojis.append(element[0])
            dic_with_repetitions = Counter(list_of_emojis)
            mensaje_a_mostrar = "Aquí una lista (Función en construcción):\n"

            # Sort Dictionary and save in Tuples
            sorted_list_emojis = sorted(dic_with_repetitions.items(), key=operator.itemgetter(1), reverse=True)
            for emoji_id, times_repeated in sorted_list_emojis:
                # Normie Emoticons😂 <- Puajj
                if len(emoji_id) < 18:
                    #print(mensaje_a_mostrar)
                    if(len(mensaje_a_mostrar)>=1800):
                        await msg.channel.send(mensaje_a_mostrar)
                        mensaje_a_mostrar = ""
                    mensaje_a_mostrar += chr(int(emoji_id)) + " -> " + str(times_repeated) + " | "

                # Discord Emotes :doge: <- Nice :3
                else:
                    emote = client.get_emoji(int(emoji_id))
                    if(emote!=None):
                        mensaje_a_mostrar += "<:" + emote.name + ":" + str(emote.id) + "> -> " + str(times_repeated) + " | "
            await msg.channel.send(mensaje_a_mostrar)

        if msg.content == ("e!emoji_stats yo"):
            user_to_search = msg.author.id
        elif msg.content.find("e!emoji_stats id: ")==0:
            user_to_search = int(msg.content.replace("e!emoji_stats id: ",""))
        elif len(msg.raw_mentions)>0:
            user_to_search = msg.raw_mentions[0]
        else:
            guildToSearch = msg.guild.id
            searchAll(guildToSearch)
            return

        mySQL_call =  ("SELECT e.EMOJI_ID ")
        mySQL_call += ("FROM "+DB_NAME+".EMOJI e ")
        mySQL_call += ("INNER JOIN ("+DB_NAME+".EMOJI_SENT s INNER JOIN "+DB_NAME+".USER u ON s.USER_ID=u.ID) ON s.EMOJI_ID=e.ID ")
        mySQL_call += ("WHERE u.USER_ID = %s;")
        mycursor.execute(mySQL_call, (str(user_to_search),))
        tmp_list_of_emojis = mycursor.fetchall()

        list_of_emojis=[]
        for element in tmp_list_of_emojis:
            list_of_emojis.append(element[0])
        dic_with_repetitions = Counter(list_of_emojis)
        mensaje_a_mostrar = "Aquí una lista (Función en construcción):\n"

        # Sort Dictionary and save in Tuples
        sorted_list_emojis = sorted(dic_with_repetitions.items(), key=operator.itemgetter(1), reverse=True)
        for emoji_id, times_repeated in sorted_list_emojis:
            # Normie Emoticons😂 <- Puajj
            if len(emoji_id) < 18:
                if(len(mensaje_a_mostrar)>=1950):
                    await msg.channel.send(mensaje_a_mostrar)
                    mensaje_a_mostrar = ""
                mensaje_a_mostrar += chr(int(emoji_id)) + " -> " + str(times_repeated) + " | "

            # Discord Emotes :doge: <- Nice :3
            else:
                emote = client.get_emoji(int(emoji_id))
                if(emote!=None):
                    mensaje_a_mostrar += "<:" + emote.name + ":" + str(emote.id) + "> -> " + str(times_repeated) + " | "
        await msg.channel.send(mensaje_a_mostrar)

    async def command_boost_list():
        list_of_boost_users = msg.guild.premium_subscribers
        msg_to_send = ""
        if len(list_of_boost_users) == 0:
            msg_to_send = "No se encontraron usuarios boosteando este servidor"
        for user in list_of_boost_users:
            msg_to_send += "- " + str(user) + "\n"
        await msg.channel.send(msg_to_send)

    async def replace_user_text(text="", replaced="",times=0):
        msg_to_say = msg.content
        tmp_channel = msg.channel
        tmp_author = msg.author.display_name
        pfp_to_imitate = await msg.author.avatar_url.read()

        if len(msg.attachments)>0:
            tmp_list_images=[]
            for attachment in msg.attachments:
                tmp_img_bytes = await attachment.read()
                tmp_img_filename = attachment.filename
                tmp_img_bytes = BytesIO(tmp_img_bytes)
                tmp_img = discord.File(tmp_img_bytes, filename=tmp_img_filename)
                tmp_list_images.append(tmp_img)

        await msg.delete()
    
        reemplazador = re.compile(re.escape(text), re.IGNORECASE)
        msg_to_say = reemplazador.sub(replaced, msg_to_say, times)

        webhook_discord = await tmp_channel.create_webhook(name=tmp_author, avatar=pfp_to_imitate, reason="EldoBOT: Temp-webhook")
        if len(msg.attachments)>0:
            await webhook_discord.send(content = msg_to_say, files = tmp_list_images, username = tmp_author)#, allowed_mentions = allowed_mentions_NONE)
        else:
            await webhook_discord.send(content = msg_to_say, username = tmp_author)#, allowed_mentions = allowed_mentions_NONE)
        # Delete webhook
        await webhook_discord.delete()


    async def command_bot():
        await replace_user_text("e!bot ","",1)


    async def command_anon_reset():
        tmp_user_id = msg.author.id
        if tmp_user_id in anon_list:
            del anon_list[tmp_user_id]
        await msg.channel.send(content="Tu perfil anónimo fué reseteado correctamente",delete_after=2.5)
        await msg.delete()
        with open(PICKLE_OF_ANONS, 'wb') as pickle_file:
            pickle.dump(anon_list,pickle_file)

    async def command_anon_apodo():
        tmp_msg = msg.content
        tmp_channel = msg.channel
        tmp_user_id = msg.author.id
        tmp_guild_id = msg.guild.id
        await msg.delete()

        tmp_apodo = tmp_msg.replace("e!apodo ","",1)
        if tmp_apodo=="":
            await msg.channel.send(content="Tienes que escribit tu apodo después del comando **e!apodo **",delete_after=3)
        elif tmp_user_id in anon_list:
            anon_list[tmp_user_id]["apodo"] = tmp_apodo
            await msg.channel.send(content="Apodo cambiado correctamente",delete_after=2)
        else:
            anon_list[tmp_user_id] = {"apodo":tmp_apodo,"foto":ANON_DEFAULT_PFP,"guild":tmp_guild_id}
            await msg.channel.send(content="Apodo cambiado correctamente",delete_after=2)

        with open(PICKLE_OF_ANONS, 'wb') as pickle_file:
            pickle.dump(anon_list,pickle_file)


    async def command_anon_photo():
        tmp_channel = msg.channel
        tmp_user_id = msg.author.id
        tmp_guild_id = msg.guild.id

        if len(msg.attachments)>0:
            attachment_file=await msg.attachments[0].to_file()
            tmp_msg = await channel_logs.send(content="Usuario: "+str(msg.author),file = attachment_file)
            tmp_msg_image_url = tmp_msg.attachments[0].url
            await msg.channel.send(content="Foto cambiada correctamente",delete_after=1.5)

        else:
            tmp_msg_image_url = ANON_DEFAULT_PFP
            await msg.channel.send(content="Tienes que adjuntar una foto junto al comando e!foto",delete_after=3)

        await msg.delete()

        if tmp_user_id in anon_list:
            anon_list[tmp_user_id]["foto"] = tmp_msg_image_url
        else:
            anon_list[tmp_user_id] = {"apodo":"Usuario Anónimo","foto":tmp_msg_image_url,"guild":tmp_guild_id}

        with open(PICKLE_OF_ANONS, 'wb') as pickle_file:
            pickle.dump(anon_list,pickle_file)

    async def command_anon():
        msg_to_say = msg.content
        tmp_channel = msg.channel
        tmp_user_id = msg.author.id
        tmp_user_nick = msg.author.display_name  # To calculate our weekly HASH
        await msg.delete()

        # Add a number that changes every ~10 days at the end, to vary the hash
        # Use nickname so user can vary his hash by just changing it's nickname
        # Hash it with md5 and get 4 first digits. I don't really care about colisions :P
        str_to_hash = tmp_user_nick + str(tmp_user_id) + \
            str(hex(int(time.time())))[2:-5]
        hash_adition = hashlib.md5(
            str_to_hash.encode('utf-8')).hexdigest()[:4].upper()

        if tmp_user_id in anon_list:
            tmp_avatar = anon_list[tmp_user_id]["foto"]
            tmp_author = anon_list[tmp_user_id]["apodo"]
        else:
            tmp_avatar = ANON_DEFAULT_PFP
            tmp_author = "Usuario Anónimo #" + hash_adition

        msg_to_say = msg_to_say.replace("e!anon ","",1)
        msg_to_say = discord.utils.escape_mentions(msg_to_say)
        webhook_discord = await tmp_channel.create_webhook(name=tmp_author, reason="EldoBOT: Temp-webhook Usuario-anónimo")
        await webhook_discord.send(content = msg_to_say, username = tmp_author, avatar_url = tmp_avatar)#, allowed_mentions = allowed_mentions_NONE)
        # Delete webhook
        await webhook_discord.delete()
        print("Confesión hecha!")

    async def command_say_like(msg):
        msg_to_say = msg.clean_content
        tmp_content = msg.content
        tmp_channel = msg.channel
        tmp_author = msg.author
        user_to_imitate = msg.mentions[0]

        # Delete message
        await msg.delete()

        print(msg_to_say)
        if(tmp_content.lower().find("e!di como id:")==0):
            user_ID_to_imitate = re.findall('<(.*?)>', tmp_content)[0]
            msg_to_say = msg_to_say.replace("<"+user_ID_to_imitate+">","")
            msg_to_say = msg_to_say.replace("e!di como id:","")
            #msg_to_say = tmp_clean_msg[tmp_clean_msg.find(msg_to_say[2:4]):] # Ohtia! Que es esto?? Pos... no hace falta entenderlo :P
        else:
            msg_to_say = msg_to_say.replace("e!di como","",1)
            msg_to_say = msg_to_say.replace("@"+user_to_imitate.nick,"",1)
            #msg_to_say = tmp_clean_msg[tmp_clean_msg.find(msg_to_say[2:4]):] # WTF, porque?? Shhh

        if(user_to_imitate != None):
            await send_msg_as(user_to_imitate=user_to_imitate,channel=tmp_channel,content=msg_to_say,embed=True,user_that_sent=tmp_author)
        else:
            print("User: "+user_ID_to_imitate+" not found")
    
    async def botStatsShow(date_to_search=""):
        pandasDataFrame = pd.DataFrame.from_dict(stats)
        pandasDataFrame = pandasDataFrame.unstack().reset_index().fillna(0)
        pandasDataFrame['index1'] = pandasDataFrame.index
        pandasDataFrame = pandasDataFrame.rename(columns={"level_0": "Date", "level_1": "Command","0":"Value","index1":"Index"})
        pandasDataFrame = pandasDataFrame.rename(columns={pandasDataFrame.columns[2]: "Value"})

        print(pandasDataFrame)
        
        fig, ax = plt.subplots()
        
        for key, grp in pandasDataFrame.groupby(['Command']):
            ax = grp.plot(ax=ax, kind='line', x='Index', y='Value', label=key)

        plt.legend(loc='best')
        plt.savefig('statsGraph.png')
        
        await msg.channel.send(content="Test", file=discord.File(fp= "statsGraph.png", filename="statsGraph.png"))

        """if date_to_search == "today":
            date_to_search = datetime.today().strftime("%d/%m/%Y")
            msg_to_send+="**"+date_to_search+"**:\n"
            for command in stats[date_to_search]:
                msg_to_send+="**"+command+"**:"+str(stats[day][command])+"\n"
        else:
            msg_to_send = ""
            for day in stats:
                msg_to_send+="**"+day+"**:\n"
                for command in stats[day]:
                    msg_to_send+="**"+command+"**:"+str(stats[day][command])+"\n"
                if len(msg_to_send)>1930:
                    await msg.channel.send(msg_to_send)
                    msg_to_send = ""
            await msg.channel.send(msg_to_send)"""
    
    async def createGuild():
        """
        guildName = msg.content.replace("guild_create ","")
        createdGuild = await client.create_guild(guildName, region=None, icon=None)
        await msg.channel.send("Guild created!")
        createdChannel = await createdGuild.create_text_channel("general")
        createdInvitation = await createdChannel.create_invite()
        await msg.channel.send("Invitation URL:\n"+createdInvitation.url)"""
        await msg.channel.send("Función desactivada")
        return

    # The channel where this command is used gets temporarily closed, and their members get muted
    # Use it in case of a raid. 
    async def za_warudo(msg):

        pass

    # This saves in a Databases what emojis where used by wich user and when, so we can do statistics later on
    async def save_emojis():
        if re.findall('<:(.*?)>', msg.content, re.DOTALL) or len("".join(c for c in msg.content if c in emoji.UNICODE_EMOJI))>0:
            raw_emojis_in_msg = re.findall('<:(.*?)>', msg.content, re.DOTALL)
            emojis_IDs = []
            emojis_call_names = []
            emojis_image_URL = []
            emojis_to_count = []
            emoji_DB_ID = []
            mycursor.execute("SELECT EMOJI_ID, ID FROM "+DB_NAME+".EMOJI;")
            tmp_list_of_existing_IDs = mycursor.fetchall()
            list_of_existing_IDs=[]
            for element in tmp_list_of_existing_IDs:
                list_of_existing_IDs.append(element[0])
            list_of_existing_DB_IDs=[]
            for element in tmp_list_of_existing_IDs:
                list_of_existing_DB_IDs.append(element[1])

            # Creating a list of the emojis on the message, and saving information
            # about the ones that we are seeing for the first time
            for raw_emoji in raw_emojis_in_msg:
                temp_emojiID = raw_emoji[raw_emoji.find(":")+1:]
                emojis_to_count.append(str(temp_emojiID))
                if not (temp_emojiID in list_of_existing_IDs or temp_emojiID in emojis_IDs):
                    emojis_call_names.append(raw_emoji[:raw_emoji.find(":")])
                    emojis_IDs.append(temp_emojiID)
                    temp_emoji = client.get_emoji(int(emojis_IDs[-1]))
                    if(temp_emoji==None):
                        emojis_image_URL.append("https://cdn.discordapp.com/emojis/"+str(emojis_IDs[-1])+".png")
                    else:
                        emojis_image_URL.append(str(temp_emoji.url))
                elif(temp_emojiID in list_of_existing_IDs):
                    emoji_DB_ID.append(list_of_existing_DB_IDs[list_of_existing_IDs.index(temp_emojiID)])

            # Add the normie UNICODE emojis to the list
            normie_emoji_list= "".join(c for c in msg.content if c in emoji.UNICODE_EMOJI)
            for normie_emoji in normie_emoji_list:
                emojis_to_count.append(str(ord(normie_emoji)))
                if not (str(ord(normie_emoji)) in list_of_existing_IDs or str(ord(normie_emoji)) in emojis_IDs):
                    emojis_call_names.append(unicodedata.name(normie_emoji))
                    emojis_IDs.append(str(ord(normie_emoji)))
                    emojis_image_URL.append("openmoji/master/color/618x618/"+str(format(ord(normie_emoji),"x").upper())+".png")
                elif(str(ord(normie_emoji)) in list_of_existing_IDs):
                    emoji_DB_ID.append(
                        list_of_existing_DB_IDs[list_of_existing_IDs.index(str(ord(normie_emoji)))])

            # Add new emojis to database
            if(len(emojis_IDs)>0):
                mySQL_query = "INSERT INTO "+DB_NAME+".EMOJI (EMOJI_ID, NAME, IMAGE_URL) VALUES (%s, %s, %s) "
                records_to_insert = tuple(zip(emojis_IDs, emojis_call_names[:33], emojis_image_URL))
                mycursor.executemany(mySQL_query,records_to_insert)
                mydb.commit()
                if(len(records_to_insert)>0):
                    print("We just added " + str(len(emojis_IDs))+" new emoji(s)! Here the list: "+str(emojis_call_names))

                for i_emoji in range(len(records_to_insert)): # Cool code that extracts the real DB ID's
                    emoji_DB_ID.append(mycursor.lastrowid-i_emoji)

            # Checking if the writer of the message is already on our Database
            mycursor.execute("SELECT USER_ID FROM "+DB_NAME +
                             ".USER WHERE USER.USER_ID = " + str(msg.author.id) + ";")
            tmp_list_of_existing_IDs = mycursor.fetchall()
            if(mycursor.rowcount == 0):
                addUserToDB(msg.author)
            
            # Checking if channel is on our Database
            mycursor.execute("SELECT CHANNEL_ID FROM "+DB_NAME +
                             ".CHANNEL WHERE CHANNEL.CHANNEL_ID = " + str(msg.channel.id) + ";")
            tmp_list_of_existing_IDs = mycursor.fetchall()
            # Insert Channel if it isn't there
            if(mycursor.rowcount == 0):
                mycursor.execute("SELECT ID FROM "+DB_NAME +
                             ".GUILD WHERE GUILD.GUILD_ID = " + str(msg.guild.id) + ";")
                tmp_list_of_existing_IDs = mycursor.fetchall()
                
                if(mycursor.rowcount == 0):
                    print("ERROR, GUILD NOT FOUND!")
                else:
                    guild_DB_id = tmp_list_of_existing_IDs[0][0]
                    mySQL_query = "INSERT INTO " + DB_NAME + ".CHANNEL (CHANNEL_ID ,GUILD_ID, NAME) VALUES (%s, %s, %s);"
                    mycursor.execute(mySQL_query, (str(msg.channel.id), str(guild_DB_id), unidecode(msg.channel.name).replace(
                        "DROP", "DRO_P").replace("drop", "dro_p").replace("*", "+")))
                    mydb.commit()

            # Put the emoji + user in the database
            ## Get user ID
            mycursor.execute("SELECT ID FROM "+DB_NAME +
                            ".USER WHERE USER.USER_ID = " + str(msg.author.id) + ";")
            tmp_list_of_existing_IDs = mycursor.fetchall()
            if(mycursor.rowcount == 0):
                print("ERROR, AUTHOR NOT FOUND!")
            else:
                author_DB_id = tmp_list_of_existing_IDs[0][0]
            ## Get guild ID
            mycursor.execute("SELECT ID FROM "+DB_NAME +
                            ".GUILD WHERE GUILD.GUILD_ID = " + str(msg.guild.id) + ";")
            tmp_list_of_existing_IDs = mycursor.fetchall()
            if(mycursor.rowcount == 0):
                print("ERROR, GUILD NOT FOUND!")
            else:
                guild_DB_id = tmp_list_of_existing_IDs[0][0]

            userID_list = [author_DB_id]*(len(emoji_DB_ID))
            guildID_list = [guild_DB_id]*(len(emoji_DB_ID))
            records_to_insert = tuple(zip(emoji_DB_ID,userID_list,guildID_list))
            mySQL_query = "INSERT INTO EMOJI_SENT (EMOJI_ID, USER_ID, GUILD_ID) VALUES (%s, %s, %s) "
            mycursor.executemany(mySQL_query,records_to_insert)
            mydb.commit()

    def urlExtractor(text):
        # findall() has been used  
        # with valid conditions for urls in text
        found_in = text.find(".")
        if len(text) > 10 and (found_in < len(text)-1 and found_in != -1):
            regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
            url = re.findall(regex,text)       
            return [x[0] for x in url]
        return ""

    # Handle forbidden nHentai links
    def link_forbidden_tag_search(urls,guildID):
        forbidden_detected = ""
        bad_url = ""
        replacement_text = ""
        forbidden_tag_list = [tag[1] for tag in forbidden_tags if tag[0]==str(guildID)]
        for url in urls:
            # Check for nHentai
            if(url.find("nhentai.net/g/")!=-1):
                page = requests.get(url)
                if(page.status_code == 200):
                    soup = BeautifulSoup(page.content, 'html.parser') 
                    tags = soup.find(id="tags")
                    for tag_type in list(tags.children):
                        if(tag_type.contents[0].lower().find("tags")!=-1):
                            # Here we get all the tags
                            for tag in tag_type.findAll("span", class_='name'):
                                if(tag.getText().lower() in forbidden_tag_list):
                                    forbidden_detected += tag.getText()+" "
                                    bad_url = url
                            if forbidden_detected!="":
                                replacement_text = "#" + re.findall(r'\d+', url)[0]
                else:
                    print("We couldn't open the Link: ",url)

            # Check for HitomiLa
            elif(url.find("hitomi.la/")!=-1):
                url_copy = url # Save a copy to send it at the end
                # This URL has an URL that redirects us the one we want :P
                if(url.find("https://hitomi.la/reader/") != -1):
                    redirect_url_code = re.findall(r'\d+', url)[0]
                    url = "https://hitomi.la/galleries/"+redirect_url_code+".html"

                # If the user is strange enough to give us this as URL. 
                #  It also handles the above generated url. 
                #  It ultimately redirects to the Doujinshi site that has the tags on it
                if(url.find("https://hitomi.la/galleries/") != -1 ):
                    page = requests.get(url)
                    if(page.status_code == 200):
                        soup = BeautifulSoup(page.content, 'html.parser')
                        tags = soup.find('a', href=True)
                        url = tags['href']
                    else:
                        print("We couldn't open the redirected link: ",url)
                
                # If the URL is from the site where the tags are, read the tags
                #  It also can handle the above generated url. 
                if(url.find("https://hitomi.la/doujinshi/") != -1):
                    page = requests.get(url)                
                    if(page.status_code == 200):
                        soup = BeautifulSoup(page.content, 'html.parser')
                        tags = soup.findAll("ul", class_="tags")
                        tags = tags[1].findAll("li")
                        for tag in tags:
                            for forbidden_tag in forbidden_tag_list:
                                if(tag.getText().lower()==forbidden_tag):
                                    forbidden_detected += tag.getText()+" "
                                    bad_url = url
                        if forbidden_detected!="":
                            replacement_text = soup.select("body > div.container > div.content > div.gallery.dj-gallery > h1 > a")[0].getText()
                    else:
                        print("We couldn't open the Link: ",url)
                bad_url = url_copy # Restore copy. We do this, so we send the correct url to replace

        if forbidden_detected!="":
            return [forbidden_detected,bad_url,replacement_text]
        else:
            return None
    
    async def tgfDoujinshi(msg):
        urls = urlExtractor(msg.content)
        if(len(urls)>0):
            forbiddenTags_url = link_forbidden_tag_search(urls,msg.guild.id)
            if (forbiddenTags_url!=None):
                forbiddenCode = forbiddenTags_url[2]
                content = msg.content.replace(forbiddenTags_url[1],"`"+forbiddenCode+"`")
                content += "\n\nEste link fué reducido porque detectamos el/los siguientes tags:\n`"+forbiddenTags_url[0]+"`"
                await send_msg_as(user_to_imitate=msg.author,channel=msg.channel,content=content)
                await msg.delete()
    
    async def spam_detector(msg):
        global MUTE_ROL
        for rol in msg.author.roles: # Eww, Hardcoded :P (>=lvl 3)
            if(rol.id == 630560047872737320):
                return
        
        if str(msg.author.id) not in spam_detector_list:
            spam_detector_list[str(msg.author.id)] = []
        
        spam_detector_list[str(msg.author.id)].append(
            [homoglyphs.to_ascii(msg.content), msg.created_at, msg.channel.id])

        if len(spam_detector_list[str(msg.author.id)])>5:
            first_to_scan = 1
            spam_points = 0
            for spm_msg in spam_detector_list[str(msg.author.id)]:
                for i in range (first_to_scan,len(spam_detector_list[str(msg.author.id)])):
                    # If the messages where sent 5 minutes apart or less
                    if( spm_msg[0]==spam_detector_list[str(msg.author.id)][i][0]
                        and abs(spm_msg[1]-spam_detector_list[str(msg.author.id)][i][1]).total_seconds()/60<7 
                        and spm_msg[2]!=spam_detector_list[str(msg.author.id)][i][2] ):
                        print("spam?")
                        spam_points += 1
                first_to_scan += 1
                if first_to_scan == len(spam_detector_list[str(msg.author.id)]):
                    break
            
            if spam_points >= 4:
                msg.author.add_roles(MUTE_ROL)
                print("SPAM!!!")

        elif len(spam_detector_list[str(msg.author.id)])>10:
            spam_detector_list[str(msg.author.id)].pop(0)
        


    global temp_busquedas
    msg_received = msg.content.lower()
    await save_emojis()

    # Global commands without activators
    if msg.content.lower().find("ch!reportuser") == 0:
        await send_report()
    elif msg.content.lower().find("spoiler") != -1:
        await command_spoiler()
    elif msg.content.lower().find("name") != -1:
        TIME_A1 = int(round(time.time() * 1000))
        await new_find_name(msg)
        print("The search for the name finished after ", int(round(time.time() * 1000)) - TIME_A1)

    elif msg.content.lower().find("nombre") != -1:
        await new_find_name(msg)

    if msg.content.lower().find(":v") != -1:
        await replace_user_text(":v","Soy subnormal")

    # The Great Firewall
    await tgfDoujinshi(msg)

    if msg_received[:2]==activator:
        msg_command = msg_received[2:]
        msg_text = msg.content[2:]
        if msg_command.split()[0][:2]=="id" and msg_command.split()[0][2:].isnumeric() and len(msg_command.split())>1:
            await userNameHelper(msg = msg,id = msg_command.split()[0][2:], user_text = msg_text[msg_text.find(" "):])
            statsAdd("help-name")
        elif msg_command.split()[0]=="add" and len(msg_command.split())>1:
            await userNameAdd(msg = msg, user_text = msg_text.replace("add",""))
            statsAdd("add-name")
        elif  msg_command.find("emoji_stats")==0 and msg.author.permissions_in(msg.channel).kick_members:
            statsAdd("emoji_stats")
            await command_emoji_stats()
        elif msg_command == "help" or msg_command == "ayuda":
            statsAdd("help")
            await command_help()
        elif msg_command == "stop" or msg_command.lower() == "za warudo":
            await za_warudo(msg)
        elif msg_command.find("conf") == 0 or msg_command.find("configurar") == 0:
            statsAdd("conf")
            await command_config()
        elif msg_command.find("permitir name") == 0 or msg_command.find("permitir nombre") == 0:
            statsAdd("permitir-name")
            await command_config_permName()
        elif msg_command.find("bloquear name") == 0 or msg_command.find("bloquear nombre") == 0:
            statsAdd("bloquear-name")
            await command_config_bloqName()
        elif msg_command.find("di como")==0:
            statsAdd("di-como")
            await command_say_like(msg)
        elif msg_command.find("say") == 0 or msg_command.find("di") == 0:
            statsAdd("say")
            await command_say()
        elif msg_command.find("guilds") == 0 or msg_command.find("servidores") == 0:
            statsAdd("guilds")
            await command_guilds()
        elif msg_command == "ping" or msg_command == "test":
            statsAdd("ping")
            await command_ping()
        elif msg_command == "boost list":
            statsAdd("boost")
            await command_boost_list()
        elif msg_command.find("bot") == 0:
            statsAdd("bot")
            await command_bot()
        elif msg_command =="reset" or msg_command == "resetear":
            statsAdd("reset")
            await command_anon_reset()
        elif msg_command.find("apodo") == 0 or msg_command.find("nick") == 0:
            statsAdd("apodo")
            await command_anon_apodo()
        elif msg_command.find("foto") == 0 or msg_command.find("photo") == 0:
            statsAdd("foto")
            await command_anon_photo()
        elif msg_command.find("anon ")==0 and (msg.channel.id==706925747792511056 or msg.channel.id==681672275556434009 or msg.guild.id==646799198167105539 or msg.author.permissions_in(msg.channel).manage_messages):
            statsAdd("anon")
            await command_anon()
        elif msg_command.find("say") == 0:
            statsAdd("say")
            await command_ping()
        elif msg_command.find("qwertz")==0:
            statsAdd("qwertz")
            await testTraceMoe()
        elif msg_command.find("busca")==0:
            if not temp_busquedas:
                await msg.channel.send("Nope! No te podré ayudar esta vez")
            else:
                print("Entering debug")
                statsAdd("busca")
                await debugTraceMoe(msg=msg)
        elif msg_command.find("stats")==0:
            await botStatsShow()
            statsAdd("stats")
        elif msg_command.find("guild_create")==0:
            await createGuild()
            statsAdd("guildCreate")
        elif msg_command.find("activa bus")==0:
            if msg.author.permissions_in(msg.channel).kick_members:
                if temp_busquedas:
                    await msg.channel.send("El comando buscar ya está activado")
                else:
                    temp_busquedas = True
                    await msg.channel.send("Búsquedas por imágen activadas")
                statsAdd("activa")
            else:
                await msg.channel.send("No tienes los permisos suficientes para usar este comando")
        elif msg_command.find("desactiva bus")==0:
            if msg.author.permissions_in(msg.channel).kick_members:
                if not temp_busquedas:
                    await msg.channel.send("El comando buscar ya está desactivado")
                else:
                    temp_busquedas = False
                    await msg.channel.send("Búsquedas por imágen desactivadas")
                statsAdd("desactiva")
            else:
                await msg.channel.send("No tienes los permisos suficientes para usar este comando")
        elif msg_command.isnumeric():
            if(int(msg_command)<=10 and int(msg_command)>0):
                list_of_number_emojis=["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
                message_sent=False
                async for message_element in msg.channel.history(limit=4):
                    if (message_element.author == msg.author and message_element.content != msg.content and not message_sent):
                        for i in range(int(msg_command)):
                            await message_element.add_reaction(list_of_number_emojis[i])
                            message_sent = True
            await msg.delete()
    #await spam_detector(msg)
            
client.run(Discord_TOKEN)
