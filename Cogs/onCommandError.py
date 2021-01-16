import discord
from discord.ext import commands
from discord.ext.commands import MissingPermissions, CheckFailure, CommandNotFound
import time


class OnCommandErrorCog(commands.Cog, name="on command error", command_attrs=dict(hidden=True)):
	def __init__(self, bot):
		self.bot = bot
        
	@commands.Cog.listener()
	async def on_command_error(self, ctx, error):
		if isinstance(error, commands.CommandOnCooldown):
			day = round(error.retry_after/86400)
			hour = round(error.retry_after/3600)
			minute = round(error.retry_after/60)
			if day > 0:
				await ctx.send(content = 'Espera '+str(day)+ " día(s) más para usar nuevamente este comando.", delete_after=10)
			elif hour > 0:
				await ctx.send(content = 'Espera '+str(hour)+ " hora(s) más para usar nuevamente este comando.", delete_after=10)
			elif minute > 0:
				await ctx.send(content = 'Espera '+ str(minute)+" minuto(s) más para usar nuevamente este comando.", delete_after=10)
			else:
				await ctx.send(content = f'Espera {error.retry_after:.2f} segundo(s) más para usar nuevamente este comando.', delete_after=10)
		elif isinstance(error, CommandNotFound):
			return
		elif isinstance(error, MissingPermissions):
 			await ctx.send(error.text)
		elif isinstance(error, CheckFailure):
			await ctx.send(error.original.text)
		else:
			print(error) 

def setup(bot):
	bot.add_cog(OnCommandErrorCog(bot))
