import discord
from discord.ext import commands

from io import BytesIO
from requests import Session
import pickle
import cv2
from PIL import Image
import requests
import mysql.connector
import imagehash
from unidecode import unidecode
import urllib.parse
import json
from datetime import datetime






# TraceMOE Limits:
#   10 searches per minute
#   150 searches per day
#   https://soruly.github.io/trace.moe/#/
#
# SauceNAO Limits:
#   10 searches per minute
#   200 searches per day

class SearchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.COLOR_GREEN=1425173
        self.COLOR_BLUE=2190302
        self.COLOR_YELLOW=16776960
        self.COLOR_RED=15597568
        self.LOG_CHANNEL = 708648213774598164

        self.messages_to_react = []
        self.status_messages_to_react = []

        # Import channel configurations
        PICKLE_OF_CONFIGURATIONS="configurations.pkl"
        self.configurations = pickle.load(open(PICKLE_OF_CONFIGURATIONS, "rb" ))

        # TraceMoe variables
        self.tracemoe_session = Session()
        self.tracemoe_session.headers = {
            "Content-Type": "application/json"
        }

        # Get some variables from the magic Pickle
        #  saddly backwards compatible...
        keys = pickle.load(open("keys.pkl", "rb" ))

        ## Connect to Database
        self.mydb = mysql.connector.connect(
            host=keys["Database"]["host"],
            user=keys["Database"]["user"],
            passwd=keys["Database"]["passwd"],
            database=keys["Database"]["database"])
        self.mycursor = self.mydb.cursor()

        self.sauceNAO_TOKEN = keys["sauceNAO_TOKEN"]
        self.DB_NAME = keys["Database"]["database"]

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel_logs = await self.bot.fetch_channel(self.LOG_CHANNEL)
    
## e!buscar Command
    # (Copying) Reeplacing the TraceMoe.py library to fit it here in code
    # Shamefully copied from https://github.com/Ethosa/tracemoe/blob/master/tracemoe/TraceMoe.py
    def tracemoe_search(self, url):
        path = "https://trace.moe/api/search"#?method=jc" # New Algo method

        return self.tracemoe_session.get(
            path, params={"url": url}
        ).json()

    def tracemoe_video_preview_natural(self, response, index=0, mute=False):
        response = response["docs"][index]
        url = "https://media.trace.moe/video/%s/%s?t=%s&token=%s" % (
            response["anilist_id"],
            response["filename"], response["at"],
            response["tokenthumb"]
        )
        if mute:
            url += "&mute"
        return self.tracemoe_session.get(url).content

    def tracemoe_image_preview(self, response, index=0, page="thumbnail.php"):
        response = response["docs"][index]
        url = "https://trace.moe/%s?anilist_id=%s&file=%s&t=%s&token=%s" % (
            page, response["anilist_id"],
            response["filename"], response["at"], response["tokenthumb"]
        )
        return self.tracemoe_session.get(url).content

    def tracemoe_video_preview(self, response, index=0):
        return self.tracemoe_image_preview(response, index, "preview.php")

    @commands.command(name = "buscar",
                    aliases=["busca"],
                    usage="Envía un screenshot de un anime/H junto a este comando",
                    description = "El bot te devolverá el nombre y un breve video para entender el contexto")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def buscar(self, ctx):
        # Check if message has an attachment, ignore if not
        if len(ctx.message.attachments)>0:
            image_to_search_URL = ctx.message.attachments[0].url
        else:
            return

        fileToSend = None
        videoFound = False
        await ctx.trigger_typing()
        response = self.tracemoe_search(image_to_search_URL)
        for i, result in enumerate(response["docs"]):
            # If we already searched the 3 first videos, we skip
            # It's a strange solution, yeah, but i don't want to implement something better :P
            if(i >=3):
                break
            if result["similarity"] > 0.87:
                try:
                    videoN = self.tracemoe_video_preview_natural(response,index=i)
                    videoForce = self.tracemoe_video_preview(response,index=i)
                    # If the video without the natural cut is bigger with a diference of 1sec aprox, then we choose that one
                    #print("Normal:",BytesIO(videoForce).getbuffer().nbytes,"vs Natural:",BytesIO(videoN).getbuffer().nbytes)
                    if(BytesIO(videoForce).getbuffer().nbytes - BytesIO(videoN).getbuffer().nbytes>45000):
                        videoN = videoForce
                    # If the video is not available, we skip
                    if(BytesIO(videoN).getbuffer().nbytes <= 500):
                        continue
                    fileToSend = discord.File(fp = BytesIO(videoN),filename="eldobot_preview.mp4")
                    videoFound=True
                    break
                except Exception as e: print(e)

        if not videoFound:
            image = self.tracemoe_image_preview(response)
            fileToSend = discord.File(fp = BytesIO(image),filename="Preview_not_found_sowy_uwu.jpg")

        # Detect type of Anime
        if "is_adult" in response["docs"][0]:
            if(response["docs"][0]["is_adult"]==True):
                typeOfAnime = "H"
            else:
                typeOfAnime = "anime"
        else:
            typeOfAnime = "anime"

        # Get Anime tittle
        if "title_english" in response["docs"][0]:
            if response["docs"][0]["title_english"]!="":
                nameOfAnime = response["docs"][0]["title_english"]
            else:
                nameOfAnime = response["docs"][0]["anime"]
        else:
            nameOfAnime = response["docs"][0]["anime"]

        # Get Anime episode
        if "episode" in response["docs"][0]:
            if response["docs"][0]["episode"]!="":
                episodeOfAnime = str(response["docs"][0]["episode"])
            else:
                episodeOfAnime = "cuyo número no recuerdo"
        else:
            episodeOfAnime = "cuyo número no recuerdo"

        # Get Anime season (year)
        if "season" in response["docs"][0]:
            if response["docs"][0]["season"]!="":
                seasonOfAnime = str(response["docs"][0]["season"])
            else:
                seasonOfAnime = "en el que se produjo"
        else:
            seasonOfAnime = "en el que se produjo"

        # Get simmilarity
        if "similarity" in response["docs"][0]:
            if response["docs"][0]["similarity"]!="":
                simmilarityOfAnime = "{:04.2f}".format(response["docs"][0]["similarity"]*100.0)
            else:
                print("similarity Not Found")
                print(response)
                return
        else:
            print("similarity Not Found")
            print(response)
            return

        msg_to_send = "Estoy {}% seguro de que la imágen es de un {} del año {} llamado **\"{}\"** , episodio {}.".format(simmilarityOfAnime,typeOfAnime,seasonOfAnime,nameOfAnime,episodeOfAnime)

        await ctx.send(content = msg_to_send,file = fileToSend, reference = ctx.message, mention_author=True)
