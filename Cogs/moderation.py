import discord
from discord.ext import commands

import mysql.connector
import pickle
import re
from bs4 import BeautifulSoup
import requests



class Moderation(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):

        # Get some secrets from the magic Pickle
        keys = pickle.load(open("keys.pkl", "rb"))
        DB_NAME = keys["Database"]["database"]

        ## Connect to Database
        self.mydb = mysql.connector.connect(
            host=keys["Database"]["host"],
            user=keys["Database"]["user"],
            passwd=keys["Database"]["passwd"],
            database=keys["Database"]["database"])
        self.mycursor = self.mydb.cursor()
        # Load configurations from DB
        mySQL_query = "SELECT g.GUILD_ID, TAG FROM "+DB_NAME+".FORBIDDEN_TAGS f inner join  " + \
            DB_NAME+".GUILD g on f.GUILD_ID=g.id;"
        self.mycursor.execute(mySQL_query)
        self.forbidden_tags = self.mycursor.fetchall()

        DM_CHANNEL = 647898356311654447
        self.channel_logs = await self.bot.fetch_channel(DM_CHANNEL)


    def urlExtractor(self, text):
        # findall() has been used
        # with valid conditions for urls in text
        found_in = text.find(".")
        if len(text) > 10 and (found_in < len(text)-1 and found_in != -1):
            regex = r"(?i)\b((?:https?:\/\/|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}\/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
            url = re.findall(regex, text)
            return [x[0] for x in url]
        return ""

    # Handle forbidden nHentai links
    def link_forbidden_tag_search(self, urls, guildID):
        forbidden_detected = ""
        bad_url = ""
        replacement_text = ""
        forbidden_tag_list = [tag[1]
                              for tag in self.forbidden_tags if tag[0] == str(guildID)]
        for url in urls:
            # Check for nHentai
            if(url.find("nhentai.net/g/") != -1):
                if(url.find("http") == -1):
                    url = "https://" + url
                page = requests.get(url)
                if(page.status_code == 200):
                    soup = BeautifulSoup(page.content, 'html.parser')
                    tags = soup.find(id="tags")
                    for tag_type in list(tags.children):
                        if(tag_type.contents[0].lower().find("tags") != -1):
                            # Here we get all the tags
                            for tag in tag_type.findAll("span", class_='name'):
                                if(tag.getText().lower() in forbidden_tag_list):
                                    forbidden_detected += tag.getText()+" "
                                    bad_url = url
                            if forbidden_detected != "":
                                replacement_text = "#" + \
                                    re.findall(r'\d+', url)[0]
                else:
                    print("We couldn't open the Link: ", url)

            # Check for HitomiLa
            elif(url.find("hitomi.la/") != -1):
                url_copy = url  # Save a copy to send it at the end
                # This URL has an URL that redirects us the one we want :P
                if(url.find("https://hitomi.la/reader/") != -1):
                    redirect_url_code = re.findall(r'\d+', url)[0]
                    url = "https://hitomi.la/galleries/"+redirect_url_code+".html"

                # If the user is strange enough to give us this as URL.
                #  It also handles the above generated url.
                #  It ultimately redirects to the Doujinshi site that has the tags on it
                if(url.find("https://hitomi.la/galleries/") != -1):
                    page = requests.get(url)
                    if(page.status_code == 200):
                        soup = BeautifulSoup(page.content, 'html.parser')
                        tags = soup.find('a', href=True)
                        url = tags['href']
                    else:
                        print("We couldn't open the redirected link: ", url)

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
                                if(tag.getText().lower() == forbidden_tag):
                                    forbidden_detected += tag.getText()+" "
                                    bad_url = url
                        if forbidden_detected != "":
                            replacement_text = soup.select(
                                "body > div.container > div.content > div.gallery.dj-gallery > h1 > a")[0].getText()
                    else:
                        print("We couldn't open the Link: ", url)
                bad_url = url_copy  # Restore copy. We do this, so we send the correct url to replace

        if forbidden_detected != "":
            return [forbidden_detected, bad_url, replacement_text]
        else:
            return None

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
        
        # Delete webhook
        await webhook_discord.delete()
        return sent_message

    async def tgfDoujinshi(self, msg):
        urls = self.urlExtractor(msg.content)
        if(len(urls) > 0):
            forbiddenTags_url = self.link_forbidden_tag_search(urls, msg.guild.id)
            if (forbiddenTags_url != None):
                forbiddenCode = forbiddenTags_url[2]
                content = msg.content.replace(
                    forbiddenTags_url[1], "`"+forbiddenCode+"`")
                content += "\n\nEste link fué reducido porque detectamos el/los siguientes tags:\n`" + \
                    forbiddenTags_url[0]+"`"

                await self.send_msg_as(user_to_imitate=msg.author, channel=msg.channel, content=content)
                await msg.delete()
        
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages comming from a bot
        if message.author.bot:
            # If the bot is nHitomi, then look for forbidden tags
            if message.author.id == 515386276543725568:
                collected_forbidden_tags = ""
                forbidden_tag_list = [
                    tag[1] for tag in self.forbidden_tags if tag[0] == str(message.guild.id)]
                for embed in message.embeds:
                    for field in embed.fields:
                        if field.name.find("Tag") != -1:
                            for tag in forbidden_tag_list:
                                if field.value.find(tag) != -1:
                                    collected_forbidden_tags += tag + ", "
                if collected_forbidden_tags != "":
                    content = "La respuesta del bot fué eliminada porque detectamos el/los siguientes tags:\n`" + \
                        collected_forbidden_tags[:-2]+"`"
                    await message.channel.send(content=content, delete_after=10)
                    await message.delete()
            return
        if isinstance(message.channel, discord.DMChannel):
            if message.attachments:
                url_list = "\n"
                for attachment in message.attachments:
                    url_list += attachment.url + "\n"
                await self.channel_logs.send(content="Enviado por: **"+message.author.name+"**\n"+message.content+url_list)
            else:
                await self.channel_logs.send(content="Enviado por: **"+message.author.name+"**\n"+message.content)

        await self.tgfDoujinshi(message)


def setup(bot):
    bot.add_cog(Moderation(bot))
