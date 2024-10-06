import random
from dataclasses import dataclass
from typing import Callable
import discord
from discord.ext import commands
from datetime import datetime
from memory.files import InventoryData as inv
from library.graphics import SearchContent
from memory.files import PencilsData
import config
import library.logger as logger
import traceback
from library.other_tools import EventTime


def shorten(num: int):
    sign = 1 if num >= 0 else -1
    num = abs(num)
    last = 1
    for i in config.measure.keys():
        if num >= i: last = i

    total = round(num / last, 2)
    if total - round(total) == 0: total = round(total)

    return str(total*sign) + " " + config.measure[last]


def get_random_height(height):
    mx = int(height / 10) + 1
    mn = -mx // 2
    if mx < 10: mx = 10
    while True:
        plus = random.randint(mn, mx)
        if plus: return plus


def get_time_format(dt: datetime = None):
    if dt is None:
        dt = datetime.now()
    epoch = round(dt.timestamp())
    time_format = f"<t:{epoch}:R>"
    return time_format


def format_money(amount: float) -> str:
    end = "$"

    if amount >= 1000000:
        amount = round(amount / 1_000_000, 1)
        end = "M$"

    if amount >= 1000:
        amount = round(amount / 1000, 1)
        end = "K$"

    if amount%1 == 0:
        amount = int(amount)

    return str(amount)+end


@dataclass
class Thing:
    name: str
    emoji: str | None
    description: str | None
    amount: int | None
    min_amount: int | None
    max_amount: int | None
    function: Callable


class ThingsClass:
    def __init__(self):
        self.things = {}

    def thing(self, func, name: str, amount: tuple[int, int] = (1, 1), emoji: str | None = None,
              description: str | None = None):
        if amount[0] == amount[1]:
            new_thing = Thing(name, emoji, description, amount[0], None, None, func)
        else:
            new_thing = Thing(name, emoji, description, None, amount[0], amount[1], func)
        self.things[name] = new_thing

    def get_random_thing(self):
        thing = self.things[random.choice(list(self.things.keys()))]
        if thing.amount is None:
            amount = random.randint(thing.min_amount, thing.max_amount)
        else:
            amount = thing.amount
        return thing.name, amount, thing.emoji

    async def execute_thing(self, ctx: commands.Context, target_user: discord.Member, thing: str):
        things_and_identifiers = {i.name.lower(): i for i in list(self.things.values())}

        if thing.lower() in things_and_identifiers.keys():
            func = things_and_identifiers[thing.lower()].function
            await func(ctx, target_user)
            return True
        else:
            return False

    def get_help(self, thing: str, default: str = "Такого предмета нет"):
        descriptions = {i.name.lower(): i.description for i in list(self.things.values())}
        if thing.lower() in descriptions.keys():
            return descriptions[thing.lower()]
        else:
            return default

    def get_emoji(self, thing: str, default: str = None):
        emojis = {i.name.lower(): i.emoji for i in list(self.things.values())}
        if thing.lower() in emojis.keys():
            return emojis[thing.lower()]
        else:
            return default


Things = ThingsClass()


async def scissors(ctx: commands.Context, member: discord.Member):
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


Things.thing(scissors, "Ножницы", (1, 1), ":scissors:",
             description="Отрезает у указанного игрока половину размера между вашей писькой и писькой игрока. Например если у вас 10, а у игрока 100 - отрезает (100-10)/2 = 45. Ваша писька должна быть МЕНЬШЕ чем у игрока")


async def booster(ctx: commands.Context, member: discord.Member):
    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Бустер"):
        await ctx.send("У вас нет бустера")
        return
    height = PencilsData.get_last_plus(ctx.guild.id, ctx.author.id)
    PencilsData.add_heigth(ctx.guild.id, ctx.author.id, height)
    PencilsData.log(ctx.guild.id, ctx.author.id, datetime.now().strftime("%Y-%m-%d"), height)
    await ctx.send(f"Бустер применен, вы получили +{shorten(height)}")


Things.thing(booster, "Бустер", (1, 1), ":chart_with_upwards_trend:",
             description="Удваивает размер письки за сегодняшний день")


async def robber(ctx: commands.Context, member: discord.Member):
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


Things.thing(robber, "Вор писек", (1, 1), ":ninja:",
             description="Крадет половину письки указанного игрока (за сегодняшний день) и добавляет вам")


async def bp(ctx: commands.Context, member: discord.Member):
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
                                  title=f"~~Писька {member.display_name}~~ Ваша писька уменьшилась на " + shorten(
                                      abs(plus)),
                                  description=f"Теперь она {shorten(total)} в длину\n:eggplant: :chart_with_downwards_trend: ")
            embed.set_thumbnail(url=SearchContent.get_gif("shrink"))

        await ctx.send(embed=embed)
    else:
        await ctx.send(f"{member.display_name} уже использовал дейли")
        inv.add_thing_or_uses(ctx.guild.id, ctx.author.id, "b.p", 1)


Things.thing(bp, "b.p", (1, 1), ":eggplant:",
             description="Получает дейли письку за другого игрока если он еще не получал дейли")


