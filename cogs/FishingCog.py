import discord
from discord import Interaction
from discord.ext import commands
from memory.files import InventoryData as inv
from memory.files import BalanceData
from library.things_lib import Things
from library.graphics import SearchContent
from memoryV2 import DB
from dataclasses import dataclass
from library import logger
import config
import random
import math
import traceback


@dataclass
class FishData:
    name: str
    description: str
    emoji: str
    image: str
    cost: int
    size: tuple[int, int]


@dataclass
class Fish:
    name: str
    description: str
    emoji: str
    image: str
    cost: int
    size: int


fish_db = DB.DataBase("fishbag", "♦")
fish_slice_key = "♂"


def db_set_fishes(guild_id: int, user_id: int, fishes: list[Fish]) -> None:
    fish_str = fish_slice_key.join([str(fish) for fish in fishes])
    fish_db.new_key(guild_id, user_id, fish_str)


def db_get_fishes(guild_id, user_id) -> list[Fish]:
    raw_str = fish_db.read_key(guild_id, user_id)
    if raw_str is None or not raw_str.strip():
        return []
    fish_list = raw_str.strip().split(fish_slice_key)
    return [eval(fish) for fish in fish_list]


def db_add_fish(guild_id, user_id, fish: Fish) -> None:
    fish_list = db_get_fishes(guild_id, user_id)
    fish_list.append(fish)
    db_set_fishes(guild_id, user_id, fish_list)


def fish_gen(fish_data: FishData) -> Fish:
    size = random.randint(fish_data.size[0], fish_data.size[1])
    average_size = (fish_data.size[0] + fish_data.size[1]) / 2
    max_delta = average_size - fish_data.size[0]
    delta_size = size - average_size
    aberration_coeff = delta_size / max_delta
    cost = round(aberration_coeff * config.fish_price_aberration * fish_data.cost + fish_data.cost)
    fish = Fish(
        name=fish_data.name,
        description=fish_data.description,
        emoji=fish_data.emoji,
        image=fish_data.image,
        cost=cost,
        size=size
    )
    return fish


def get_random_fish(power: int) -> Fish:
    if power == 1:
        fish_data = random.choice(small_fish)
    elif power == 2:
        fish_data = random.choice(medium_fish)
    else:  # power == 3:
        fish_data = random.choice(large_fish)
    return fish_gen(fish_data)


small_fish = [  # 194, 194, 194
    FishData(name="Рыба клоун",
             description="Клоун как ты",
             emoji=":tropical_fish:",
             image="https://www.stellexshop.ru/upload/iblock/ed0/erz977qq64a5iugh7gjgn928ld83r7dz/nemo480.jpg",
             cost=1000,
             size=(5, 14)),
    FishData(name="Карасик",
             description="Просто рыба, что с него взять",
             emoji=":fish:",
             image="https://static.wikia.nocookie.net/fortnite/images/7/7b/%D0%9E%D1%80%D0%B0%D0%BD%D0%B6%D0%B5%D0%B2%D0%B0%D1%8F_%D1%80%D1%8B%D0%B1%D0%BA%D0%B0.png/revision/latest?cb=20210221072224&path-prefix=ru",
             cost=800,
             size=(5, 20)),
    FishData(name="Рак",
             description="Снова сфидил",
             emoji=":lobster:",
             image="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT96PNeWr_a5P5-5oYA1jI5CpK_mdnqNV6Vpg&s",
             cost=500,
             size=(3, 10)),
]

medium_fish = [  # 98, 160, 240
    FishData(name="Синий лобстер",
             description="Как из мема",
             emoji=":lobster:",
             image="https://pikuco.ru/upload/test_stable/5a5/5a53a24f65bbcf7c756be1ccf8fb8da8.webp",
             cost=5000,
             size=(20, 35)),
    FishData(name="Рыба фугу",
             description="Смешная рыба",
             emoji=":blowfish:",
             image="https://flomaster.top/o/uploads/posts/2024-02/thumbs/1708701959_flomaster-top-p-samie-smeshnie-ribi-vkontakte-risunok-1.jpg",
             cost=3000,
             size=(10, 20)),
]

large_fish = [  # 255, 182, 79
    FishData(name="Мегаладон",
             description="ЭТО РЕАЛЬНО МЕГАЛАДОН!!!",
             emoji=":lobster:",
             image="https://i.ytimg.com/vi/sngjQpWrxAc/maxresdefault.jpg",
             cost=10000,
             size=(200, 400)),
    FishData(name="Рыба Адун",
             description="Синий",
             emoji=":fish:",
             image="https://media.tenor.com/Gr2xrowbvHgAAAAM/%D0%BF%D0%B0%D0%BF%D0%B8%D1%87-%D0%B0%D0%B4%D1%83%D0%BD.gif",
             cost=3000,
             size=(20, 35)),
]

