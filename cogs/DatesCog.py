import discord
from datetime import datetime
from discord.ext import commands
from memoryV1.files_db import DatesData as d


class DatesCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Даты"
        self.__cog_description__ = "Команды чтобы считать дни до определенной даты"
        self.bot = bot

    @commands.group(invoke_without_command=True, brief="Узнать сколько времени осталось",
                    aliases=["отсчет", "отсчёт", "о", "dt"])
    async def dates(self, ctx):
        date_list = d.get_dates(str(ctx.guild.id))
        if not date_list:
            await ctx.send(embed=discord.Embed(title="Список дат пуст!", color=discord.Colour.green(),
                                               description="Используйте b.dates new"))
            return
        today = datetime.today()

        text = ""
        for name in date_list:
            end_date = datetime.strptime(date_list[name], "%Y-%m-%d")
            days_left = (end_date - today).days + 1
            if days_left > 0:
                text += f'**• {name.title()} ({date_list[name]}) через {days_left} дней**\n'
            elif days_left < 0:
                text += f'**• {name.title()} ({date_list[name]}) было {abs(days_left)} дней назад**\n'
            else:
                text += f'**• {name.title()} ({date_list[name]}) сегодня!**\n'

        embed = discord.Embed(
            title="**Текущие отсчеты дней:**",
            color=discord.Colour.green(),
            description=text)
        await ctx.send(embed=embed)

    @dates.command(brief="Добавить дату", aliases=["n"])
    async def new(self, ctx, date, *, name):
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except:
            await ctx.send("Неправильно указана дата, пример: 1939-09-01 Др Юи")
            return
        if not name.strip():
            await ctx.send("Неправильно указано название, пример: 1939-09-01 Др Юи")
            return
        d.new_date(str(ctx.guild.id), date, name.strip())
        await ctx.send("Записано!")

    @dates.command(brief="Удалить дату", aliases=["del", "rm"])
    async def delete(self, ctx, name):
        if d.del_date(str(ctx.guild.id), name):
            await ctx.send("Удалено")
        else:
            await ctx.senf("Нет такова")


async def setup(bot):
    await bot.add_cog(DatesCog(bot))