async def unorevers(ctx: commands.Context, member: discord.Member):
    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Уно реверс кард"):
        await ctx.send("У вас нет Уно реверс кард")
        return

    await ctx.send("Вы случайно порвали карту...")


Things.thing(unorevers, "Уно реверс кард", (1, 1), ":identification_card:",
             description="Пассивно защищает от следующей подляны, при использовании просто ломается")


async def bodya(ctx: commands.Context, member: discord.Member = None):
    if not member or type(member) is not discord.Member:
        await ctx.send("Укажите на кого вы хотите использовать бодю")
        return
    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Бодя голоден"):
        await ctx.send("У вас нет Боди")
        return
    if inv.use_thing(ctx.guild.id, member.id, "Уно реверс кард"):
        await ctx.send(f"У вас ничего не получилось, потому что у {member.display_name} был уно реверс кард")
        await ctx.send(SearchContent.get_gif("Uno reverse", limit=30))
        return

    member_inv = inv.get_inv(ctx.guild.id, member.id)
    if not member_inv:
        await ctx.send(f"У {member.display_name} ничего нет")
        inv.add_thing_or_uses(ctx.guild.id, ctx.author.id, "Бодя голоден", 1)
        return
    get_thing = random.choice(list(member_inv.keys()))
    member_inv.pop(get_thing)
    inv.set_inv(ctx.guild.id, member.id, member_inv)

    await ctx.send(f"Бодя слопал все {get_thing} из инвентаря {member.display_name}")


Things.thing(bodya, "Бодя голоден", (1, 1), ":pig:",
             description="Удаляет из инвентаря указанного игрока случайный предмет (если у него есть предметы)")


async def bubilda(ctx: commands.Context, member: discord.Member):
    kick = random.choice([True, False])

    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Бубылда", minus=kick):
        await ctx.send("У вас нет Бубылды")
        return

    if member:
        if kick:
            inv.add_thing_or_uses(ctx.guild.id, member.id, "Бубылда", 1)
            await ctx.send(f"Вы положили бубылду в инвентарь {member.display_name}")
        else:
            await ctx.send("Вы попытались отдать бубылду, но она вернулась к вам")
    else:
        if kick:
            await ctx.send("Вы выкинули бубылду из инвентаря")
        else:
            await ctx.send("Вы попытались выкинуть бубылду из инвентаря но она вернулась")


Things.thing(bubilda, "Бубылда", (1, 2), ":smirk_cat:", description="Символ удачи, достатка и больших писек. Можно отдать другому игроку. Имеет секретные функции")


async def funnycat(ctx: commands.Context, member: discord.Member):
    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Смешной кот"):
        await ctx.send("У вас нет смешного кота")
        return
    await ctx.send(SearchContent.get_gif(limit=50))


Things.thing(funnycat, "Смешной кот", (1, 3), "<:funnycat:1051348714423328778>",
             description="Отправляет гифку смешного кота")


async def magicball(ctx: commands.Context, member: discord.Member):
    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Магические шары"):
        await ctx.send("У вас нет магических шаров")
        return

    class MagicballButtons(discord.ui.View):
        def __init__(self, owner: discord.Member):
            self.owner = owner
            self.is_timeout = False
            super().__init__(timeout=60 * 60)

        @discord.ui.button(label="Заглянуть", style=discord.ButtonStyle.blurple, emoji="👀")
        async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            response: discord.InteractionResponse = interaction.response
            if self.owner.id != interaction.user.id:
                await response.send_message("Вы ничего не увидели", ephemeral=True)
                return
            await response.send_message(
                "Следующий ивент будет в " + get_time_format(EventTime.get_time()) + " (±2 минуты)", ephemeral=True)

    await ctx.reply("Загляните в магический шар :crystal_ball::crystal_ball:\nОсторожнее, он пропадет через час", view=MagicballButtons(ctx.author))


Things.thing(magicball, "Магические шары", (1, 1), ":crystal_ball::crystal_ball:",
             description="Показывает время следующего ивента")


async def pashalko(ctx: commands.Context, member: discord.Member):
    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Пасхалко"):
        await ctx.send("У вас нет пасхалко")
        return

    await ctx.send("Пасхалко использовано, вам добавлено 42 к удаче")


Things.thing(pashalko, "Пасхалко", (1, 1), ":black_joker:", description="Добавляет 42 к удаче")


async def passivka(ctx: commands.Context, member: discord.Member):
    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Пассивка"):
        await ctx.send("У вас нет Пассивки")
        return

    height = PencilsData.get_pisa(ctx.guild.id, ctx.author.id)
    plus = round(height * 0.1)
    PencilsData.add_heigth(ctx.guild.id, ctx.author.id, plus)
    PencilsData.log(ctx.guild.id, ctx.author.id, datetime.now().strftime("%Y-%m-%d"), plus)
    await ctx.send(f"Пассивка использована, вы получили +{shorten(plus)}")


Things.thing(passivka, "Пассивка", (1, 1), ":gem:", description="Добавляет за каждую пассивку +5% от велечины, которая выпала вам в b.p (даже если выпал минус, пассивка добавит плюс к писе)\nЕсли использовать добавит +10% и пропадет")


