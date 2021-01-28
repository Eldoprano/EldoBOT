import discord
from discord.ext import commands

from io import BytesIO
import re

class InstantChanges(commands.Cog, name="Cambios rápidos", description="Comandos pensados para mejorar el ecosistema en el servidor"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name = "spoiler",
                      usage="Envía una imagen o video junto a este comando.",
                    description = "Marca la imágen o el video enviado como spoiler.")
    @commands.guild_only()
    async def command_spoiler(self, msg):
        if len(msg.attachments)>0:
            tmp_list_images=[]
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
            # Delete webhook
            await webhook_discord.delete()
            await msg.delete()
    
    async def replace_user_text(self, msg, text="", replaced="", times=0):
        msg_to_say = msg.content
        tmp_channel = msg.channel
        tmp_author = msg.author.display_name
        pfp_to_imitate = await msg.author.avatar_url.read()

        if len(msg.attachments) > 0:
            tmp_list_images = []
            for attachment in msg.attachments:
                tmp_img_bytes = await attachment.read()
                tmp_img_filename = attachment.filename
                tmp_img_bytes = BytesIO(tmp_img_bytes)
                tmp_img = discord.File(
                    tmp_img_bytes, filename=tmp_img_filename)
                tmp_list_images.append(tmp_img)

        await msg.delete()

        reemplazador = re.compile(re.escape(text), re.IGNORECASE)
        msg_to_say = reemplazador.sub(replaced, msg_to_say, times)

        webhook_discord = await tmp_channel.create_webhook(name=tmp_author, avatar=pfp_to_imitate, reason="EldoBOT: Temp-webhook")
        if len(msg.attachments) > 0:
            # , allowed_mentions = allowed_mentions_NONE)
            await webhook_discord.send(content=msg_to_say, files=tmp_list_images, username=tmp_author)
        else:
            # , allowed_mentions = allowed_mentions_NONE)
            await webhook_discord.send(content=msg_to_say, username=tmp_author)
        # Delete webhook
        await webhook_discord.delete()


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        if message.content.lower().find("spoiler") != -1:
            await self.command_spoiler(message)
        if message.content.lower().find(":v") != -1:
            await self.replace_user_text(message, ":v", "Soy subnormal")
        if message.content.lower().find("v:") != -1:
            await self.replace_user_text(message, "v:", "Soy subnormal")

def setup(bot):
    bot.add_cog(InstantChanges(bot))
