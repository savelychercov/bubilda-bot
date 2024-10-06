import discord
from discord.ext import commands, tasks
from discord import utils
from memory.files import readall, read_key, PencilsData, new_key, delete_key, InventoryData, daily_key, pisi_key, ShopData
import random
import config
import traceback
import library.logger as logger
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import mplcyberpunk
from statistics import mean
from library.graphics import SearchContent
from library.things_lib import Things, get_random_height, shorten, format_money
from library.other_tools import EventTime

measure = config.measure
plt.style.use('cyberpunk')

logging = config.pisi_cog_logging

pisi_date_log_format = "%Y-%m-%d"

event_messages = {}  # message.id: [datetime, message]


class ClaimHeightButton(discord.ui.View):
    def __init__(self):
        self.is_clicked = False
        super().__init__(timeout=None)

    @discord.ui.button(label="Забрать", style=discord.ButtonStyle.blurple, emoji="🎁")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_clicked: return
        self.is_clicked = True

        await interaction.message.edit(view=None, content="Подождите чючють :arrows_counterclockwise:")

        event_messages.pop(interaction.message.id)

        heights_dict = PencilsData.get_all_pisi(str(interaction.channel.guild.id))
        if heights_dict:
            heights = list(map(int, heights_dict.values()))
        else:
            heights = [0, 0]
        plus = 0
        for i in range(10):
            plus = abs(random.randint(min(heights), max(min(heights) + 2, round((mean(heights) - min(heights)) * 0.8))))
            if plus: break

        PencilsData.add_heigth(str(interaction.guild.id), str(interaction.user.id), plus)
        PencilsData.log(str(interaction.guild.id), str(interaction.user.id), datetime.now().strftime(pisi_date_log_format), plus)

        await update_role(
            interaction.guild,
            interaction.user,
            PencilsData.get_pisa(str(interaction.guild.id), str(interaction.user.id))
        )
        embed = discord.Embed(
            title=f"**+{shorten(plus)} к письке!!! 🎉**",
            description=":eggplant::chart_with_upwards_trend::up::free:",
            color=discord.Color.dark_gold(),
            timestamp=datetime.now()
        )
        embed.set_footer(
            text=f"Забрал {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.message.edit(embed=embed, view=None, content=None)


class ClaimThingButton(discord.ui.View):
    def __init__(self):
        self.is_clicked = False
        super().__init__(timeout=None)

    @discord.ui.button(label="Забрать", style=discord.ButtonStyle.blurple, emoji="📦")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.is_clicked: return
        self.is_clicked = True

        event_messages.pop(interaction.message.id)

        thing, amount, emoji = Things.get_random_thing()
        InventoryData.add_thing_or_uses(interaction.guild.id, interaction.user.id, thing, amount)

        if emoji is not None:
            thing = f"{emoji} {thing}"

        t = "Вам попался " + thing + (" ("+str(amount)+" шт)" if amount >= 1 else " (∞ шт)") + "!!!"

        embed = discord.Embed(
            title=t,
            description=":open_mouth: :package: <:funnycat:1051348714423328778>",
            color=discord.Color.teal(),
            timestamp=datetime.now()
        )
        embed.set_footer(
            text=f"Забрал {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.message.edit(embed=embed, view=None)


async def send_height_pisi_event_to_channel(channel: discord.TextChannel):
    embed = discord.Embed(
        title=f"**＋**<:poker_question:1225039226593345576> **к письке!!!**",
        description="**Успей забрать первым!**",
        color=discord.Color.gold()
    )
    message: discord.Message = await channel.send(
        embed=embed,
        view=ClaimHeightButton())

    del_time = datetime.now() + timedelta(seconds=config.delete_event_time)
    event_messages[message.id] = [del_time, message]

    if logging: logger.log(f"Event sent to {channel.name}")


async def send_thing_pisi_event_to_channel(channel: discord.TextChannel):
    embed = discord.Embed(
        title=":eggplant:<:poker_question:1225039226593345576>:shushing_face: Неизвестный предмет!!!",
        description="**Успей забрать первым!**",
        color=discord.Color.teal()
    )
    message: discord.Message = await channel.send(
        embed=embed,
        view=ClaimThingButton())

    del_time = datetime.now() + timedelta(seconds=config.delete_event_time)
    event_messages[message.id] = [del_time, message]

    if logging: logger.log(f"Event sent to {channel.name}")


async def send_pisi_event(bot, current: commands.Context = None):
    if current is not None:
        if random.random() < config.send_thing_chance:
            await send_thing_pisi_event_to_channel(current.channel)
        else:
            await send_height_pisi_event_to_channel(current.channel)
        return

    channels = readall("enabledpisievents")
    if channels is None: return

    for guild_id, channel_id in channels.items():
        channel = bot.get_guild(int(guild_id)).get_channel(int(channel_id))
        if random.random() < config.send_thing_chance:
            await send_thing_pisi_event_to_channel(channel)
        else:
            await send_height_pisi_event_to_channel(channel)


async def sell_item_event(bot: commands.Bot, guarant: bool = False, context = None):
    if not guarant and config.sell_item_on_event_chance < random.random(): return

    if not context:
        channels = readall("enabledpisievents").items()
    else:
        channels = [(str(context.guild.id), str(context.channel.id))]

    for guild_id, channel_id in channels:
        thing, amount, emoji = Things.get_random_thing()
        price = random.randint(config.sell_min_price, config.sell_max_price)

        ShopData.remove_slot_by_user(guild_id, bot.user.id)
        ShopData.add_to_shop(str(guild_id), thing, amount, price, str(bot.user.id))

        desc = f"> Предмет: {thing} {emoji}\n> Цена: {format_money(price)}\n> Количество: {amount}шт."

        embed = discord.Embed(
            color=discord.Color.from_rgb(167, 207, 242),
            title="В магазине появился новый предмет",
            description=desc
        )
        embed.set_footer(text="Успей купить первым")

        channel = bot.get_guild(int(guild_id)).get_channel(int(channel_id))
        await channel.send(embed=embed)


async def update_role(guild: discord.Guild, member: discord.Member, height: int):
    try:
        roles = config.guild_roles.get(guild.id, None)
        if not roles: return

        role_id = roles[max(roles.keys())]
        last_i = 1
        for i in roles.keys():
            if height < i:
                role_id = roles[last_i]
                break
            else:
                last_i = i

        try: role = utils.get(guild.roles, id=role_id)
        except AttributeError:
            if logging: logger.log(f"Role {role_id} not found in {guild.name}")
            return

        roles_to_remove = [utils.get(guild.roles, id=i) for i in roles.values()]
        await member.remove_roles(*roles_to_remove)
        await member.add_roles(role)
    except Exception as e:
        logger.err(e, "Error in update_role: ")


class PisiCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Команды писек"
        self.__cog_description__ = "Тут есть все команды которые связаны с письками"
        self.bot = bot
        self.event_task = None
        if logging: logger.log(f"Started at {datetime.now().strftime('%H:%M:%S')}\nNext event at {EventTime.get_time().strftime('%H:%M:%S')}")

    def cog_load(self):
        self.event_task = self.try_send_event.start()

    def cog_unload(self):
        if self.event_task:
            self.event_task.cancel()

    medals = [
        ":first_place:",
        ":second_place:",
        ":third_place:",
    ]

    @tasks.loop(seconds=config.update_event_time)
    async def try_send_event(self):
        now = datetime.now()
        if EventTime.check_time():
            await send_pisi_event(self.bot)
            await sell_item_event(self.bot)
            if logging: logger.log(
                f"Event sent at {now.strftime('%H:%M:%S')}\nNext event at {EventTime.get_time().strftime('%H:%M:%S')}")

        to_delete = []
        for mes_id, data in event_messages.items():
            if now > data[0]:
                to_delete.append(mes_id)
                await data[1].delete()

        for mes_id in to_delete:
            event_messages.pop(mes_id)

    @commands.command(brief="Топ по длине писи", aliases=["ptop", "pisit", "pt"])
    async def pisitop(self, ctx):
        heights = PencilsData.get_all_pisi(str(ctx.guild.id))
        if heights:

            for key in heights:
                heights[key] = int(heights[key])

            sortedkeys = sorted(heights, key=heights.get)
            sorted_heights = {}
            for key in sortedkeys[::-1]:
                sorted_heights[key] = heights[key]

            tops = []
            for i, user in enumerate(sorted_heights):
                discord_user: discord.member.Member = utils.get(ctx.guild.members, id=int(user))
                tops.append("**• " + discord_user.display_name + " - " + shorten(sorted_heights[user]) + "** " + (
                    self.medals[i] if i < 3 else ""))
            message = "\n".join(tops)
            if len(tops) > 3:
                message += ":pensive:"
            message += "\n"

            embed = discord.Embed(
                color=discord.Color.from_rgb(250, 130, 236),
                title="Топ по размеру писи:",
                description=message + "\nОбщая длина - **" + shorten(sum(list(map(int, heights.values())))) + "**"
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Тут еще ни у кого нет писи")

    @commands.command(brief="Нарастить писю", aliases=["pi", "p", "piska"])
    async def pisa(self, ctx: commands.Context):
        today, filename, user = str(ctx.message.created_at.date()), str(ctx.guild.id), str(ctx.author.id)

        if not config.testing:
            check = PencilsData.checkdaily_pisa(filename, user, today)
        else:
            check = True

        if not check:
            embed = discord.Embed(color=discord.Color.from_rgb(250, 130, 236),
                                  title="Сегодня вы уже писали эту команду",
                                  description=":shushing_face: :deaf_man_tone4:")
            embed.set_thumbnail(url=SearchContent.get_gif("bruh", limit=30))
            await ctx.send(embed=embed)
            return

        old = PencilsData.get_pisa(filename, user)
        plus = get_random_height(old)

        double_chance = InventoryData.get_uses(filename, user, "Бубылда") / 100
        bubilda_bonus = random.random() < double_chance
        if bubilda_bonus:
            plus *= 2

        passive_count = InventoryData.get_uses(filename, user, "Пассивка")
        passive_bonus = round(abs(plus)*0.05*passive_count)
        plus += passive_bonus

        PencilsData.add_heigth(filename, user, plus)
        PencilsData.log(filename, user, ctx.message.created_at.strftime(pisi_date_log_format), plus)

        total = old + plus

        if plus > 0:
            embed = discord.Embed(color=discord.Color.from_rgb(250, 130, 236),
                                  title="Ваша писька выросла на " + shorten(plus),
                                  description=f"Теперь она {shorten(total)} в длину\n:eggplant: :chart_with_upwards_trend:")
            embed.set_thumbnail(url=SearchContent.get_gif("grow", limit=30))
        else:
            embed = discord.Embed(color=discord.Color.from_rgb(250, 130, 236),
                                  title="Ваша писька уменьшилась на " + shorten(abs(plus)),
                                  description=f"Теперь она {shorten(total)} в длину\n:eggplant: :chart_with_downwards_trend: ")
            embed.set_thumbnail(url=SearchContent.get_gif("shrink", limit=30))

        if passive_bonus > 0:
            embed.description += f"\n+{shorten(passive_bonus)} с Пассивок ({passive_count})"
        if bubilda_bonus:
            embed.description += f"\n:confetti_ball: Бубылда удваивает ваш дейли :tada: <:funnycat:1051348714423328778>!!! (шанс {round(double_chance, 2)})"
        await ctx.send(embed=embed)
        await update_role(ctx.guild, ctx.author, total)

    """@commands.command(brief="Инфо о писях", aliases=["piinfo", "pinfo", "pisinfo", "pf"])
    async def pisiinfo(self, ctx):
        roles_dict = config.guild_roles[ctx.guild.id]
        just_shift = len(str(max(roles_dict.keys())))

        title = "Чтобы растить писи - команда **b.pisa**\n\nЧтобы посмотреть топ - b.pisitop\n\nВаша **роль** зависит от длины писи:"

        message = "\n"
        for cost in roles_dict.keys():
            cost_text = ("" + shorten(cost)).ljust(just_shift) + " см"
            role: discord.Role = utils.get(ctx.guild.roles, id=roles_dict[cost])
            message += f"**• `{cost_text}` **— {role.mention}\n"

        message += "\nРоль обновляется при изменении размера писи"

        embed = discord.Embed(
            title=title,
            description=message,
            color=discord.Colour.blurple()
        )
        await ctx.send(embed=embed)"""

    @commands.command(brief="Убирает отметку что вы забирали дейли писю (dev)", aliases=["unp"])
    async def unpisa(self, ctx: commands.Context, member: discord.Member = None):
        if ctx.author.id not in config.admin_ids:
            await ctx.send(":stuck_out_tongue:")
            return
        if not member:
            member = ctx.author

        filename = str(ctx.guild.id)
        if delete_key(pisi_key + daily_key + filename, str(member.id)):
            await ctx.send("Отметка убрана")
        else:
            await ctx.send("Вы не писали b.p")

    @commands.command(brief="График всех писек", aliases=["pga"])
    async def pisigraphall(self, ctx: commands.Context, count_str: str = "all"):
        title = 'График роста писи'
        try:
            count_days = int(count_str)
            title += f' за {count_str} д.'
            if count_days < 1:
                await ctx.send("Неверное значение <:funnycat:1051348714423328778>")
                return
        except ValueError:
            match count_str:
                case "all" | "a" | "все" | "всё":
                    count_days = 0
                    title += ' за всё время'
                case "week" | "w" | "неделя" | "н" | "нед":
                    count_days = 7
                    title += ' за неделю'
                case "month" | "m" | "месяц" | "м" | "мес":
                    count_days = 30
                    title += ' за месяц'
                case "year" | "y" | "год" | "г":
                    count_days = 365
                    title += ' за год'
                case _:
                    await ctx.send("Неверное значение <:funnycat:1051348714423328778>")
                    return

        max_points_on_graph = 13  # 13-25
        count_points = 1

        vals = PencilsData.get_all_pisi(str(ctx.guild.id))
        if vals is None:
            await ctx.send("Нет данных <:funnycat:1051348714423328778>")
            return
        min_height = max([int(i) for i in vals.values()])//50

        try:
            guild = str(ctx.guild.id)

            data = {}
            data_raw = readall(config.filekeys.pisi_key + "log" + guild)

            if not data_raw:
                await ctx.send("Нет данных <:funnycat:1051348714423328778>")
                return

            for key, value in data_raw.items():
                try:
                    name = utils.get(ctx.guild.members, id=int(key)).display_name
                except AttributeError:
                    name = key
                data[name] = {}

                days = list(value.split("/"))
                data[name]["start-val"] = int(days[0])
                for oneday in days[1:]:
                    date, plus = oneday.split(":")
                    date = datetime.strptime(date, pisi_date_log_format).strftime(pisi_date_log_format)
                    data[name][date] = int(plus)

            dates: set = set()
            for person in data.values():
                dates.update(person.keys())

            dates.remove('start-val')

            dates: list = sorted([datetime.strptime(date, pisi_date_log_format) for date in dates])
            skip_dates = []
            if 0 < count_days < len(dates):
                skip_dates = dates[:len(dates) - count_days]
                dates = dates[-count_days:]

            if len(dates) > max_points_on_graph:
                show_every_n = len(dates) // max_points_on_graph
            else:
                show_every_n = 1
            display_dates = ["START"]
            for date in dates:
                if count_points % show_every_n == 0 or count_points == len(dates):
                    display_dates.append(date.strftime('%m-%d'))
                count_points += 1

            for person, values in data.items():
                x = []
                y = []
                current_sum = values['start-val']
                if skip_dates:
                    for date in skip_dates:
                        date_str = str(date.strftime(pisi_date_log_format))
                        if date_str not in list(values.keys()): continue
                        current_sum += values[date_str]
                x.append("START")
                y.append(current_sum)

                for date in dates:
                    date_str = str(date.strftime(pisi_date_log_format))
                    if date_str in list(values.keys()):
                        current_sum += values[date_str]
                    x.append(date.strftime('%m-%d'))
                    y.append(current_sum)

                if current_sum < min_height:
                    continue

                plt.plot(x, y, label=person, marker='')

                plt.text(
                    x[-1],
                    y[-1],
                    " _ " + shorten(current_sum) + " " + person,
                    fontsize=10,
                    ha='left',
                    color="white",
                    bbox=dict(facecolor='#3e3852', alpha=0.9, linewidth=0, pad=0)
                )

            plt.xticks(display_dates, rotation=90)
            plt.xlabel('Даты')
            plt.ylabel('Размер писи')
            plt.title(title)
            plt.legend(loc='upper left')
            plt.autoscale(axis='x', tight=True)

            # mplcyberpunk.add_gradient_fill(alpha_gradientglow=0.35, gradient_start="bottom")
            mplcyberpunk.make_lines_glow()

            plt.savefig('memory/lastpisigraph.png', bbox_inches='tight', dpi=200)
            plt.clf()

            await ctx.send(file=discord.File('memory/lastpisigraph.png'))
        except Exception as e:
            logger.err(e, "Ошибка построения графика:\n")
            await ctx.send("Ошибочки <:funnycat:1051348714423328778>")
        finally:
            plt.clf()

    @commands.command(brief="Индивидуальный график писек", aliases=["pg"])
    async def pisigraph(self, ctx: commands.Context, member: discord.Member = None):
        max_points_on_graph = 8  # 8-15
        count_points = 1
        try:
            if member is None:
                user = str(ctx.author.id)
                name = ctx.author.display_name
            else:
                user = str(member.id)
                name = member.display_name

            guild = str(ctx.guild.id)

            data_raw = read_key(config.filekeys.pisi_key + "log" + str(guild), str(user))

            if not data_raw:
                await ctx.send("Нет данных <:funnycat:1051348714423328778>")
                return

            data = {}

            days = list(data_raw.split("/"))
            start_val = int(days[0])
            for oneday in days[1:]:
                date, plus = oneday.split(":")
                date = datetime.strptime(date, pisi_date_log_format).strftime("%m-%d")
                data[date] = int(plus)

            show_every_n = len(data)//max_points_on_graph
            if show_every_n == 0: show_every_n = 1

            x = []
            y = []
            current_sum = start_val
            interim_sum = start_val
            x_date_points = ["START"]
            x.append("START")
            y.append(current_sum)

            for date in data.keys():
                plus = data[date]
                current_sum += plus
                interim_sum += plus

                if count_points % show_every_n == 0 or count_points == len(data):
                    plt.text(
                        date,
                        current_sum,
                        s=("+" if interim_sum > 0 else "-") + shorten(abs(interim_sum)), fontsize=10,
                        ha='right', va='bottom' if interim_sum > 0 else 'top',
                        bbox=dict(facecolor='#352278' if interim_sum > 0 else '#960e0e', alpha=0.9, pad=2))
                    interim_sum = 0
                    x_date_points.append(date)

                count_points += 1

                x.append(date)
                y.append(current_sum)

            plt.plot(x, y, label=f"{name}: {shorten(current_sum)}", marker='o')

            plt.xticks(x_date_points, rotation=90)
            plt.xlabel('Даты')
            plt.ylabel('Размер писи')
            plt.title('График роста писи')
            plt.legend(loc='upper left')
            plt.autoscale(axis='x', tight=True)

            mplcyberpunk.add_glow_effects(gradient_fill=True)

            plt.savefig('memory/lastpisigraph.png', bbox_inches='tight', dpi=200)

            await ctx.send(file=discord.File('memory/lastpisigraph.png'))
        except:
            if logging: logger.log("Ошибка построения графика:\n" + str(traceback.format_exc()))
            await ctx.send("Ошибочки <:funnycat:1051348714423328778>")
        finally:
            plt.clf()

    @commands.command(brief="Добавить размер (dev)")
    async def addpisa(self, ctx: commands.Context, user: discord.Member, *, amount: int):
        try:
            if amount == 0:
                await ctx.send("Неверное значение <:funnycat:1051348714423328778>")
                return

            if ctx.author.id not in config.admin_ids:
                await ctx.send("Нельзя <:funnycat:1051348714423328778>")
                return

            PencilsData.add_heigth(str(ctx.guild.id), str(user.id), amount)
            PencilsData.log(str(ctx.guild.id), str(user.id), datetime.now().strftime(pisi_date_log_format), amount)
            if amount > 0:
                await ctx.send(f"Увеличено на {shorten(amount)}")
            else:
                await ctx.send(f"Укорочено на {shorten(abs(amount))}")
        except:
            if logging: logger.log("Ошибка добавления писи:\n" + str(traceback.format_exc()))

    @commands.command(brief="Задать размер (dev)")
    async def setpisa(self, ctx: commands.Context, user: discord.Member, *, amount: int):
        try:
            if ctx.author.id not in config.admin_ids:
                await ctx.send("Нельзя <:funnycat:1051348714423328778>")
                return

            old = PencilsData.get_pisa(str(ctx.guild.id), str(user.id))
            PencilsData.set_pisa(str(ctx.guild.id), str(user.id), amount)
            PencilsData.log(str(ctx.guild.id), str(user.id), datetime.now().strftime(pisi_date_log_format), amount - old)
            if amount >= 0:
                await ctx.send(f"Установлено на {shorten(amount)} ({amount})")
            else:
                await ctx.send(f"Установлено на -{shorten(abs(amount))} ({amount})")
        except:
            if logging: logger.log("Ошибка установки писи:\n" + str(traceback.format_exc()))

    @commands.command(brief="Лог писек (dev)", aliases=["pl"])
    async def pisilog(self, ctx: commands.Context):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return
        user = str(ctx.author.id)
        guild = str(ctx.guild.id)

        if not int(user) in config.admin_ids:
            await ctx.send("<:funnycat:1051348714423328778>")
            return

        with open("memory/temppisilogtosend.txt", "w+", encoding="utf-8") as file:
            data = readall(f"{config.filekeys.pisi_key}log{guild}")

            if not data:
                await ctx.send("Нет данных <:funnycat:1051348714423328778>")
                return

            for user_id, logs in data.items():
                file.write(utils.get(ctx.guild.members, id=int(user_id)).display_name + "\n")
                file.write("start-val:")
                logs = logs.split("/")
                for log in logs:
                    file.write(log + "\n")
                file.write(f"total-val:{PencilsData.get_pisa(guild, user_id)}\n")
                file.write("\n---------------\n\n")

        await ctx.author.send(file=discord.File("memory/temppisilogtosend.txt"))
        await ctx.send("Лог отправлен босс")

    @commands.command(brief="Отправить ивенты (dev)")
    async def pisieventsendall(self, ctx: commands.Context):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return
        try:
            await send_pisi_event(self.bot)
        except:
            if logging: logger.log("Ошибка рассылки ивентов:\n" + str(traceback.format_exc()))

    @commands.command(brief="Отправить один ивент (dev)")
    async def pisieventsend(self, ctx: commands.Context):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return
        try:
            await send_pisi_event(self.bot, ctx)
        except:
            if logging: logger.log("Ошибка отправки ивента:\n" + str(traceback.format_exc()))

    @commands.command(brief="Отпревить ивент магазина (dev)")
    async def shopeventsendall(self, ctx: commands.Context):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return
        try:
            await sell_item_event(self.bot, True)
        except:
            if logging: logger.log("Ошибка магазинного ивента:\n" + str(traceback.format_exc()))

    @commands.command(brief="Отпревить ивент магазина (dev)")
    async def shopeventsend(self, ctx: commands.Context):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return
        try:
            await sell_item_event(self.bot, True, ctx)
        except:
            if logging: logger.log("Ошибка магазинного ивента:\n" + str(traceback.format_exc()))

    @commands.command(brief="Ивенты с письками (dev)")
    async def pisieventenable(self, ctx: commands.Context):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return

        file = "enabledpisievents"
        channel = read_key(file, str(ctx.guild.id))
        if channel is None:
            new_key(file, str(ctx.guild.id), str(ctx.channel.id))
            await ctx.send("Ивенты с письками включены <:funnycat:1051348714423328778>")
        elif channel == str(ctx.channel.id):
            await ctx.send("Уже включено <:funnycat:1051348714423328778>")
        elif channel != str(ctx.channel.id):
            new_key(file, str(ctx.guild.id), str(ctx.channel.id))
            await ctx.send("Ивенты с письками переключены на этот канал <:funnycat:1051348714423328778>")
            # self.event_task = self.try_send_event.start()

    @commands.command(brief="Отключить ивенты (dev)")
    async def pisieventdisable(self, ctx: commands.Context):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return

        file = "enabledpisievents"
        if delete_key(file, str(ctx.guild.id)):
            await ctx.send("Ивенты с письками отключены на этом сервере <:funnycat:1051348714423328778>")
        else:
            await ctx.send("Ивенты с письками не включены <:funnycat:1051348714423328778>")


async def setup(bot):
    await bot.add_cog(PisiCog(bot))