current_managers = {
    # user_id: manager
}


class FishingManager:
    def __init__(self, bot: commands.Bot, context: commands.Context):
        self.bot = bot
        self.user = context.author
        self.channel = context.channel
        self.guild = context.guild
        self.message: discord.Message = None
        self.wait_count = 1

    def get_check(self) -> bool:
        is_pressed = False

        async def check_owner(interaction: discord.Interaction):
            nonlocal is_pressed
            response: discord.InteractionResponse = interaction.response
            check = interaction.user.id == self.user.id
            if not check:
                await response.send_message("Не мешайте человеку рыбачить :pray:", ephemeral=True)
                return False
            if is_pressed:
                await response.defer()
                return False
            is_pressed = True
            return True

        return check_owner

    async def start(self) -> None:
        has_rod = inv.has_thing(self.guild.id, self.user.id, "Удочка")
        bait_count = inv.get_uses(self.guild.id, self.user.id, "Наживка")
        has_bait = bait_count != 0
        desc = f"> Удочка :fishing_pole:: {'Есть' if has_rod else 'Нет'}\n> Наживка :worm:: {(str(bait_count) + ' шт') if has_bait else 'Нет'}"
        if not has_rod or not has_bait:
            desc += "\n\n:exclamation: Вы не можете рыбачить, у вас не хватает предметов :exclamation:"

        start_embed = discord.Embed(
            title=":tropical_fish: Рыбалка :fish:",
            description=desc,
            color=discord.Color.from_rgb(84, 232, 145))
        start_embed.set_footer(text=f"{self.user.display_name}", icon_url=self.user.display_avatar.url)

        self.message = await self.channel.send(embed=start_embed)
        start_view = self.FishingStartView(self, enabled=has_rod and has_bait)
        await self.message.edit(view=start_view)

    async def stop(self) -> None:
        cancel_embed = discord.Embed(
            title="Рыбалка отменена",
            description="До следующего раза!",
            color=discord.Color.from_rgb(56, 89, 50)
        )
        cancel_embed.set_footer(text=self.user.display_name, icon_url=self.user.display_avatar.url)

        try:
            await self.message.edit(embed=cancel_embed, view=None)
        except discord.errors.NotFound:
            pass
        except Exception as e:
            logger.log("Cant cancel fishing session:\n" + str(e))

    class FishingStartView(discord.ui.View):
        def __init__(self, manager, enabled: bool):
            super().__init__(timeout=60*10)

            self.manager: FishingManager = manager

            self.enabled = enabled
            self.interaction_check = self.manager.get_check()

            fishing_button = discord.ui.Button(
                label="Начать рыбалку",
                style=discord.ButtonStyle.green,
                emoji="🎣",
                disabled=not enabled,
                row=0)
            fishing_button.callback = self.fishing_button
            self.add_item(fishing_button)

        async def on_timeout(self) -> None:
            self.stop()
            await self.manager.stop()

        async def fishing_button(self, interaction: discord.Interaction):
            response: discord.InteractionResponse = interaction.response
            await response.defer()
            if not inv.use_thing(self.manager.guild.id, self.manager.user.id, "Наживка"):
                await response.send_message("Вы не можете рыбачить, у вас нет наживки", ephemeral=True)
                await self.manager.stop()
                return
            view = self.manager.FishingWaitView(self.manager, first=True)
            wait_embed = view.get_embed()
            await self.manager.message.edit(embed=wait_embed, view=view)

        @discord.ui.button(label="Отмена", style=discord.ButtonStyle.gray, emoji="❌", row=1)
        async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.manager.message.edit(view=None)
            await self.manager.stop()
            self.stop()

    class FishingWaitView(discord.ui.View):
        def __init__(self, manager, first: bool):
            super().__init__(timeout=60*10)
            self.manager: FishingManager = manager
            self.interaction_check = self.manager.get_check()
            self.first = first
            self.ended = False

        def get_embed(self):
            if self.first:
                wait_embed = discord.Embed(
                    title=":tropical_fish: Рыбалка :fish:",
                    description=f"Вы закинули удочку!\n> -1 Наживка :worm:\n\nВы ждете {self.manager.wait_count} мин.",
                    color=discord.Color.from_rgb(84, 232, 145))
            else:
                wait_embed = discord.Embed(
                    title=":tropical_fish: Рыбалка :fish:",
                    description=f"Рыба не клюет...\n\nВы ждете {self.manager.wait_count} мин.",
                    color=discord.Color.from_rgb(84, 232, 145))
            wait_embed.set_footer(
                text=f"{self.manager.user.display_name}",
                icon_url=self.manager.user.display_avatar.url)
            return wait_embed

        async def on_timeout(self) -> None:
            if self.ended: return
            self.stop()
            await self.manager.stop()

        @discord.ui.button(label="Тянуть", style=discord.ButtonStyle.gray, emoji="🎣", row=0)
        async def catch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            response: discord.InteractionResponse = interaction.response
            self.ended = True
            self.stop()
            nothing_embed = discord.Embed(
                title=":tropical_fish: Рыбалка :fish:",
                description="Вы ничего не поймали!\nРыбалка завершена",
                color=discord.Color.from_rgb(84, 232, 145))
            nothing_embed.set_footer(
                text=f"{self.manager.user.display_name}",
                icon_url=self.manager.user.display_avatar.url)
            await self.manager.message.edit(embed=nothing_embed, view=None)

        @discord.ui.button(label="Ждать", style=discord.ButtonStyle.green, emoji="😴", row=0)
        async def wait_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            response: discord.InteractionResponse = interaction.response
            await response.defer()
            self.manager.wait_count += 1
            if config.nibble_chance > random.random():
                view = self.manager.FishingNibbleView(self.manager, power=random.randint(1, 3))
            else:
                view = self.manager.FishingWaitView(self.manager, first=False)
            next_embed = view.get_embed()
            await self.manager.message.edit(embed=next_embed, view=view)

        @discord.ui.button(label="Отмена", style=discord.ButtonStyle.gray, emoji="❌", row=1)
        async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.manager.message.edit(view=None)
            await self.manager.stop()
            self.stop()

    class FishingNibbleView(discord.ui.View):
        def __init__(self, manager, power: int):
            super().__init__(timeout=60*10)
            self.manager: FishingManager = manager
            self.interaction_check = self.manager.get_check()
            self.power = power
            self.ended = False

        async def on_timeout(self) -> None:
            if self.ended: return
            self.stop()
            await self.manager.stop()

        def get_embed(self):
            if self.power == 1:
                nibble_embed = discord.Embed(
                    title=":tropical_fish: Рыбалка :fish:",
                    description=f"Чуть чуть клюет!\n\nВы ждете {self.manager.wait_count} мин.",
                    color=discord.Color.from_rgb(84, 232, 145))
            elif self.power == 2:
                nibble_embed = discord.Embed(
                    title=":tropical_fish: Рыбалка :fish:",
                    description=f"Клюет!\n\nВы ждете {self.manager.wait_count} мин.",
                    color=discord.Color.from_rgb(84, 232, 145))
            else:  # self.power == 3:
                nibble_embed = discord.Embed(
                    title=":tropical_fish: Рыбалка :fish:",
                    description=f"Жоска клюет!\n\nВы ждете {self.manager.wait_count} мин.",
                    color=discord.Color.from_rgb(84, 232, 145))
            nibble_embed.set_footer(
                text=f"{self.manager.user.display_name}",
                icon_url=self.manager.user.display_avatar.url)
            return nibble_embed

        @discord.ui.button(label="Тянуть", style=discord.ButtonStyle.green, emoji="🎣", row=0)
        async def catch_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            try:
                response: discord.InteractionResponse = interaction.response
                await response.defer()
                self.ended = True
                self.stop()
                if config.fish_fall_off_chance > random.random():
                    end_embed = discord.Embed(
                        title=":tropical_fish: Рыбалка :fish:",
                        description="Рыба сорвалась!\nПовезет в следующий раз\nРыбалка завершена",
                        color=discord.Color.from_rgb(61, 107, 26))
                elif config.catch_thing_chance > random.random():
                    thing, uses, emoji = Things.get_random_thing()
                    inv.add_thing_or_uses(self.manager.guild.id, self.manager.user.id, thing, uses)
                    end_embed = discord.Embed(
                        title=":tropical_fish: Рыбалка :fish:",
                        description=f"Вы поймали {thing} {emoji}\n"
                                    f"> Количество: {uses} шт\n\n",
                        color=discord.Color.from_rgb(150, 255, 210))
                else:
                    fish = get_random_fish(self.power)
                    db_add_fish(self.manager.guild.id, self.manager.user.id, fish)
                    fish_type = ["маленькую", "среднюю", "большую"][self.power - 1]
                    color = ((194, 194, 194), (98, 160, 240), (255, 182, 79))[self.power - 1]
                    end_embed = discord.Embed(
                        title=":tropical_fish: Рыбалка :fish:",
                        description=f"Вы поймали {fish_type} рыбу: {fish.name} {fish.emoji}\n"
                                    f"> Описание: {fish.description}\n"
                                    f"> Цена :moneybag:: {fish.cost}$\n"
                                    f"> Размер: {fish.size} см\n\n"
                                    "Рыбалка завершена",
                        color=discord.Color.from_rgb(*color))
                    end_embed.set_thumbnail(url=fish.image)
                end_embed.set_footer(
                    text=f"{self.manager.user.display_name}",
                    icon_url=self.manager.user.display_avatar.url)
                await self.manager.message.edit(embed=end_embed, view=None)
            except Exception as e:
                logger.log("Cant catch fish in nibble manager:\n" + str(e))

        @discord.ui.button(label="Ждать", style=discord.ButtonStyle.green, emoji="😴", row=0)
        async def wait_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            response: discord.InteractionResponse = interaction.response
            await response.defer()
            self.manager.wait_count += 1
            if config.nibble_chance > random.random():
                view = self.manager.FishingNibbleView(self.manager, power=random.randint(1, 3))
            else:
                view = self.manager.FishingWaitView(self.manager, first=False)
            next_embed = view.get_embed()
            await self.manager.message.edit(embed=next_embed, view=view)

        @discord.ui.button(label="Отмена", style=discord.ButtonStyle.gray, emoji="❌", row=1)
        async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.manager.message.edit(view=None)
            await self.manager.stop()
            self.stop()


class FishingCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Рыбалка"
        self.__cog_description__ = "Команды рыбалки"
        self.bot = bot

    @commands.command(brief="Рыбачить", aliases=["fish", "f"])
    async def fishing(self, ctx: commands.Context):
        if current_managers.get(ctx.author.id, False):
            await current_managers[ctx.author.id].stop()
            del current_managers[ctx.author.id]

        manager = FishingManager(self.bot, ctx)
        current_managers[ctx.author.id] = manager
        await manager.start()

    @fishing.error
    async def on_error(self, ctx: commands.Context, error):
        if current_managers.get(ctx.author.id, False):
            await current_managers[ctx.author.id].stop()
            del current_managers[ctx.author.id]
        logger.log("Error in fishing session:\n" + str(error))
        embed = discord.Embed(
            title=":warning: Ошибка",
            description="Я хз в чем дело",
            color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.command(brief="Посмотреть своих рыбок", aliases=["myf", "mf", "myfish"])
    async def fishbag(self, ctx: commands.Context, member: discord.Member = None):
        if member is None:
            member = ctx.author
        fish_on_page_count = 5
        pages_count = 0

        class MyFishButtons(discord.ui.View):
            def __init__(self, enabled: bool):
                super().__init__(timeout=60*10)
                self.page = 0
                self.is_sell_pressed = False
                disabled_pagination = not enabled

                previous_button = discord.ui.Button(
                    label=None, style=discord.ButtonStyle.gray, emoji="◀", disabled=disabled_pagination)
                previous_button.callback = self.previous_button_callback
                next_button = discord.ui.Button(
                    label=None, style=discord.ButtonStyle.gray, emoji="▶", disabled=disabled_pagination)
                next_button.callback = self.next_button_callback
                if ctx.author.id == member.id:
                    sell_button = discord.ui.Button(
                        label="Продать всю рыбу", style=discord.ButtonStyle.gray, emoji="💰")
                    sell_button.callback = self.sell_button_callback
                    self.add_item(sell_button)
                self.add_item(previous_button)
                self.add_item(next_button)

            async def on_timeout(self) -> None:
                await message.edit(view=None)
                self.stop()

            async def interaction_check(self, interaction: Interaction, /) -> bool:
                response: discord.InteractionResponse = interaction.response
                await response.defer()
                if interaction.user.id == ctx.author.id:
                    return True
                else:
                    await response.send_message("Вы не можете использовать эту кнопку", ephemeral=True)
                    return False

            async def previous_button_callback(self, interaction: discord.Interaction):
                if self.page > 0:
                    self.page -= 1
                    await update_page(self.page)

            async def next_button_callback(self, interaction: discord.Interaction):
                if self.page < pages_count - 1:
                    self.page += 1
                    await update_page(self.page)

            async def sell_button_callback(self, interaction: discord.Interaction):
                response: discord.InteractionResponse = interaction.response
                followup: discord.Webhook = interaction.followup
                if self.is_sell_pressed:
                    return
                self.is_sell_pressed = True
                fishes = db_get_fishes(ctx.guild.id, ctx.author.id)
                if not fishes:
                    await followup.send("У вас нет рыбы", ephemeral=True)
                    return
                db_set_fishes(ctx.guild.id, ctx.author.id, [])
                total = 0
                for fish in fishes:
                    total += fish.cost
                BalanceData.add_balance(str(ctx.guild.id), str(ctx.author.id), total)
                embed = discord.Embed(
                    title=f"Вы продали всю свою рыбу, и получили {total}$",
                    description=":moneybag: :money_mouth: :money_with_wings:",
                    color=discord.Color.green())
                embed.set_thumbnail(url=SearchContent.get_gif("money"))
                await followup.send(embed=embed)
                await update_page(self.page)

        pagination_view = None

        async def update_page(page: int = 0):
            nonlocal pages_count, pagination_view
            fishes = db_get_fishes(ctx.guild.id, member.id)
            all_fishes_count = len(fishes)
            pages_count = math.ceil(len(fishes) / fish_on_page_count) if fishes else 1
            if pagination_view is None:
                pagination_view = MyFishButtons(pages_count > 1)
            if len(fishes) > 5:
                left = min(page * fish_on_page_count, all_fishes_count-1)
                right = min((page + 1) * fish_on_page_count, all_fishes_count)
                fishes = fishes[left:right]
            if not fishes: desc = "-пусто-"
            else: desc = ""
            for fish in fishes:
                desc += (f"{fish.emoji} {fish.name}\n"
                         f"> Описание: {fish.description}\n"
                         f"> Цена :moneybag:: {fish.cost}$\n"
                         f"> Размер: {fish.size} см\n\n")
            title = f"**Рыбки {member.display_name}** ({page+1} / {pages_count})" if member != ctx.author else f"**Ваши рыбки:** ({page+1} / {pages_count})"
            embed = discord.Embed(
                title=title,
                description=desc,
                color=discord.Color.from_rgb(163, 101, 0),
            )
            embed.set_footer(text=f"Рыбы {member.display_name}", icon_url=member.display_avatar.url)

            try:
                await message.edit(content=None, embed=embed, view=pagination_view)
            except discord.errors.NotFound:
                pass

        message = await ctx.send("Загрузка...")
        await update_page()

    @commands.command(brief="Добавить рыбу в инвентарь (dev)")
    async def addfish(self, ctx: commands.Context, member: discord.Member = None, fish_str: str = None, count: int = 1):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Только администратор может использовать эту команду")
            return
        if member is None:
            member = ctx.author
        if fish_str is None:
            await ctx.send("Вы не указали рыбу")
            return

        fish_str = fish_str.lower()
        fish_pool = small_fish + medium_fish + large_fish
        fish_data = next((f for f in fish_pool if f.name.lower() == fish_str), None)
        if not fish_data:
            await ctx.send("Рыба не найдена")
            return
        embeds = []
        for _ in range(count):
            fish = fish_gen(fish_data)
            db_add_fish(ctx.guild.id, member.id, fish)

            embed = discord.Embed(
                title="Рыба добавлена:",
                description=f"{fish.emoji} **{fish.name}**\n\n"
                            f"> Описание: {fish.description}\n"
                            f"> Цена :moneybag:: {fish.cost}$\n"
                            f"> Размер: {fish.size} см\n",
                color=discord.Color.from_rgb(163, 101, 0),
            )
            embed.set_thumbnail(url=fish_data.image)
            embeds.append(embed)
        if sum([len(emb) for emb in embeds]) < 5000:
            await ctx.send(embeds=embeds)
        else:
            await ctx.send(f"Добавлено {count} рыб ({fish_data.name})")

    @commands.command(brief="Информация о рыбе", aliases=["fishi", "fi", "finfo"])
    async def fishinfo(self, ctx: commands.Context, fish_str: str):
        fish_str = fish_str.lower().strip()
        fish_pool = small_fish + medium_fish + large_fish
        fish_data = next((f for f in fish_pool if f.name.lower() == fish_str), None)
        if not fish_data:
            await ctx.send("Рыба не найдена")
            return

        embed = discord.Embed(
            title="**Информация о рыбе:**",
            description=f"{fish_data.emoji} **{fish_data.name}**\n\n"
                        f"> Описание: {fish_data.description}\n"
                        f"> Средняя цена :moneybag:: {fish_data.cost}$\n"
                        f"> Размер: {fish_data.size[0]}см - {fish_data.size[1]}см\n",
            color=discord.Color.from_rgb(163, 101, 0),
        )
        embed.set_thumbnail(url=fish_data.image)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(FishingCog(bot))
