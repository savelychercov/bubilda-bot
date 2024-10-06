import discord
from discord.ext import commands
from library.gpt import *

class AiCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief = "Генерация кода по запросу")
    async def code(self, ctx, *, arg = None):
        if arg:
            async with ctx.typing():
                await ctx.send(generate_code(arg))
        else:
            await ctx.send("Напишите запрос в команде")

    @commands.command(brief = "Написать работу, (опишите запрос точно)")
    async def essay(self, ctx, *, arg = None):
        if arg:
            msg = await ctx.send("Уже сочиняю")
            async with ctx.typing():
                await msg.edit(content = generate_text(arg))
        else:
            await ctx.send("Напишите запрос в команде")
        
async def setup(bot):
   await bot.add_cog(AiCog(bot))