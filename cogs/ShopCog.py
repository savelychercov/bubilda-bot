import discord
from discord.ext import commands
from memoryV1.files_db import InventoryData as inv
from memoryV1.files_db import BalanceData as bal
from memoryV1.files_db import ShopData
import library.logger as logger
from datetime import datetime
import traceback
from library.things_lib import Things, format_money

timeout_time = 10 * 60


class ShopButtons(discord.ui.View):
    def __init__(self, bot, message):
        super().__init__(timeout=timeout_time)
        self.message: discord.Message = message
        self.bot: commands.Bot = bot

    async def on_timeout(self) -> None:
        await self.message.edit(view=None)

    @discord.ui.button(style=discord.ButtonStyle.blurple, emoji="🔄")
    async def update(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await update_shop(self.bot, interaction.message)

    @discord.ui.button(label="Купить", style=discord.ButtonStyle.green)
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await interaction.response.send_message(view=BuyView(self.bot, interaction.guild))
        await interaction.response.send_modal(BuyModal(self.bot, interaction.guild))

    @discord.ui.button(label="Продать", style=discord.ButtonStyle.gray)
    async def sell(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SellModal(self.bot))


class BuyModal(discord.ui.Modal, title="Покупка"):
    def __init__(self, bot, guild):
        super().__init__(timeout=timeout_time)
        self.is_active = True
        self.bot = bot

    slot_id = discord.ui.TextInput(
        label="Номер лота в магазине",
        placeholder="Например: 1",
        required=True,
        min_length=1,
        max_length=5
    )

    async def on_timeout(self) -> None:
        self.is_active = False

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        logger.log("Sell Error " + str(error))
        await interaction.response.send_message("Произошла ошибка при заполнении формы", ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not self.is_active: return

            try:
                slot_id = int(self.slot_id.value)
            except ValueError:
                await interaction.response.send_message(
                    "Неправильно введен номер предмета, либо предмет уже купили\nВведите цифру предмета которая отображается в магазине",
                    ephemeral=True)
                return

            slot = ShopData.get_slot(interaction.guild.id, slot_id)
            if slot is None:
                await interaction.response.send_message(
                    "В магазине нет такого предмета\nВведите номер предмета который отображается в магазине",
                    ephemeral=True)
                return

            buying_user = interaction.user
            selling_user: discord.Member = discord.utils.get(interaction.guild.members, id=slot.user_id)

            if selling_user.id == buying_user.id:
                embed = discord.Embed(
                    title=f"Вы сняли свой лот (№{slot.id})",
                    color=discord.Color.orange(),
                    description=f"{slot.thing} ({slot.amount}шт.)",
                    timestamp=datetime.now()
                )
                embed.set_footer(text=interaction.user.display_name)

                ShopData.remove_slot(interaction.guild.id, slot.id)
                inv.add_thing_or_uses(interaction.guild.id, buying_user.id, slot.thing, slot.amount)

                await interaction.response.send_message(embed=embed)
                await update_shop(self.bot, interaction.message)
                return

            not_enough_money = bal.add_balance(interaction.guild.id, buying_user.id, -slot.price)
            if not_enough_money:
                await interaction.response.send_message(
                    "У вас не хватает " + format_money(abs(not_enough_money)) + " чтобы купить этот предмет",
                    ephemeral=True)
                return

            bal.add_balance(interaction.guild.id, selling_user.id, slot.price)

            ShopData.remove_slot(interaction.guild.id, slot.id)
            inv.add_thing_or_uses(interaction.guild.id, buying_user.id, slot.thing, slot.amount)

            desc = f"Вы купили **{slot.thing}** ({slot.amount}шт) за {format_money(slot.price)}\n"
            desc += f"У вас осталось: **{bal.get_balance(interaction.guild.id, buying_user.id)}$**\n"
            desc += f"**+{format_money(slot.price)}** для {selling_user.mention}"

            embed = discord.Embed(
                title="Покупка",
                color=discord.Color.orange(),
                description=desc,
                timestamp=datetime.now()
            )
            embed.set_footer(text=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)

            await interaction.response.send_message(embed=embed)
            await update_shop(self.bot, interaction.message)

        except:
            logger.log(traceback.format_exc())


class SellModal(discord.ui.Modal, title="Продажа"):
    def __init__(self, bot):
        super().__init__(timeout=timeout_time)
        self.is_active = True
        self.bot = bot

    thing = discord.ui.TextInput(
        label="Название предмета",
        placeholder="Например: Ножницы",
        required=True,
        style=discord.TextStyle.long,
        min_length=1,
        max_length=100
    )

    amount = discord.ui.TextInput(
        label="Количество",
        placeholder="1",
        default=1,
        required=True,
        min_length=1,
        max_length=5
    )

    price = discord.ui.TextInput(
        label="Цена",
        placeholder="1000",
        required=True,
        min_length=1,
        max_length=5
    )

    async def on_timeout(self) -> None:
        self.is_active = False

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        logger.log("Sell Error " + str(error))
        await interaction.response.send_message("Произошла ошибка при заполнении формы", ephemeral=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            if not self.is_active: return

            thing = self.thing.value
            amount = int(self.amount.value)
            price = int(self.price.value)

            # Check if user has thing to sell
            if not inv.has_thing(interaction.guild.id, interaction.user.id, thing):
                await interaction.response.send_message("У вас нет такого предмета\nПроверьте название еще раз",
                                                        ephemeral=True)
                return

            has_things = inv.get_uses(interaction.guild.id, interaction.user.id, thing)

            if has_things <= 0:
                await interaction.response.send_message(
                    "Бесконечные предметы продавать нельзя, откуда они вообще у вас", ephemeral=True)
                return

            if amount > has_things:
                await interaction.response.send_message("У вас не хватает предметов\nПроверьте количество еще раз",
                                                        ephemeral=True)
                return

            if amount <= 0:
                await interaction.response.send_message("Количество предметов должно быть больше нуля", ephemeral=True)
                return

            if price < 0:
                await interaction.response.send_message("Цена не может быть отрицательной", ephemeral=True)
                return

            for i in range(amount):
                inv.use_thing(interaction.guild.id, interaction.user.id, thing)

            ShopData.add_to_shop(interaction.guild.id, thing, amount, price, interaction.user.id)

            embed = discord.Embed(
                title="Продажа",
                color=discord.Color.orange(),
                description=f"{interaction.user.display_name} выставил {self.thing.value} ({self.amount.value}шт.) на продажу за {format_money(price)}"
            )
            await interaction.response.send_message(embed=embed)
            await update_shop(self.bot, interaction.message)
        except:
            logger.log(traceback.format_exc())


async def update_shop(bot: commands.Bot, message: discord.Message):
    embed = discord.Embed(
        title="Магазин",
        color=discord.Color.orange(),
        timestamp=datetime.now()
    )

    if not ShopData.get_shop(message.guild.id):
        embed.add_field(name="*-пусто-*", value="", inline=False)

    for slot in ShopData.get_shop(message.guild.id):
        desc = f"> Цена: {format_money(slot.price)}\n> Количество: {slot.amount}шт.\n> Владелец: {discord.utils.get(message.guild.members, id=slot.user_id).display_name}"
        emoji = Things.get_emoji(slot.thing, default = ":person_shrugging:")
        embed.add_field(name=f"**№{slot.id} - {slot.thing}** {emoji}", value=desc, inline=False)

    embed.set_footer(text="Обновлен:")

    await message.edit(embed=embed, view=ShopButtons(bot, message))


class ShopCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Магазин"
        self.__cog_description__ = "Команды для работы с магазином"
        self.bot = bot

    @commands.command(brief="Открыть магазин")
    async def shop(self, ctx):
        embed = discord.Embed(
            title="Загрузка магазина...",
            color=discord.Color.orange())
        message = await ctx.send(embed=embed)

        await update_shop(self.bot, message)


async def setup(bot):
    await bot.add_cog(ShopCog(bot))
