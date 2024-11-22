import discord
from discord.ext import commands
import library.wb_lib as wb


class WbCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    """
    spreadsheet_data.json:
    {
        "token": ...,
        "spreadsheet_url": ...,
        "worksheet": ...
    }
    """

    @commands.command(brief="Тестовая команда (dev)")
    async def test(self, ctx):
        await ctx.send("Это тестовая команда пустого кога!")


async def setup(bot):
    await bot.add_cog(WbCog(bot))
