import discord
from discord.ext import commands


class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        await ctx.send("Это тестовая команда пустого кога!")


async def setup(bot):
    await bot.add_cog(TestCog(bot))
