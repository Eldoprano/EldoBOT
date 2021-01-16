import discord
from discord.ext import commands

import hashlib
import time
import pickle
import re

class CogName(commands.Cog, name="Confesion", description="Comandos para mensajes anónimos"):
    def __init__(self, bot):
        self.bot = bot
        self.PICKLE_OF_ANONS = "anon_list.pkl"
        self.ANON_DEFAULT_PFP = "https://media.discordapp.net/attachments/647898356311654447/706938410098622555/unknown.png"

        try:
            self.anon_list = pickle.load(open(self.PICKLE_OF_ANONS, "rb"))
            print("Pickle file loaded")
        except Exception as e:
            print(e)
            print("Error, couldn't load Pickle File")
            self.anon_list = {}

        self.LOG_CHANNEL = 708648213774598164

    @commands.Cog.listener()
    async def on_ready(self):
        self.channel_logs = await self.bot.fetch_channel(self.LOG_CHANNEL)

    @commands.command(name="reset",
                      aliases=["resetear"],
                      usage="",
                      description="Resetea el apodo y la foto de tu perfil anónimo")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def command_anon_reset(self, ctx):
        msg = ctx.message
        tmp_user_id = msg.author.id
        if tmp_user_id in self.anon_list:
            del self.anon_list[tmp_user_id]
        await msg.channel.send(content="Tu perfil anónimo fué reseteado correctamente", delete_after=2.5)
        await msg.delete()
        with open(self.PICKLE_OF_ANONS, 'wb') as pickle_file:
            pickle.dump(self.anon_list, pickle_file)

    @commands.command(name="apodo",
                      aliases=["nick"],
                      usage=" <nuevo apodo>",
                      description="Cambia el apodo de tu perfil anónimo")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def command_anon_apodo(self, ctx):
        msg = ctx.message
        tmp_msg = msg.content
        tmp_channel = msg.channel
        tmp_user_id = msg.author.id
        tmp_guild_id = msg.guild.id
        await msg.delete()

        tmp_apodo = tmp_msg.replace("e!apodo ", "", 1)
        if tmp_apodo == "":
            await msg.channel.send(content="Tienes que escribit tu apodo después del comando **e!apodo **", delete_after=3)
        elif tmp_user_id in self.anon_list:
            self.anon_list[tmp_user_id]["apodo"] = tmp_apodo
            await msg.channel.send(content="Apodo cambiado correctamente", delete_after=2)
        else:
            self.anon_list[tmp_user_id] = {
                "apodo": tmp_apodo, "foto": self.ANON_DEFAULT_PFP, "guild": tmp_guild_id}
            await msg.channel.send(content="Apodo cambiado correctamente", delete_after=2)

        with open(self.PICKLE_OF_ANONS, 'wb') as pickle_file:
            pickle.dump(self.anon_list, pickle_file)

    @commands.command(name="foto",
                        aliases=["photo", "pfp"],
                        usage=" + Una foto adjunta",
                        description="Cambia la foto de tu perfil anónimo")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def command_anon_photo(self, ctx):
        msg = ctx.message
        tmp_user_id = msg.author.id
        tmp_guild_id = msg.guild.id

        if len(msg.attachments) > 0:
            attachment_file = await msg.attachments[0].to_file()
            tmp_msg = await self.channel_logs.send(content="Usuario: "+str(msg.author), file=attachment_file)
            tmp_msg_image_url = tmp_msg.attachments[0].url
            await msg.channel.send(content="Foto cambiada correctamente", delete_after=1.5)

        else:
            tmp_msg_image_url = self.ANON_DEFAULT_PFP
            await msg.channel.send(content="Tienes que adjuntar una foto junto al comando e!foto", delete_after=3)

        await msg.delete()

        if tmp_user_id in self.anon_list:
            self.anon_list[tmp_user_id]["foto"] = tmp_msg_image_url
        else:
            self.anon_list[tmp_user_id] = {
                "apodo": "Usuario Anónimo", "foto": tmp_msg_image_url, "guild": tmp_guild_id}

        with open(self.PICKLE_OF_ANONS, 'wb') as pickle_file:
            pickle.dump(self.anon_list, pickle_file)

    @commands.command(name = "anon",
                    aliases=["confess", "confesar", "confesion"],
                    usage=" <Mensaje anónimo que quieres enviar (Sin los < >)>",
                    description = "Envía un mensaje bajo un pseudónimo, el cuál cambia cada ~10 días")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def command_anon(self, ctx, *, arg):
        msg_to_say = arg
        tmp_channel = ctx.message.channel
        tmp_user_id = ctx.message.author.id
        tmp_user_nick = ctx.message.author.display_name  # To calculate our weekly HASH
        await ctx.message.delete()

        # Add a number that changes every ~10 days at the end, to vary the hash
        # Use nickname so user can vary his hash by just changing it's nickname
        # Hash it with md5 and get 4 first digits. I don't really care about colisions :P
        str_to_hash = tmp_user_nick + str(tmp_user_id) + \
            str(hex(int(time.time())))[2:-5]
        hash_adition = hashlib.md5(
            str_to_hash.encode('utf-8')).hexdigest()[:4].upper()

        if tmp_user_id in self.anon_list:
            tmp_avatar = self.anon_list[tmp_user_id]["foto"]
            tmp_author = self.anon_list[tmp_user_id]["apodo"]
        else:
            tmp_avatar = self.ANON_DEFAULT_PFP
            tmp_author = "Usuario Anónimo #" + hash_adition

        webhook_discord = await tmp_channel.create_webhook(name=tmp_author, reason="EldoBOT: Temp-webhook Usuario-anónimo")
        await webhook_discord.send(content=msg_to_say, username=tmp_author, avatar_url=tmp_avatar, allowed_mentions=None)
        
        # Delete webhook
        await webhook_discord.delete()
        print("Confesión hecha!")

    async def send_msg_as(user_to_imitate,channel,content,embed=False,user_that_sent=None,footer_msg=None,media=None):
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
        await webhook_discord.delete()
        return sent_message



    @commands.command(name="imita",
                      usage=" <menciona al usuario a imitar>",
                      description="Envía un mensaje imitando al usuario mencionado")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.member)
    async def command_say_like(self, ctx):
        msg = ctx.message
        msg_to_say = msg.clean_content
        tmp_content = msg.content
        tmp_channel = msg.channel
        tmp_author = msg.author
        user_to_imitate = msg.mentions[0]

        # Delete message
        await msg.delete()

        print(msg_to_say)
        if(tmp_content[2:].lower().find("imita id") == 0):
            user_ID_to_imitate = re.findall('<(.*?)>', tmp_content)[0]
            msg_to_say = msg_to_say.replace("<"+user_ID_to_imitate+">", "")
            msg_to_say = msg_to_say[2:].replace("imita id", "")
            #msg_to_say = tmp_clean_msg[tmp_clean_msg.find(msg_to_say[2:4]):] # Ohtia! Que es esto?? Pos... no hace falta entenderlo :P
        else:
            msg_to_say = msg_to_say[2:].replace("imita", "", 1)
            msg_to_say = msg_to_say.replace("@"+user_to_imitate.nick, "", 1)
            #msg_to_say = tmp_clean_msg[tmp_clean_msg.find(msg_to_say[2:4]):] # WTF, porque?? Shhh

        if(user_to_imitate != None):
            await self.send_msg_as(user_to_imitate=user_to_imitate, channel=tmp_channel, content=msg_to_say, embed=True, user_that_sent=tmp_author)
        else:
            print("User: "+user_ID_to_imitate+" not found")




def setup(bot):
    bot.add_cog(CogName(bot))
