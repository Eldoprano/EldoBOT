import discord
from discord.ext import commands
from random import randint

class HelpCog(commands.Cog, name="help command"):
	def __init__(self, bot):
		self.bot = bot
  

	@commands.command(name = 'help',
					usage="(commandName)",
					description = "Display the help message.")
	@commands.cooldown(1, 2, commands.BucketType.member)
	async def help (self, ctx, commandName=None):

		commandName2 = None
		stop = False

		if commandName is not None:
			for i in self.bot.commands:
				if i.name == commandName.lower():
					commandName2 = i
					break 
				else:
					for j in i.aliases:
						if j == commandName.lower():
							commandName2 = i
							stop = True
							break
						if stop is True:
							break 

			if commandName2 is None:
				await ctx.channel.send("No command found!")   
			else:
				embed = discord.Embed(title=f"**{commandName2.name.upper()} COMANDO :**", description="", color=randint(0, 0xffffff))
				embed.set_thumbnail(url=f'{self.bot.user.avatar_url}')
				embed.add_field(name=f"**NOMBRE :**", value=f"{commandName2.name}", inline=False)
				aliases = ""
			if len(commandName2.aliases) > 0:
				for aliase in commandName2.aliases:
					aliases = aliase
			else:
				commandName2.aliases = None
				aliases = None
				embed.add_field(name=f"**ALIAS :**", value=f"{aliases}", inline=False)
				if commandName2.usage is None:
					commandName2.usage = ""
				embed.add_field(name=f"**USO :**", value=f"{self.bot.command_prefix}{commandName2.name} {commandName2.usage}", inline=False)
				embed.add_field(name=f"**DESCRIPCION :**", value=f"{commandName2.description}", inline=False)
				await ctx.channel.send(embed=embed)             
		else:
			embed = discord.Embed(title=f"__**Comandos de {self.bot.user.name}**__", description=f"**{self.bot.command_prefix}help (comando)** : Muestra el cuadro de ayuda de un comando en específico.", color=randint(0, 0xffffff))
			embed.set_thumbnail(url=f'{self.bot.user.avatar_url}')
			embed.add_field(name=f"__COMANDOS :__", value=f"**{self.bot.command_prefix}buscar** : Devuelve el nombre del anime enviado. Solo funciona con screenshots de anime/H.", inline=False)
			await ctx.channel.send(embed=embed)

def setup(bot):
	bot.remove_command("help")
	bot.add_cog(HelpCog(bot))