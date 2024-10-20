from random import randint
import discord
from discord.ext import commands
import config
from library.graphics import SearchContent
from memoryV1.files_db import BalanceData, CoinflipData
from library.logger import err

coinflipmessages = {}


async def clear_cf_messages(guild_id):
    global coinflipmessages
    for user in coinflipmessages[guild_id]:
        try:
            await coinflipmessages[guild_id][user].delete()
        except discord.Forbidden | discord.NotFound | discord.HTTPException | KeyError:
            pass
    coinflipmessages[guild_id] = {}


def rand():
    return bool(randint(0, 1))


class Buttons(discord.ui.View):
    def __init__(self, author, money, guild, bot, *, timeout=config.coinflip_timeout_time):
        self.author = author
        self.money = int(money)
        self.guild = guild
        self.bot = bot
        self.pressed = False
        super().__init__(timeout=timeout)

    async def on_timeout(self):
        await clear_cf_messages(self.guild)

    @discord.ui.button(label="Сыграть", style=discord.ButtonStyle.green, emoji="✅")
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        response: discord.InteractionResponse = interaction.response
        if self.pressed:
            return

        self.pressed = True

        if self.author == interaction.user:
            await response.send_message(
                f"{interaction.user.mention} на что ты жмал! Нельзя играть на свою ставку")
            return

        bal = BalanceData.add_balance(str(self.guild), str(interaction.user.id), -self.money)
        if bal is not None:
            await response.send_message(
                interaction.user.display_name + " вам не хватает " + str(-bal) + "$ чтобы сыграть")
            return

        await clear_cf_messages(self.guild)
        winner, looser = str(self.author.id), str(interaction.user.id)
        win_money = (self.money * 2) * (100 - config.coinflip_commission) / 100
        CoinflipData.del_bid(str(self.guild), winner)
        if rand():
            winner, looser = looser, winner
        BalanceData.add_balance(str(self.guild), winner, win_money)
        embed = discord.Embed(
            color=discord.Color.gold(),
            title="**Сумма выигрыша - " + str(win_money) + "$**",
            description="Победитель - " + self.bot.get_user(
                int(winner)).display_name + "\nПроигравший - " + self.bot.get_user(int(looser)).display_name)
        embed.set_thumbnail(url=SearchContent.get_gif("money"))
        await response.send_message(content=self.author.mention, embed=embed)

    @discord.ui.button(label="Отменить", style=discord.ButtonStyle.gray, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        response: discord.InteractionResponse = interaction.response
        if self.pressed:
            return

        if self.author == interaction.user:
            await clear_cf_messages(interaction.guild.id)
            BalanceData.add_balance(str(interaction.guild.id), str(self.author.id), self.money)
            CoinflipData.del_bid(str(self.guild), str(self.author.id))
            await response.send_message(self.author.mention + ", ставка отменена")
        else:
            await response.send_message(
                f"{interaction.user.mention} на что ты жмал! Отменить ставку может только тот кто ее поставил")


class CoinsCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Денги"
        self.__cog_description__ = "Команды для работы с деньгами и коинфлипом"
        self.bot = bot

    @commands.command(brief="Передать деньги  - pay (@user) (money)")
    async def pay(self, ctx, user: discord.Member = "None", money="None"):
        try:
            if user == "None" or money == "None":
                await ctx.send("Нужно писать " + config.prefix + "pay (@user) (money)")
                return
            try:
                money = int(money)
                if money <= 0:
                    await ctx.send("Количество денег указано неправильно")
                    return
            except ValueError:
                await ctx.send("Количество денег указано неправильно")
                return
            filename, giving_user, receiving_user = str(ctx.guild.id), str(ctx.author.id), str(user.id)

            bal = BalanceData.add_balance(filename, giving_user, -money)
            if bal:
                await ctx.send("Вам не хватает " + str(-bal) + "$")
                return

            BalanceData.add_balance(filename, receiving_user, money)
            await ctx.send(user.mention + ", вам передали " + str(money) + "$")
        except Exception as e:
            await ctx.send("Нужно писать " + config.prefix + "pay (@user) (money)")
            err(e, "Pay error:")

    @commands.command(brief="Узнать топ по балансу", aliases=["balls", "baltop", "bt", "btop", "t"])
    async def top(self, ctx):
        balls = BalanceData.allbalance(str(ctx.guild.id))
        if balls:

            for key in balls:
                balls[key] = int(balls[key])

            sorted_keys = sorted(balls, key=balls.get)
            sortedBalance = {}
            for key in sorted_keys[::-1]:
                sortedBalance[key] = balls[key]

            message = "\n"
            for user in sortedBalance:
                message = message + "**• " + self.bot.get_user(int(user)).display_name + " - " + str(
                    sortedBalance[user]) + "$**\n"
            embed = discord.Embed(
                color=discord.Color.gold(),
                title="Топ по балансу:",
                description=message + "\nОбщий баланс сервера - **" + str(sum(list(map(int, balls.values())))) + "$**"
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("Топ пуст!")

    @commands.command(brief="Узнать баланс - bal *(@user)", aliases=["bal", "ebal"])
    async def balance(self, ctx, user: discord.Member = "None"):
        if user == "None": user = ctx.author
        bal = BalanceData.get_balance(str(ctx.guild.id), str(user.id))
        await ctx.send("Баланс " + user.display_name + " - " + str(bal) + "$")

    @commands.command(brief="Добавить деньги (dev)")
    async def addbal(self, ctx, user: discord.Member = None, money: int = 500):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return
        if user is None:
            user = ctx.author
        BalanceData.add_balance(str(ctx.guild.id), str(user.id), int(money))
        await ctx.send(f"Добавлено {money}$ для {user.display_name}")

    @commands.command(brief="Заработать немного денег", aliases=["d"])
    async def daily(self, ctx):
        today, filename, user = str(ctx.message.created_at.date()), str(ctx.guild.id), str(ctx.author.id)
        check = BalanceData.checkdaily(filename, user, today)
        if check:
            money = randint(100, 500)
            BalanceData.add_balance(filename, user, money)
            embed = discord.Embed(color=discord.Color.gold(), title="Вы получаете " + str(money) + "$",
                                  description="Ура побежа")
            embed.set_thumbnail(url=SearchContent.get_gif("coin"))
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(color=discord.Color.dark_gold(), title="Сегодня вы уже забирали daily",
                                  description="Следующий раз завтра")
            embed.set_thumbnail(url=SearchContent.get_gif("bruh"))
            await ctx.send(embed=embed)

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.command(brief="Сыграть в коинфлип", aliases=["cf"])
    async def coinflip(self, ctx, money="None"):
        try:
            if money == "None":
                await clear_cf_messages(ctx.guild.id)
                """try: await ctx.message.delete()
                except: pass"""

                flips = CoinflipData.get_bids(str(ctx.guild.id))
                local_cf_messages = {}

                if not flips:
                    embed = discord.Embed(color=discord.Color.dark_gold(), title="Ставок нет!")
                    embed.set_thumbnail(url=SearchContent.get_gif("bruh"))
                    await ctx.send(embed=embed)
                    return

                for userId in flips:
                    user = self.bot.get_user(int(userId))
                    embed = discord.Embed(
                        color=discord.Color.gold(),
                        title=user.display_name + " - " + flips[userId] + "$")
                    embed.set_thumbnail(url=user.display_avatar)
                    local_cf_messages[userId] = await ctx.send(embed=embed, view=Buttons(author=user, money=flips[userId],
                                                                                       guild=ctx.guild.id,
                                                                                       bot=self.bot))
                    coinflipmessages[ctx.guild.id] = local_cf_messages
            else:
                try:
                    money = int(money)
                    if money <= 0:
                        await ctx.send("Количество денег указано неправильно")
                        return
                except ValueError:
                    await ctx.send("Количество денег указано неправильно")
                    return

                filename, givingUser = str(ctx.guild.id), str(ctx.author.id)

                if CoinflipData.check_bid(filename, givingUser):
                    await ctx.send("У вас уже есть ставка!")
                    return

                bal = BalanceData.add_balance(filename, givingUser, -money)
                if bal:
                    await ctx.send("Вам не хватает " + str(-bal) + "$")
                    return

                CoinflipData.new_bid(filename, givingUser, money)
                embed = discord.Embed(
                    color=discord.Color.gold(),
                    title="Ставка в размере " + str(money) + "$ создана",
                    description="Сыграть через " + config.prefix + "coinflip")
                embed.set_thumbnail(url=ctx.author.display_avatar)
                await ctx.send(embed=embed)
        except Exception as e:
            err(e, "Coinflip error:")


async def setup(bot):
    await bot.add_cog(CoinsCog(bot))
