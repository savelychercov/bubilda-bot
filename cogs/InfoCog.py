import discord
import requests
from discord.ext import commands
from library.graphics import SearchContent
from library import logger
from bs4 import BeautifulSoup as bs
from fake_useragent import UserAgent
from random import randint as rnd

url = {"daily": "https://74.ru/horoscope/daily/", "tomorrow": "https://74.ru/horoscope/tomorrow/"}
url_holidays = "https://calend.online/holiday/"
user_agent = UserAgent().random


def gethoro(day="daily"):
    preds = {}
    headers = {"User-Agent": user_agent}
    r = requests.get(url[day], headers=headers)
    soup = bs(r.text, 'html.parser')
    for s in soup.select(".IjM3t"):
        for ln in s.select(".IGRa5"):
            sign = str(ln.select("h3")[0].text)
            pred = str(ln.select("div")[1].text)
            preds[sign.lower()] = pred
    return preds


class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Инфа из интернета"
        self.__cog_description__ = "Ищет информацию за вас"
        self.bot = bot

    """
    @commands.command(name="horo", aliases=["гороскоп", "horoscope", "г"], brief="Гороскоп - horo *(знак) *(завтра)")
    async def horoscope(self, ctx, *, arg="none"):
        try:
            embtitle = ""
            arg = str(arg).lower()
            if arg == "none" or arg.find("завтра") == -1:
                preds = gethoro("daily")
                embtitle = "Гороскоп на сегодня"
            else:
                preds = gethoro("tomorrow")
                arg = arg.replace("завтра", "").strip()
                embtitle = "Гороскоп на завтра"

            if arg and arg != "none":
                try:
                    localpred = preds[arg]
                    preds = {}
                    preds[arg] = localpred
                except:
                    await ctx.send(searchcontent.getgif(arg))
                    return

            embed = discord.Embed(title=embtitle, color=0x109319)
            embed.set_author(name="Bubilda Predictor",
                             icon_url="https://cdn.discordapp.com/attachments/1050725563561676840/1053651366314246164/bub.jpg")
            for key in preds:
                embed.add_field(name=str(key).upper(), value=preds[key], inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            logger.err(e)
    """

    @commands.command(name="today", aliases=["holidays", "holi", "day"], brief="Показать сегодняшние праздники")
    async def day(self, ctx):

        r = requests.get(url_holidays)
        soup = bs(r.text, 'html.parser')
        holidays = ""
        for sel in soup.select(".holidays-list > li"):
            holidays = holidays + "**• " + sel.text.strip() + "**\n"

        embed = discord.Embed(
            title="ПРАЗДНИКИ СЕГОДНЯ:",
            color=discord.Colour.yellow(),
            description=holidays
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(InfoCog(bot))

if __name__ == "__main__":
    print(gethoro())
