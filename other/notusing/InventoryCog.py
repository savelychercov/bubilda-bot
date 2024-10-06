import discord
from discord.ext import commands
from memory.files import InventoryData as inv
from memory.files import PencilsData
from config import admin_ids, measure, things
from library.graphics import SearchContent
import traceback
import library.logger as logger
from datetime import datetime
import random


def shorten(num: int):
    last = 1
    for i in measure.keys():
        if num >= i: last = i

    total = round(num / last, 2)
    if total - round(total) == 0: total = round(total)

    return str(total) + " " + measure[last]


def get_random_height(height):
    mx = int(height / 10) + 1
    mn = -mx // 2
    if mx < 10: mx = 10
    while True:
        plus = random.randint(mn, mx)
        if plus: return plus


class InventoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True, brief="Посмотреть свой инвентарь", aliases=["inv"])
    async def inventory(self, ctx: commands.Context, member: discord.Member = None):
        if member is not None:
            if ctx.author.id not in admin_ids:
                await ctx.send("Низя")
                return

        user = member or ctx.author

        inv_dict = inv.get_inv(ctx.guild.id, user.id)

        embed = discord.Embed(title="**Инвентарь:**", color=discord.Color.from_rgb(125, 68, 64))
        embed.set_footer(text=f"Инвентарь {user.display_name}", icon_url=user.display_avatar.url)
        if not inv_dict:
            embed.description = "*-пусто-*"
            await ctx.send(embed=embed)
            return

        for th in inv_dict.keys():
            embed.add_field(
                name=f"- {th}",
                value=f"Осталось использований: {inv_dict[th]}" if inv_dict[th] > 0 else "",
                inline=False)

        await ctx.send(embed=embed)

    @inventory.command(brief="Добавить в инвентарь (dev)", aliases=["give", "set"])
    async def add(self, ctx: commands.Context, member: discord.Member, thing: str, uses: int = -1):
        if ctx.author.id not in admin_ids:
            return

        if thing == "all":
            for i in things.keys():
                inv.set_thing(ctx.guild.id, member.id, i, uses)
        else:
            inv.set_thing(ctx.guild.id, member.id, thing, uses)

        await ctx.send(f"{thing} добавлено ({uses if uses > 0 else '∞'})")

    @inventory.command(brief="Удалить из инвентаря (dev)", aliases=["delete", "del", "rm"])
    async def remove(self, ctx: commands.Context, member: discord.Member, thing: str):
        if ctx.author.id not in admin_ids:
            return

        if inv.del_thing(ctx.guild.id, member.id, thing):
            await ctx.send(f"{thing} удалено")
        else:
            await ctx.send(f"Там нет {thing}")

    @inventory.command(brief="Очистить инвентарь (dev)")
    async def clear(self, ctx: commands.Context, member: discord.Member):
        if ctx.author.id not in admin_ids:
            return

        inv.set_inv(ctx.guild.id, member.id, {})
        await ctx.send("Инвентарь очищен")

    @commands.command(brief='Использовать предмет: use "название предмета" @игрок')
    async def use(self, ctx: commands.Context, thing: str, member: discord.Member = None):
        thing_orig = thing
        thing = thing.lower()

        if thing == "ножницы":
            try:
                if not member or type(member) is not discord.Member:
                    await ctx.send("Укажите на кого вы хотите использовать ножницы")
                    return
                if not inv.use_thing(ctx.guild.id, ctx.author.id, "Ножницы"):
                    await ctx.send("У вас нет ножниц")
                    return
                if inv.use_thing(ctx.guild.id, member.id, "Уно реверс кард"):
                    await ctx.send(f"У вас ничего не получилось, потому что у {member.display_name} был уно реверс кард")
                    await ctx.send(SearchContent.get_gif("Uno reverse", limit=30))
                    return

                height_member = PencilsData.get_pisa(ctx.guild.id, member.id)
                height_user = PencilsData.get_pisa(ctx.guild.id, ctx.author.id)
                if height_user >= height_member:
                    await ctx.send(f"Писька {member.display_name} должна быть больше чем ваша")
                    return

                minus = - (height_member - height_user) // 2
                PencilsData.add_heigth(ctx.guild.id, member.id, minus)
                PencilsData.log(ctx.guild.id, member.id, datetime.now().strftime("%Y-%m-%d"), minus)
                await ctx.send(f"Вы отрезали {shorten(abs(minus))} у {member.display_name}")
            except:
                logger.log(f"Ошибка ножниц: {traceback.format_exc()}")

        elif thing == "бустер":
            if not inv.use_thing(ctx.guild.id, ctx.author.id, "Бустер"):
                await ctx.send("У вас нет бустера")
                return
            height = PencilsData.get_last_plus(ctx.guild.id, ctx.author.id)
            PencilsData.add_heigth(ctx.guild.id, ctx.author.id, height)
            PencilsData.log(ctx.guild.id, ctx.author.id, datetime.now().strftime("%Y-%m-%d"), height)
            await ctx.send(f"Бустер применен, вы получили +{shorten(height)}")

        elif thing == "вор писек":
            if not member or type(member) is not discord.Member:
                await ctx.send("Укажите на кого вы хотите использовать вора писек")
                return
            if not inv.use_thing(ctx.guild.id, ctx.author.id, "Вор писек"):
                await ctx.send("У вас нет вора писек")
                return
            if inv.use_thing(ctx.guild.id, member.id, "Уно реверс кард"):
                await ctx.send(f"У вас ничего не получилось, потому что у {member.display_name} был уно реверс кард")
                await ctx.send(SearchContent.get_gif("Uno reverse", limit=30))
                return

            height = PencilsData.get_last_plus(ctx.guild.id, member.id) // 2

            PencilsData.add_heigth(ctx.guild.id, member.id, -height)
            PencilsData.log(ctx.guild.id, member.id, datetime.now().strftime("%Y-%m-%d"), -height)

            PencilsData.add_heigth(ctx.guild.id, ctx.author.id, height)
            PencilsData.log(ctx.guild.id, ctx.author.id, datetime.now().strftime("%Y-%m-%d"), height)

            await ctx.send(f"Вор писек украл {shorten(height)} у {member.display_name}")

        elif thing == "b.p":
            try:
                if not member or type(member) is not discord.Member:
                    await ctx.send("Укажите на кого вы хотите использовать b.p")
                    return
                if not inv.use_thing(ctx.guild.id, ctx.author.id, "b.p"):
                    await ctx.send("У вас нет b.p")
                    return
                if inv.use_thing(ctx.guild.id, member.id, "Уно реверс кард"):
                    await ctx.send(f"У вас ничего не получилось, потому что у {member.display_name} был уно реверс кард")
                    await ctx.send(SearchContent.get_gif("Uno reverse", limit=30))
                    return

                if PencilsData.checkdaily_pisa(ctx.guild.id, member.id, datetime.now().strftime("%Y-%m-%d")):

                    plus = get_random_height(PencilsData.get_pisa(ctx.guild.id, member.id))
                    PencilsData.add_heigth(ctx.guild.id, ctx.author.id, plus)
                    PencilsData.log(ctx.guild.id, ctx.author.id, datetime.now().strftime("%Y-%m-%d"), plus)
                    total = PencilsData.get_pisa(ctx.guild.id, ctx.author.id)

                    if plus > 0:
                        embed = discord.Embed(color=discord.Color.from_rgb(250, 130, 236),
                              title=f"~~Писька {member.display_name}~~ Ваша писька выросла на " + shorten(plus),
                              description=f"Теперь она {shorten(total)} в длину\n:eggplant: :chart_with_upwards_trend:")
                        embed.set_thumbnail(url=SearchContent.get_gif("grow"))
                    else:
                        embed = discord.Embed(color=discord.Color.from_rgb(250, 130, 236),
                              title=f"~~Писька {member.display_name}~~ Ваша писька уменьшилась на " + shorten(abs(plus)),
                              description=f"Теперь она {shorten(total)} в длину\n:eggplant: :chart_with_downwards_trend: ")
                        embed.set_thumbnail(url=SearchContent.get_gif("shrink"))

                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"{member.display_name} уже использовал дейли")
            except:
                logger.log(f"Ошибка b.p: {traceback.format_exc()}")

        elif thing == "уно реверс кард":
            if not inv.use_thing(ctx.guild.id, ctx.author.id, "Уно реверс кард"):
                await ctx.send("У вас нет Уно реверс кард")
                return

            await ctx.send("Вы случайно порвали карту...")

        elif thing == "бодя голоден":
            if not member or type(member) is not discord.Member:
                await ctx.send("Укажите на кого вы хотите использовать ножницы")
                return
            if not inv.use_thing(ctx.guild.id, ctx.author.id, "Бодя голоден"):
                await ctx.send("У вас нет Боди")
                return
            if inv.use_thing(ctx.guild.id, member.id, "Уно реверс кард"):
                await ctx.send(f"У вас ничего не получилось, потому что у {member.display_name} был уно реверс кард")
                await ctx.send(SearchContent.get_gif("Uno reverse", limit=30))
                return

            member_inv = inv.get_inv(ctx.guild.id, member.id)
            get_thing = random.choice(list(member_inv.keys()))
            member_inv.pop(get_thing)
            inv.set_inv(ctx.guild.id, member.id, member_inv)

            await ctx.send(f"Вы выкинули все {get_thing} из инвентаря {member.display_name}")

        elif thing == "бубылда":
            if not inv.use_thing(ctx.guild.id, ctx.author.id, "Бубылда", minus=False):
                await ctx.send("У вас нет Бубылды")
                return
            await ctx.send("Вы попытались выкинуть бубылду из инвентаря но она вернулась")

        elif thing == "смешной кот":
            if not inv.use_thing(ctx.guild.id, ctx.author.id, "Смешной кот"):
                await ctx.send("У вас нет смешного кота")
                return
            await ctx.send(SearchContent.get_gif(limit=50))

        else:
            if inv.use_thing(ctx.guild.id, ctx.author.id, thing_orig):
                await ctx.send("Ничего не произошло...")
            else:
                await ctx.send(f"У вас нет {thing}")

    @commands.command(brief='Узнать что делает предмет: info "название предмета"', aliases=["inf"])
    async def info(self, ctx: commands.Context, thing: str = None):
        if thing is None:
            await ctx.send('Укажите предмет: info "Название предмета"')
            return

        embed = discord.Embed(
            title=f"**{thing}**",
            color=discord.Color.orange(),
            description=things.get(thing, f"Не знаю что делает {thing}")
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