async def inventory_robber(ctx: commands.Context, member: discord.Member):
    if not member or type(member) is not discord.Member:
        await ctx.send("Укажите на кого вы хотите использовать Ворунчика")
        return
    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Ворунчик"):
        await ctx.send("У вас нет Ворунчика")
        return
    if inv.use_thing(ctx.guild.id, member.id, "Уно реверс кард"):
        await ctx.send(f"У вас ничего не получилось, потому что у {member.display_name} был уно реверс кард")
        await ctx.send(SearchContent.get_gif("Uno reverse", limit=30))
        return

    member_inv = inv.get_inv(ctx.guild.id, member.id)
    if not member_inv:
        await ctx.send(f"У {member.display_name} ничего нет")
        inv.add_thing_or_uses(ctx.guild.id, ctx.author.id, "Ворунчик", 1)
        return
    get_thing = random.choice(list(member_inv.keys()))
    inv.use_thing(ctx.guild.id, member.id, get_thing)
    inv.add_thing_or_uses(ctx.guild.id, ctx.author.id, get_thing, 1)

    await ctx.send(f"Вы украли один {get_thing} из инвентаря {member.display_name}")

Things.thing(inventory_robber, "Ворунчик", (1, 1), ":man_detective::skin-tone-5:", description="Ворует один случайный предмет из инвентаря игрока")


async def danger_daily(ctx: commands.Context, member: discord.Member):
    check = PencilsData.checkdaily_pisa(ctx.guild.id, ctx.author.id, datetime.now().strftime("%Y-%m-%d"))

    if not check:
        await ctx.send("Сегодня вы уже забирали дейли")
        return

    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Опасный дейли"):
        await ctx.send("У вас нет Опасного дейли")
        return

    old = PencilsData.get_pisa(ctx.guild.id, ctx.author.id)
    height = random.randint(int(old*-0.20), int(old*0.20))

    PencilsData.add_heigth(ctx.guild.id, ctx.author.id, height)
    PencilsData.log(ctx.guild.id, ctx.author.id, datetime.now().strftime("%Y-%m-%d"), height)

    if height > 0:
        embed = discord.Embed(color=discord.Color.gold(),
                              title="Ваша писька выросла на " + shorten(height),
                              description=f"Теперь она {shorten(old+height)} в длину\n:eggplant: :chart_with_upwards_trend:")
        embed.set_thumbnail(url=SearchContent.get_gif("lets go", limit=30))
    else:
        embed = discord.Embed(color=discord.Color.dark_gray(),
                              title="Ваша писька уменьшилась на " + shorten(abs(height)),
                              description=f"Теперь она {shorten(old+height)} в длину\n:eggplant: :chart_with_downwards_trend:")
        embed.set_thumbnail(url=SearchContent.get_gif("skull", limit=30))

    await ctx.send(embed=embed)

Things.thing(danger_daily, "Опасный дейли", (1, 2), ":skull:", description="Это как дейли только опаснее.\nМожет добавить или отнять до 20% письки.\nМожно использовать вместо обычного дейли")


async def fishing_rod(ctx: commands.Context, member: discord.Member):
    if not inv.has_thing(ctx.guild.id, ctx.author.id, "Удочка"):
        await ctx.send("У вас нет удочки")
        return
    await ctx.send(f"Чтобы использовать удочку используйте команду {config.prefix}fishing")

Things.thing(fishing_rod, "Удочка", (1, 1), ":fishing_pole:", description=f"Удочка для рыбалки\nЧтобы рыбачить используйте команду {config.prefix}fishing\nДля рыбалки нужна наживка")


async def bait(ctx: commands.Context, member: discord.Member):
    if not inv.has_thing(ctx.guild.id, ctx.author.id, "Наживка"):
        await ctx.send("У вас нет наживки")
        return
    await ctx.send(f"Чтобы рыбачить используйте команду {config.prefix}fishing")

Things.thing(bait, "Наживка", (3, 5), ":worm:", description=f"Наживка для рыбалки\nЧтобы рыбачить используйте команду {config.prefix}fishing\nДля рыбалки нужна наживка")


async def ctrlz(ctx: commands.Context, member: discord.Member):
    if not member:
        member = ctx.author
    is_self_use = ctx.author.id == member.id
    if not inv.use_thing(ctx.guild.id, ctx.author.id, "Ctrl+Z"):
        await ctx.send("У вас нет Ctrl+Z")
        return

    height = -(PencilsData.get_last_plus(ctx.guild.id, member.id) // 2)

    PencilsData.add_heigth(ctx.guild.id, member.id, height)
    PencilsData.log(ctx.guild.id, member.id, datetime.now().strftime("%Y-%m-%d"), height)

    if is_self_use:
        await ctx.send(f"Ctrl+z использован, вы получили {shorten(height)}")
    else:
        await ctx.send(f"Ctrl+z использован, {member.display_name} получает {shorten(height)}")

Things.thing(ctrlz, "Ctrl+Z", (1, 1), ":back:", description="Работает как бустер, только обратно.\nУменьшает вам или другому игроку размер письки за последний день в два раза.\nРаботает и с отрицательным значением")