##################
## name Command ##
##################
    async def send_msg_as(self, user_to_imitate,channel,content,embed=False,user_that_sent=None,footer_msg=None,media=None):
        # Filter mentions out of the content
        content = discord.utils.escape_mentions(content)
        pfp_to_imitate = await user_to_imitate.avatar_url.read()

        # Create a temporal Webhook to send the message
        webhook_discord = await channel.create_webhook(name=user_to_imitate.name, avatar=pfp_to_imitate, reason="EldoBOT: Temp-webhook")
        
        # If we want to send it as an Embed (that shows who sent it) we go here
        if embed and user_that_sent!=None:
            embed_to_send = discord.Embed(description=content, colour=3553598).set_footer(text="Enviado por: " + str(user_that_sent.display_name))
            if media!=None:
                embed_to_send.set_image(url = media)
            sent_message = await webhook_discord.send(embed = embed_to_send, username = user_to_imitate.display_name, wait = True)
        elif footer_msg!=None:
            embed_to_send = discord.Embed(description=content, colour=3553598).set_footer(text = footer_msg)
            if media!=None:
                embed_to_send.set_image(url = media)
            sent_message = await webhook_discord.send(embed = embed_to_send, username = user_to_imitate.display_name, wait = True)
        elif embed:
            embed_to_send = discord.Embed(description=content, colour=3553598)
            if media!=None:
                embed_to_send.set_image(url = media)
            sent_message = await webhook_discord.send(embed = embed_to_send, username = user_to_imitate.display_name, wait = True)
        # If we just want to send it as a normal message, we go here
        elif not embed:
            sent_message = await webhook_discord.send(content = content, username = user_to_imitate.display_name, wait = True)
        
        print(content," Printed!")

        # Delete webhook
        print(sent_message.id)
        await webhook_discord.delete()
        print(sent_message.id)
        return sent_message

    def dbUserID_to_discordIDNameImage(self,id):
        mySQL_query = "SELECT USER_ID, USERNAME, IMAGE_URL FROM "+self.DB_NAME+".USER WHERE ID="+str(id)+";"
        self.mycursor.execute(mySQL_query)
        tmp_user_DB = self.mycursor.fetchall()
        if (self.mycursor.rowcount==0):
            return None
        else:
            return tmp_user_DB[0]

    def addUserToDB(self, author):
        mySQL_query = "INSERT INTO " + self.DB_NAME + ".USER (USER_ID ,USERNAME, IMAGE_URL) VALUES (%s, %s, %s);"
        self.mycursor.execute(mySQL_query, (str(author.id), unidecode(author.name).replace(
            "DROP", "DRO_P").replace("drop", "dro_p")[:32].replace("*", "+"), # Lame&unnecesary SQL-Injection protection
            str(author.avatar_url)[:str(author.avatar_url).find("?")]))
        self.mydb.commit()
        return self.mycursor.lastrowid

    def discordID_to_dbUserID(self, id,author=None):
        mySQL_query = "SELECT ID FROM "+self.DB_NAME+".USER WHERE USER_ID="+str(id)+";"
        self.mycursor.execute(mySQL_query)
        tmp_user_DBid = self.mycursor.fetchall()
        if(self.mycursor.rowcount==0):
            if author!=None:
                return self.addUserToDB(author)
            else:
                return None
        else:
            return tmp_user_DBid[0][0]

    def discordGuildID_to_dbGuildID(self, id):
        mySQL_query = "SELECT ID FROM "+self.DB_NAME+".GUILD WHERE GUILD_ID="+str(id)+";"
        self.mycursor.execute(mySQL_query)
        tmp_guild_DBid = self.mycursor.fetchall()
        if(self.mycursor.rowcount==0):
            return None
        else:
            return tmp_guild_DBid[0][0]

    async def userNameAdd(self, msg, user_text):
        if len(msg.attachments) == 0:
            await msg.channel.send(content="Tienes que enviar una imagen junto a este comando",delete_after=7)

        imageData = await msg.attachments[0].read()
        imageData = BytesIO(imageData)
        pil_image = Image.open(imageData)
        image_hash = str(imagehash.phash(pil_image,16))
        pil_image.save("temp_images/"+image_hash+".png")

        with open("out.txt", "wb") as outfile:
            # Copy the BytesIO stream to the output file
            outfile.write(imageData.getbuffer())
        imageData.close()

        discord_user_id = str(self.discordID_to_dbUserID(msg.author.id))
        discord_guild_id = str(self.discordGuildID_to_dbGuildID(msg.guild.id))

        mySQL_query = "INSERT INTO "+self.DB_NAME+".NAME_IMAGE (HASH, URL, FILE_NAME, EXTENSION, GUILD_THAT_ASKED, USER_THAT_ASKED, FOUND, FOUND_BY_BOT, CONFIRMED_BY) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
        self.mycursor.execute(mySQL_query, (image_hash, str(msg.attachments[0].url),"HASH.png", "png", discord_guild_id, discord_user_id,"1","0",discord_user_id,))
        self.mydb.commit()
        name_image_id = self.mycursor.lastrowid

        mySQL_query = "INSERT INTO "+self.DB_NAME+".NAME_RESULT (USER_THAT_FOUND, TEXT) VALUES (%s, %s) "
        self.mycursor.execute(mySQL_query, (discord_user_id, user_text, ))
        self.mydb.commit()
        name_result_id = self.mycursor.lastrowid

        # Link Name Result with Name Image
        mySQL_query = "INSERT INTO "+self.DB_NAME+".NAME_LOG (IMAGE_ID, NAME_ID) VALUES (%s, %s) "
        self.mycursor.execute(mySQL_query, (name_image_id, name_result_id))
        self.mydb.commit()

        await msg.channel.send(content="Imágen añadida!",delete_after=7)



    # It get's called when the user wants to send the name of an image that wasn't found by the bot
    # It sends and Embed message with the information that the user gaves us, and it saves it on our DB
    async def userNameHelper(self, msg, id, user_text):
        # Get User ID
        mySQL_query = "SELECT FOUND, URL, CONFIRMED_BY FROM "+self.DB_NAME + \
            ".NAME_IMAGE WHERE ID="+id+";"
        self.mycursor.execute(mySQL_query)
        tmp_user_DBid = self.mycursor.fetchall()
        if(self.mycursor.rowcount==0):
            await msg.channel.send(content="No pudimos encontrar la id "+id+" en nuestra base de datos. Si crees que esto es un error, menciona a mi creador @Eldoprano",delete_after=20)
        elif(tmp_user_DBid[0][0]==1):
            user_that_confirmed = self.dbUserID_to_discordIDNameImage(tmp_user_DBid[0][2])[1]
            if(user_that_confirmed != None):
                await msg.channel.send(content="Esta imagen ya fué aceptada como encontrada por: "+user_that_confirmed,delete_after=20)
            else:
                print("Error, user "+tmp_user_DBid[0][2]+" doesn't exist")
        else:
            image_url=None
            if len(msg.attachments) > 0:
                image_url = msg.attachments[0].url

            # Update status of image
            db_author_id = self.discordID_to_dbUserID(msg.author.id, msg.author)

            mySQL_query = "UPDATE "+self.DB_NAME+".NAME_IMAGE SET FOUND=1, FOUND_BY_BOT=0, CONFIRMED_BY=%s \
                WHERE ID="+id+";"
            self.mycursor.execute(mySQL_query, (str(db_author_id),))
            self.mydb.commit()

            # Create a Name Result
            if image_url==None:
                mySQL_query = "INSERT INTO "+self.DB_NAME+".NAME_RESULT (USER_THAT_FOUND, TEXT) VALUES (%s, %s) "
                self.mycursor.execute(mySQL_query, (str(db_author_id), user_text, ))
                self.mydb.commit()
            else:
                mySQL_query = "INSERT INTO "+self.DB_NAME+".NAME_RESULT (USER_THAT_FOUND, TEXT, IMAGE_LINK) VALUES (%s, %s, %s) "
                self.mycursor.execute(mySQL_query, (str(db_author_id), user_text, image_url))
                self.mydb.commit()
            
            name_result_id = self.mycursor.lastrowid

            # Link Name Result with Name Image
            mySQL_query = "INSERT INTO "+self.DB_NAME+".NAME_LOG (IMAGE_ID, NAME_ID) VALUES (%s, %s) "
            self.mycursor.execute(mySQL_query, (id, name_result_id))
            self.mydb.commit()

            # Create and send final Embedded
            if image_url==None:
                embed_to_send = discord.Embed(description=user_text, color=self.COLOR_GREEN).set_author(
                    name=msg.author.name, icon_url=str(msg.author.avatar_url)).set_thumbnail(url = tmp_user_DBid[0][1])
            else:
                embed_to_send = discord.Embed(description=user_text, color=self.COLOR_GREEN).set_author(
                    name=msg.author.name, icon_url=str(msg.author.avatar_url)).set_thumbnail(url = tmp_user_DBid[0][1]).set_image(url = image_url)

            await msg.channel.send(embed=embed_to_send)
            await msg.delete()

        

    # Outputs an Embed Discord message with usefull links to find the searched image
    def embedSearchHelper(self, url, idOfName = ""):
        unparsed_url = url
        url = urllib.parse.quote(url)
        yandex_url = "https://yandex.com/images/search?url="+url+"&rpt=imageview"
        google_url = "https://www.google.com/searchbyimage?image_url="+url
        tinyEYE_url = "https://www.tineye.com/search/?url="+url
        imageOPS_url = "http://imgops.com/"+unparsed_url
        return (
            discord.Embed(title="Links de búsqueda:",
                          description="Aquí algunos links que te ayudarán a encontrar tu imagen. Suerte en tu búsqueda!", color=self.COLOR_BLUE)
            .add_field(name="Yandex:", value="Es muy probable que aquí logres encontrar lo que buscas [link]("+yandex_url+").", inline=False)
            .add_field(name="Google:", value="De vez en cuando Google te ayudará a encontrarlo [link]("+google_url+").", inline=True)
            .add_field(name="tinyEYE:", value="También puedes probar tu suerte con TinyEYE [link]("+tinyEYE_url+").", inline=True)
            .add_field(name="No lograste encontrarlo?", value="En esta página puedes encontrar otras páginas más que te pueden ayudar con tu búsqueda [link]("+imageOPS_url+").", inline=False)
            .add_field(name="Lograste encontrar la imagen?", value="Puedes ayudar a mejorar el bot enviando el nombre de la imagen con el comando:\n\n `e!id"\
                +str(idOfName)+"` *La imagen es del autor/anime...* \n\n[Si quieres también puedes adjuntar una imagen]", inline=True)
        )

    async def save_media_on_log(self, media=None, url=None, name="NONE.png",message=""):
        message = "eldoBOT backup plan :3 (just ignore this)\n"+message
        file_to_send="" # To combat the "possibly unbound" thingy
        if media!=None:
            file_to_send = discord.File(fp = BytesIO(media),filename=name)

        elif url!=None:
            response = requests.get(url)
            if response.ok:
                file_to_send = BytesIO(response.content)
                file_to_send = discord.File(fp = file_to_send,filename=name)
            else:
                print("Error! We couldn't get the image of the URL on function: save_media_on_log()")
                return "https://i.kym-cdn.com/photos/images/newsfeed/000/747/832/bb7.gif"

        message_sent = await self.channel_logs.send(file = file_to_send,content = message)
        return message_sent.attachments[0].url

    async def get_video_frame(self,attachment):
        with open("temp.mp4", 'wb') as video_file:
            video_file = await attachment.save(video_file)
        cam = cv2.VideoCapture("temp.mp4")
        ret,image_to_search = cam.read()
        #print(type(image_to_search),type(ret),type(cam),type(video_file))
        return image_to_search

    # Lee el tipo de reacción. Si es positiva (y viene de un miembro nivel +3), aceptalo y actualiza la DB
    # Si es negativa, busca con TraceMOE y pregunta de nuevo todo esto (eliminando la fallida)
    # Si es también negativa, ábrelo a los usuarios
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        list_of_messages = list(zip(*self.messages_to_react))
        if len(list_of_messages) == 0:
            return
        # Message Status (0=No action -1=video,no action 1=action,no video 2=delete)
        self.status_messages_to_react

        # URL of image
        list_of_image_URL = list_of_messages[2]

        # ID in DB
        list_of_DB_ids = list_of_messages[1]

        # Discord messages
        list_of_messages = list_of_messages[0]

        # IDs from the messages
        list_of_message_IDs = []

        for element in list_of_messages:
            list_of_message_IDs.append(str(element.id))

        def change_embed_dic(dictionary, confirmed, user_that_confirmed, idOfName=None):
            if confirmed:
                dictionary["color"] = self.COLOR_GREEN
                dictionary["title"] = "Confirmamos, nombre encontrado!"
                dictionary["footer"]["text"] = "Confirmado por " + \
                    user_that_confirmed + \
                    dictionary["footer"]["text"][dictionary["footer"]
                                                 ["text"].index('|')-1:]
            else:
                dictionary["color"] = self.COLOR_RED
                dictionary["title"] = "Mission failed, we'll get em next time"
                dictionary["description"] = "~~" + dictionary["description"] + \
                    "~~\n\nEsta respuesta fué marcada como incorrecta, pero puedes intentar buscarla por ti mism@ reaccionando al 🔎\n"
                dictionary["description"] += "Lograste encontrar la imágen? Puedes ayudar a mejorar el bot enviando el nombre de la imagen con el comando:\n"
                dictionary["description"] += "**e!id"+str(
                    idOfName)+"** *La imagen es del autor/anime...* \n[Si quieres también puedes adjuntar una imagen]"
                dictionary["footer"]["text"] = "Negado por " + user_that_confirmed + \
                    dictionary["footer"]["text"][dictionary["footer"]
                                                 ["text"].index('|')-1:]
            return discord.Embed.from_dict(dictionary)

        if str(payload.message_id) in list_of_message_IDs and payload.event_type == "REACTION_ADD":
            position_to_change = list_of_message_IDs.index(
                str(payload.message_id))
            actual_status = self.status_messages_to_react[position_to_change]
            if payload.user_id == 702233706240278579:  # eldoBOT
                return
            guild_of_reaction = self.bot.get_guild(payload.guild_id)
            author_of_reaction = await guild_of_reaction.fetch_member(payload.user_id)
            can_react = True  # Now everyone can react
            for rol in author_of_reaction.roles:  # Eww, Hardcoded :P (>=lvl 3)
                if(rol.id == 630560047872737320 or rol.name == "Godness" or payload.user_id == 597235650361688064):
                    can_react = True
            if not can_react:
                the_reactions = list_of_messages[position_to_change].reactions
                for reaction in the_reactions:
                    await reaction.remove(author_of_reaction)
                return

            if (author_of_reaction.nick == None):
                member_name = author_of_reaction.name
            else:
                member_name = author_of_reaction.nick
            if payload.emoji.name == "✅" and actual_status <= 0:
                print("Sending good news to DB")
                # Get User ID
                mySQL_query = "SELECT ID FROM "+self.DB_NAME + \
                    ".USER WHERE USER_ID="+str(author_of_reaction.id)+";"
                self.mycursor.execute(mySQL_query)
                tmp_user_DBid = self.mycursor.fetchall()
                if(self.mycursor.rowcount == 0):
                    tmp_user_DBid = self.addUserToDB(author_of_reaction)
                else:
                    tmp_user_DBid = tmp_user_DBid[0][0]

                # Update status of message
                mySQL_query = "UPDATE "+self.DB_NAME+".NAME_IMAGE SET FOUND=1, FOUND_BY_BOT=1, CONFIRMED_BY=%s \
                    WHERE ID="+str(list_of_DB_ids[position_to_change])+";"
                self.mycursor.execute(mySQL_query, (tmp_user_DBid,))
                self.mydb.commit()
                # Change status or remove message from list
                if(actual_status == -1):
                    self.messages_to_react.pop(position_to_change)
                    self.status_messages_to_react.pop(position_to_change)
                else:
                    self.status_messages_to_react[position_to_change] = 1
                # Show who confirmed to be true
                embed_message = list_of_messages[position_to_change].embeds[0]
                embed_message = change_embed_dic(
                    embed_message.to_dict(), True, member_name)
                await list_of_messages[position_to_change].edit(embed=embed_message)

            elif payload.emoji.name == "❌" and actual_status <= 0:
                print("Sending bad news to DB")
                # Get User ID
                mySQL_query = "SELECT ID FROM "+self.DB_NAME + \
                    ".USER WHERE USER_ID="+str(author_of_reaction.id)+";"
                self.mycursor.execute(mySQL_query)
                tmp_user_DBid = self.mycursor.fetchall()
                if(self.mycursor.rowcount == 0):
                    tmp_user_DBid = self.addUserToDB(author_of_reaction)
                else:
                    tmp_user_DBid = tmp_user_DBid[0][0]

                # Update status of message
                mySQL_query = "UPDATE "+self.DB_NAME+".NAME_IMAGE SET FOUND_BY_BOT=0, CONFIRMED_BY=%s \
                    WHERE ID="+str(list_of_DB_ids[position_to_change])+";"
                self.mycursor.execute(mySQL_query, (tmp_user_DBid,))
                self.mydb.commit()
                # Change status or remove message from list
                if(actual_status == -1):
                    self.messages_to_react.pop(position_to_change)
                    self.status_messages_to_react.pop(position_to_change)
                else:
                    self.status_messages_to_react[position_to_change] = 1
                # Show who confirmed to be true
                embed_message = list_of_messages[position_to_change].embeds[0]
                embed_message = change_embed_dic(
                    embed_message.to_dict(), False, member_name, list_of_DB_ids[position_to_change])
                await list_of_messages[position_to_change].edit(embed=embed_message)

            elif payload.emoji.name == "🎦" and actual_status >= 0:
                channel_of_reaction = guild_of_reaction.get_channel(
                    payload.channel_id)
                message_of_reaction = await channel_of_reaction.fetch_message(payload.message_id)
                embedded_msg_color = message_of_reaction.embeds[0].color.value

                print(embedded_msg_color)
                url_to_send = list_of_image_URL[position_to_change]
                if embedded_msg_color == self.COLOR_GREEN:
                    url_to_send = message_of_reaction.embeds[0].image.url
                    print(url_to_send)

                await self.debugTraceMoe(list_of_image_URL[position_to_change], message_of_reaction)
                # Change status or remove message from list
                if(actual_status == 1):
                    self.messages_to_react.pop(position_to_change)
                    self.status_messages_to_react.pop(position_to_change)
                else:
                    self.status_messages_to_react[position_to_change] = -1

            elif payload.emoji.name == "✖":
                channel_of_reaction = guild_of_reaction.get_channel(
                    payload.channel_id)
                message_of_reaction = await channel_of_reaction.fetch_message(payload.message_id)

            elif payload.emoji.name == "🔎":
                mySQL_query = "SELECT URL FROM "+self.DB_NAME + \
                    ".NAME_IMAGE WHERE ID=" + \
                    str(list_of_DB_ids[position_to_change])+";"
                self.mycursor.execute(mySQL_query)
                url_to_search = self.mycursor.fetchall()
                url_to_search = url_to_search[0][0]
                embedHelper = self.embedSearchHelper(
                    url_to_search, list_of_DB_ids[position_to_change])
                await list_of_messages[position_to_change].channel.send(embed=embedHelper, delete_after=1800)

    @commands.command(name = "name",
                    usage="Tienes que enviar una imágen/video anime junto a este comando. Funciona mejor con imagenes bien recortadas.",
                    description = "El bot te devolverá información dependiendo del tipo de imagen enviado.")
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def find_name(self, msg):
        # If there is no attachment, we ignore it
        if len(msg.attachments)==0:
            return 

        # Check if we can send names to this channel
        can_i_send_message = False
        if "name_channel" in self.configurations["guilds"][msg.guild.id]["commands"]:
            if self.configurations["guilds"][msg.guild.id]["commands"]["name_channel_set"] == True:
                if msg.channel.id in self.configurations["guilds"][msg.guild.id]["commands"]["name_channel"]:
                    can_i_send_message = True
                else:
                    can_i_send_message = False
            else: # If the user didn't configured the allowed channels, we will just send the command
                can_i_send_message = True
        else:
            can_i_send_message = True

        # If the user sent the command in a channel where we don't allow it, we inform him
        if can_i_send_message == False:
            #await msg.channel.send(content=configurations["guilds"][msg.guild.id]["commands"]["name_ignore_message"], delete_after=60)
            return

        async with msg.channel.typing():
            # Get image URL
            image_to_search_URL = msg.attachments[0].url
            emb_user = msg.author.name

        # If the image is a... video, then we get the first frame
        if msg.attachments[0].filename.find(".mp4")!=-1:
            image_to_search = await self.get_video_frame(msg.attachments[0])
            image_to_search = Image.fromarray(image_to_search, 'RGB')
        else:
            image_to_search = requests.get(image_to_search_URL)
            image_to_search = Image.open(BytesIO(image_to_search.content))
        print("Searching image: " + image_to_search_URL)

        image_to_search = image_to_search.convert('RGB')
        image_to_search.thumbnail((250,250), resample=Image.ANTIALIAS)
        imageData = BytesIO()
        image_to_search.save(imageData,format='PNG')
        text_ready = False

        # Check if it was already confirmed by a user
        hash_found = False
        mySQL_query = "SELECT HASH, FOUND, CONFIRMED_BY, FOUND_BY_BOT, ID FROM " + \
            self.DB_NAME+".NAME_IMAGE WHERE CONFIRMED_BY IS NOT NULL;"
        self.mycursor.execute(mySQL_query)
        sql_result = self.mycursor.fetchall()
        pil_image = Image.open(imageData)
        image_hash = imagehash.phash(pil_image,16)
        image_DB_id = None
        text_in_footer = ""
        for row in sql_result:
            received_hash = imagehash.hex_to_hash(row[0])
            if received_hash-image_hash < 40:
                image_DB_id = row[4]
                print("A Hash was found!")
                # If it was found, but not by the bot, it means that a user added a found
                # message, so we search for that data on the DB to show it
                if(row[3]==0 and row[1]==1): 
                    print("found, but not by the bot")
                    mySQL_query = "SELECT NAME_RESULT.USER_THAT_FOUND, NAME_RESULT.TEXT, NAME_RESULT.IMAGE_LINK, NAME_IMAGE.URL "
                    mySQL_query += "FROM eldoBOT_DB.NAME_IMAGE INNER JOIN (NAME_RESULT INNER JOIN NAME_LOG on "
                    mySQL_query += "NAME_RESULT.ID=NAME_LOG.NAME_ID) ON NAME_LOG.IMAGE_ID = NAME_IMAGE.ID "
                    mySQL_query += "WHERE NAME_IMAGE.ID = %s ORDER BY NAME_RESULT.DATE DESC;"
                    self.mycursor.execute(mySQL_query,(row[4],))
                    tmp_user_DBid = self.mycursor.fetchall()
                    # Small error handling. This should not happen
                    if self.mycursor.rowcount==0:
                        print("Huston, we have a problem with the HASH/USERMADE search")
                        continue
                    author_name = self.dbUserID_to_discordIDNameImage(tmp_user_DBid[0][0])
                    author_image= author_name[2]
                    author_name = author_name[1]
                    # If the user included an image together with his found message
                    if(tmp_user_DBid[0][2]!=None): 
                        embed_to_send = discord.Embed(description=tmp_user_DBid[0][1], color=1425173).set_author(
                            name=author_name, icon_url=author_image).set_thumbnail(url = tmp_user_DBid[0][3]).set_image(url = tmp_user_DBid[0][2])
                    # If not, we just show the found message together with the searched image
                    else:
                        embed_to_send = discord.Embed(description=tmp_user_DBid[0][1], color=1425173).set_author(
                            name=author_name, icon_url=author_image).set_thumbnail(url = tmp_user_DBid[0][3])
                    
                    await msg.channel.send(embed=embed_to_send)
                    return

                # If the image was found by the bot before, we show who confirmed or denied it
                elif(row[3]==1):
                    print("found by the bot before")
                    mySQL_query = "SELECT USERNAME FROM "+self.DB_NAME+".USER WHERE ID="+str(row[2])+";"
                    self.mycursor.execute(mySQL_query)
                    tmp_user_DBid = self.mycursor.fetchall()

                    hash_found = True
                    if(row[1]==1):
                        emb_embbed_tittle = "Nombre encontrado y confirmado"
                        text_in_footer = "Confirmado por " + tmp_user_DBid[0][0]
                        emb_color = 1425173
                    else:
                        emb_embbed_tittle = "Nombre no encontrado. Pero aquí una imagen parecida:"
                        text_in_footer = "Denegado por " + tmp_user_DBid[0][0]
                        emb_color = 15597568
                
                else:
                    print("Some strange things are happening with our DB")

        
        # Variables for the Embedded message:
        emb_similarity = ""
        emb_name = ""
        emb_episode = ""
        emb_character = ""
        emb_artist = ""
        emb_company = ""
        emb_game = ""
        emb_link = ""
        emb_preview = ""


        # Original URL (For future changes)
        # url = 'http://saucenao.com/search.php?output_type=2&numres=1&minsim='+minsim+'&dbmask='+str(db_bitmask)+'&api_key='+api_key
        url = 'http://saucenao.com/search.php?output_type=2&numres=3&minsim=85!&dbmask=79725015039&api_key='+self.sauceNAO_TOKEN
        files = {'file': ("image.png", imageData.getvalue())}
        r = requests.post(url, files=files)
        emb_index_saucenao = ""
        if r.status_code != 200:
            if r.status_code == 403:
                print('Incorrect or Invalid API Key! Please Edit Script to Configure...')
            else:
                #generally non 200 statuses are due to either overloaded servers or the user is out of searches
                print("status code: "+str(r.status_code))
                await msg.channel.send(content="Hey @Eldoprano#1758 ! Se que parece imposible, pero estos tipos acaba de agotar mi API de búsqueda :P")
                await msg.add_reaction("🕖")
        else:
            results = json.loads(r.text)
            result_data = results["results"][0]["data"]
            similarity_of_result = results["results"][0]["header"]["similarity"]
            if "thumbnail" in results["results"][0]["header"]:
                emb_preview = results["results"][0]["header"]["thumbnail"]

            emb_similarity = float(similarity_of_result)
            if(float(similarity_of_result)>58):
                emb_index_saucenao = results["results"][0]["header"]["index_name"]
                emb_index_saucenao = emb_index_saucenao[emb_index_saucenao.find(":")+1:emb_index_saucenao.find(" - ")]
                if "pixiv_id" in result_data:
                    emb_artist = result_data["member_name"]
                    if requests.get(result_data["ext_urls"][0]).status_code != 404:
                        emb_link =  result_data["ext_urls"][0]
                elif "nijie_id" in result_data:
                    emb_name = result_data["title"]
                    emb_artist = result_data["member_name"]
                    emb_link = result_data["ext_urls"][0]
                elif "source" in result_data and not text_ready:
                    if "part" in result_data:
                        emb_name = result_data["source"]
                        emb_episode = result_data["part"]
                    elif result_data["source"].find("twitter.com")!=-1:
                        emb_artist = result_data["creator"]
                        if "material" in result_data:
                            emb_name = result_data["material"]
                        if requests.get(result_data["source"]).status_code != 404:
                            emb_link = result_data["source"]
                        else:
                            emb_link = "**Link del Twitt original caído**"

                    elif "sankaku_id" in result_data or "gelbooru_id" in result_data or "konachan_id" in result_data:
                        if "creator" in result_data:
                            if result_data["creator"] == "":
                                if result_data["material"] != "":
                                    emb_name = result_data["material"][0:result_data["material"].find(",")]
                                    if result_data["characters"] != "":
                                        emb_character = result_data["characters"]

                        if "material" in result_data and not text_ready:
                            if result_data["material"]=="original":
                                if "characters" in result_data:
                                    if result_data["characters"]!="":
                                        emb_character = result_data["characters"]
                            elif result_data["material"]!="":
                                emb_name = result_data["material"]
                        if(result_data["creator"]!=""):
                            emb_artist = result_data["creator"]
                if "getchu_id" in result_data:
                    emb_company = result_data["company"]
                    emb_game = result_data["title"]

                # Rellena datos que no fueron llenados
                if emb_name == "":
                    try: 
                        if "title_english" in result_data:
                            emb_name = result_data["title_english"]
                        emb_name = result_data["title"]
                    except Exception as e: print(e)
                if emb_artist == "":
                    try: 
                        if type(result_data["creator"])==type([]):
                            for artist in result_data["creator"]:
                                emb_artist += artist+", "
                            emb_artist = emb_artist[:-2]
                        else:
                            emb_artist = result_data["creator"]
                    except Exception as e: print(e)
                if emb_character == "":
                    try: emb_character = result_data["characters"]
                    except Exception as e: print(e)
                if emb_link == "":
                    try: 
                        if "mal_id" in result_data:
                            emb_link = "https://myanimelist.net/anime/" + \
                        result_data["mal_id"]
                        elif type(result_data["ext_urls"])==type([]):
                            emb_link = result_data["ext_urls"][0]
                        else:
                            emb_link = result_data["ext_urls"]
                    except Exception as e: print(e)
                if emb_link == "":
                    try: 
                        if type(result_data["ext_urls"])==type([]):
                            emb_link = result_data["ext_urls"][0]
                        else:
                            emb_link = result_data["ext_urls"]
                    except Exception as e: print(e)
                if emb_name == "":
                    try: emb_name = result_data["eng_name"]
                    except Exception as e: print(e)
                if emb_episode == "" and "episode" in result_data:
                    emb_episode = result_data["episode"]

            embed_sent = None
            bot_failed_this_time = False
            # Aquí ya deberíamos de tener todos los datos, así que empezamos a crear el mensaje
            if emb_name != "" or emb_artist != "" or emb_link != "":
                emb_description = ""
                if(emb_name != ""):
                    emb_description += "**Nombre: ** "+str(emb_name)+"\n"
                if(emb_episode != ""):
                    emb_description += "**Episodio: ** "+str(emb_episode)+"\n"
                if(emb_character != ""):
                    emb_description += "**Personaje: ** "+str(emb_character)+"\n"
                if(emb_artist != ""):
                    emb_description += "**Artista: ** "+str(emb_artist)+"\n"
                if(emb_company != ""):
                    emb_description += "**Compañía: ** "+str(emb_company)+"\n"
                if(emb_game != ""):
                    emb_description += "**Juego: ** "+str(emb_game)+"\n"
                if(emb_link != ""):
                    emb_description += "**Link: ** "+str(emb_link)+"\n"

                emb_description += "**Encontrado en: **"+emb_index_saucenao+"\n"

                if not hash_found:
                    if emb_similarity > 89:
                        emb_color = 1425173  # A nice green
                        emb_embbed_tittle = "Nombre encontrado!"
                    elif emb_similarity > 73:
                        emb_color = 16776960 # An insecure yellow
                        emb_embbed_tittle = "Nombre quizás encontrado!"
                    else:
                        emb_color = 15597568 # A worrying red
                        emb_embbed_tittle = "Nombre probablemente encontrado!"

                    text_in_footer = "Porcentaje de seguridad: " + str(emb_similarity)+ "% | Pedido por: "+ emb_user
                else:
                    text_in_footer += " | Pedido por: "+ emb_user
                

                # Create Webhook
                embed_to_send = discord.Embed(description=emb_description, colour=emb_color, title=emb_embbed_tittle).set_footer(text=text_in_footer)
                if emb_preview != "":
                    emb_preview_file = requests.get(emb_preview)
                    if emb_preview_file.status_code == 200:
                        tmp_msg_image_url = await self.save_media_on_log(media = emb_preview_file.content,name="eldoBOT_temp_preview_File.png",message=emb_description)
                        embed_to_send.set_image(url=tmp_msg_image_url)
                # Send message
                print("Sending message to channel")
                embed_sent = await msg.channel.send(embed=embed_to_send)

                # Save user sended Image to our log channel
                emb_preview_file = await msg.attachments[0].read()
                tmp_msg_image_url = await self.save_media_on_log(media = emb_preview_file,name="eldoBOT_temp_File.png",message="Esta es una imagen que un usuario buscó")
                image_to_search_URL = tmp_msg_image_url

                # También una reacción para buscar con TraceMOE, si es que si funcionó, pero el usuario quiere video
                if not hash_found:
                    await embed_sent.add_reaction("✅")
                    await embed_sent.add_reaction("❌")
                await embed_sent.add_reaction("🎦")
                await embed_sent.add_reaction("🔎")

            else:  
                bot_failed_this_time = True
                if float(similarity_of_result)>75:
                    with open('log.ignore', 'a') as writer:
                        writer.write("\n---------- NOT FOUND "+datetime.today().strftime("%d/%m/%Y %H:%M:%S")+"-------------\n")
                        writer.write(str(results))
                        writer.write(str(result_data))
                    await msg.add_reaction("➖")
                else:
                    emb_preview_file = await msg.attachments[0].read()
                    tmp_msg_image_url = await self.save_media_on_log(media = emb_preview_file,name="eldoBOT_ha_fallado.png",message="Este es una imagen que fallamos en encontrar con el bot")
                    image_to_search_URL = tmp_msg_image_url
                    # We send the webhook after we add the image to the DB
                

            if not hash_found:
                pil_image = Image.open(imageData)
                image_hash = str(imagehash.phash(pil_image,16))
                pil_image.save("temp_images/"+image_hash+".png")

                with open("out.txt", "wb") as outfile:
                    # Copy the BytesIO stream to the output file
                    outfile.write(imageData.getbuffer())
                imageData.close()


            mySQL_query = "SELECT ID FROM "+self.DB_NAME+".USER WHERE USER_ID="+str(msg.author.id)+";"
            self.mycursor.execute(mySQL_query)
            tmp_user_DBid = self.mycursor.fetchall()
            if(self.mycursor.rowcount==0):
                tmp_user_DBid = self.addUserToDB(msg.author)
            else:
                tmp_user_DBid = tmp_user_DBid[0][0]
            
            if not hash_found:
                print("hash wasn't found apparently")
                mySQL_query = "SELECT ID FROM "+self.DB_NAME+".GUILD WHERE GUILD_ID="+str(msg.guild.id)+";"
                self.mycursor.execute(mySQL_query)
                tmp_guild_DBid = self.mycursor.fetchall()[0][0]

                mySQL_query = "INSERT INTO "+self.DB_NAME+".NAME_IMAGE (HASH, URL, FILE_NAME, EXTENSION, GUILD_THAT_ASKED, USER_THAT_ASKED) VALUES (%s, %s, %s, %s, %s, %s) "
                try:
                    self.mycursor.execute(mySQL_query, (image_hash, str(image_to_search_URL),"HASH.png", "png", tmp_guild_DBid, tmp_user_DBid))
                    self.mydb.commit()
                except Exception as e:
                    print(e)

                global messages_to_react
                global status_messages_to_react

                image_DB_id = self.mycursor.lastrowid

                # Send the message that we failed to find the name, together with
                # the image ID as footer. We moved it here to get the DB ID
                if bot_failed_this_time:
                    embed_sent = await self.send_msg_as(user_to_imitate=msg.author,\
                        channel=msg.channel,content=msg.clean_content,
                        embed=True, media=tmp_msg_image_url, 
                        footer_msg="Nombre no encontrado... | e!id"+str(image_DB_id))

                    await embed_sent.add_reaction("✖")
                    await embed_sent.add_reaction("🔎")
                    await msg.delete()

            if image_DB_id!=None:            
                # Change this if you want to read reactions from failed searches (TODO)
                self.messages_to_react.append([embed_sent,image_DB_id,tmp_msg_image_url])
                self.status_messages_to_react.append(0)

                if len(self.messages_to_react)>50:
                    self.messages_to_react.pop(0)
                    self.status_messages_to_react.pop(0)




    @commands.Cog.listener()
    async def on_message(self,message):
        if message.content.lower().find("name") != -1:
            await self.find_name(message)

def setup(bot):
    bot.add_cog(SearchCog(bot))
