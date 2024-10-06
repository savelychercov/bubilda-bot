import discord
from discord import Interaction
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import datetime
from dataclasses import dataclass
import random
from memoryV2.DB import DefinedDataBase
from library import tiles_lib
# from library.logger import err


# region config
temp_path = "memoryV2/"

image_size = (500, 665)
grid_size = 4

background_color = (255, 255, 255)
text_color = (255, 200, 255)
text_background_color = (100, 10, 100)
grid_color = (66, 66, 66)
grid_line_size = 2

font_path = "library/nyashasans.ttf"
font = ImageFont.truetype(font_path, 20)

update_every = 12  # hours
tile_increase_chance = 0.2
# endregion


# region game logic
@dataclass
class MergeGame:
    tiles: list[tuple[str, int, int]]
    earned_money: int
    total_money: int
    last_update: datetime.datetime


db = DefinedDataBase(int, MergeGame, "merge_game")


def get_remaining_time(game: MergeGame) -> datetime.timedelta:
    return datetime.datetime.now() - game.last_update + datetime.timedelta(hours=update_every)


def update_game(game: MergeGame):
    while datetime.datetime.now() >= (ut := game.last_update + datetime.timedelta(hours=update_every)):
        earned_today = tiles_lib.calculate_daily_money(game)
        tile_to_add = generate_new_tile(game)
        if tile_to_add: game.tiles.append(tile_to_add)
        game.earned_money += earned_today
        game.total_money += earned_today
        game.last_update = ut


def random_empty_cell(game: MergeGame) -> tuple[int, int]:
    empty_cells_list = empty_cells(game)
    if empty_cells_list:
        return random.choice(empty_cells_list)
    else:
        return None


def generate_new_tile(game: MergeGame) -> tuple[str, int, int]:
    tile_pos = random_empty_cell(game)
    if not tile_pos: return None
    tile_level = 1
    while random.random() < tile_increase_chance and tile_level < 3:
        tile_level += 1
    return tiles_lib.get_tile_by_level(tile_level).name, *tile_pos


def empty_cells(game: MergeGame) -> list[tuple[int, int]]:
    empty_cells_list = []
    for y in range(grid_size):
        for x in range(grid_size):
            if (x, y) not in [(tx, ty) for (name, tx, ty) in game.tiles]:
                empty_cells_list.append((x, y))
    return empty_cells_list


def chosen_cells(game: MergeGame) -> list[tuple[int, int]]:
    return [(x, y) for (name, x, y) in game.tiles]


def remove_tile_pos(game: MergeGame, tile_pos: tuple[int, int]):
    game.tiles = [(name, x, y) for (name, x, y) in game.tiles if (x, y) != tile_pos]


def save_game(guild_id, user_id, game: MergeGame):
    db.set_obj(guild_id, user_id, game)


def load_game(guild_id, user_id) -> MergeGame:
    game = db.get_obj(guild_id, user_id)
    if game is None:
        game = MergeGame([], 0, 0, datetime.datetime.now())
        db.set_obj(guild_id, user_id, game)
    return game
# endregion


# region calculations
def number(x, y): return y * grid_size + x + 1


def pos(num):
    return (num - 1) % grid_size, (num - 1) // grid_size


def margin(top_left: tuple[int, int],
           bottom_right: tuple[int, int],
           margin_size: int) -> tuple[tuple[int, int], tuple[int, int]]:
    new_tl = (top_left[0] + margin_size, top_left[1] + margin_size)
    new_br = (bottom_right[0] - margin_size, bottom_right[1] - margin_size)
    return new_tl, new_br


def center(top_left: tuple[int, int],
           bottom_right: tuple[int, int]) -> tuple[int, int]:
    x = (top_left[0] + bottom_right[0]) // 2
    y = (top_left[1] + bottom_right[1]) // 2
    return x, y


def resize_to_pos(image: Image, top_left: tuple[int, int], bottom_right: tuple[int, int]):
    square_size = min(bottom_right[0] - top_left[0], bottom_right[1] - top_left[1])
    small_image = image.resize((square_size, square_size))
    return small_image


def center_bottom(top_left: tuple[int, int],
                  bottom_right: tuple[int, int]) -> tuple[int, int]:
    x = (top_left[0] + bottom_right[0]) // 2
    y = bottom_right[1]
    return x, y
# endregion


# region drawing
async def new_image(img_size: tuple[int, int]) -> Image:
    image = Image.new("RGB", img_size, background_color)
    return image


async def draw_grid(
        image: Image,
        left_top: tuple[int, int],
        right_bottom: tuple[int, int]) -> tuple[Image, list[tuple[tuple[int, int], tuple[int, int]]]]:
    draw = ImageDraw.Draw(image)

    right_top = (right_bottom[0], left_top[1])
    left_bottom = (left_top[0], right_bottom[1])
    width = right_bottom[0] - left_top[0]
    height = right_bottom[1] - left_top[1]
    step_x = width // grid_size
    step_y = height // grid_size
    x_shift = left_top[0]
    y_shift = left_top[1]

    # Позиции клеток: (top_left, bottom_right)
    cells = []

    for x in range(0, width, step_x):
        cells.append([])
        for y in range(0, height, step_y):
            cell = (x+x_shift, y+y_shift), (x+x_shift+step_x, y+y_shift+step_y)
            cells[-1].append(cell)

    for x in range(0, width, step_x):
        draw.line([(x+x_shift, y_shift), (x+x_shift, height+y_shift)], fill=grid_color, width=grid_line_size)
    for y in range(0, height, step_y):
        draw.line([(x_shift, y+y_shift), (width+x_shift, y+y_shift)], fill=grid_color, width=grid_line_size)

    draw.line([left_top, right_top], fill=grid_color, width=grid_line_size)
    draw.line([right_top, right_bottom], fill=grid_color, width=grid_line_size)
    draw.line([right_bottom, left_bottom], fill=grid_color, width=grid_line_size)
    draw.line([left_bottom, left_top], fill=grid_color, width=grid_line_size)

    # Сохраняем изображение
    return image, cells


async def draw_numbers(image: Image, cells: list[tuple[tuple[int, int], tuple[int, int]]]):
    draw = ImageDraw.Draw(image)
    for x in range(grid_size):
        for y in range(grid_size):
            text_pos = cells[x][y][0]
            draw.text((text_pos[0]+5, text_pos[1]+5), align="left", anchor="lt", text=str(number(x, y)), fill=grid_color, font=font)
    return image


async def draw_game(image: Image, cells: list[tuple[tuple[int, int], tuple[int, int]]], game: MergeGame):
    draw = ImageDraw.Draw(image)
    for (name, x, y) in game.tiles:
        tile = tiles_lib.get_tile_by_name(name)
        if tile is None:
            text_pos = center(*cells[x][y])
            draw.rectangle(margin(*cells[x][y], 15), fill=text_background_color, width=15)
            draw.text(text_pos, align="center", anchor="mm", text=name.lower(), fill=text_color, font=font)
            continue
        tile_image = Image.open(tile.image_path)
        tile_image = resize_to_pos(tile_image, *cells[x][y])
        image.paste(tile_image, cells[x][y][0], tile_image)
        text_pos = center_bottom(*cells[x][y])
        back_pos_tl = (
            cells[x][y][0][0]+1,
            cells[x][y][0][1]+(cells[x][y][1][1]-cells[x][y][0][1])-20
        )
        draw.rectangle(margin(back_pos_tl, cells[x][y][1], 2), fill=text_background_color, width=15)
        draw.text(text_pos,
                  align="center", anchor="mb",
                  text=name, fill=text_color, font=font)
    return image


async def draw_info(image: Image, game: MergeGame, top_left: tuple[int, int], bottom_right: tuple[int, int]):
    draw = ImageDraw.Draw(image)
    text_pos = (top_left[0] + 10, top_left[1] + 10)
    # formate timedelta (get_remaining_time(game)) to HH:MM
    remaining = str(datetime.datetime(1, 1, 1) + get_remaining_time(game))[11:16]
    text = (f"Заработано: {game.earned_money}$\n"
            f"В день: {tiles_lib.calculate_daily_money(game)}$\n"
            f"За всё время: {game.total_money}$\n"
            f"Осталось: {remaining}")
    draw.rectangle(margin(top_left, bottom_right, 5), fill=text_background_color)
    draw.text(text_pos, align="left", text=text, fill=text_color, font=font)
    return image


async def refresh_image(message: discord.Message, user: discord.User, guild: discord.Guild):
    image_name = temp_path + str(user.id) + "merge_game.png"
    image = await new_image(image_size)
    image, cells = await draw_grid(image, *margin((0, 0), (image_size[0], image_size[0]), 10))
    game = load_game(guild.id, user.id)
    update_game(game)
    image = await draw_game(image, cells, game)
    image = await draw_info(image, game, (10, image_size[0] + 10), (image_size[0] - 10, image_size[1] - 10))
    image = await draw_numbers(image, cells)
    image.save(image_name)
    view = MergeGameView(game, message, user)
    await message.edit(content=None, attachments=[discord.File(image_name)], view=view)
# endregion


# region Views
class MoveOptionsView(discord.ui.View):
    def __init__(self, game: MergeGame, move_message: discord.Message, game_message: discord.Message, user: discord.User):
        super().__init__()
        self.game = game
        self.move_message = move_message
        self.game_message = game_message
        self.user = user

        self.tile_selector = discord.ui.Select(
            placeholder="Выберите плитку",
            options=[
                discord.SelectOption(label=f"{name} ({number(x, y)})", value=repr((name, x, y))) for (name, x, y) in game.tiles
            ]
        )
        self.add_item(self.tile_selector)

        self.cell_selector = discord.ui.Select(
            placeholder="Выберите ячейку",
            options=[
                discord.SelectOption(label=f"{number(x, y)}", value=str(number(x, y))) for (x, y) in empty_cells(game)
            ]
        )
        self.add_item(self.cell_selector)

    @discord.ui.button(label="Переместить", style=discord.ButtonStyle.green, row=2)
    async def move_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        followup: discord.Webhook = interaction.followup
        if not self.tile_selector.values:
            await followup.send("Нужно выбрать плитку", ephemeral=True)
            return
        tile_name, x, y = eval(self.tile_selector.values[0])
        if not self.cell_selector.values:
            await followup.send("Нужно выбрать ячейку", ephemeral=True)
            return
        new_x, new_y = pos(int(self.cell_selector.values[0]))
        self.game.tiles.remove((tile_name, int(x), int(y)))
        self.game.tiles.append((tile_name, new_x, new_y))
        save_game(interaction.guild.id, interaction.user.id, self.game)
        await self.move_message.edit(
            content=f"Плитка {tile_name} перемещена в ячейку №{number(new_x, new_y)}",
            view=None
        )
        await refresh_image(self.game_message, interaction.user, interaction.guild)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.gray, row=2)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.move_message.edit(
            content=f"Перемещение отменено",
            view=None
        )

    class MoveOptionsView(discord.ui.View):
        def __init__(self, game: MergeGame, move_message: discord.Message, game_message: discord.Message,
                     user: discord.User):
            super().__init__()
            self.game = game
            self.move_message = move_message
            self.game_message = game_message
            self.user = user

            self.tile_selector = discord.ui.Select(
                placeholder="Выберите плитку",
                options=[
                    discord.SelectOption(label=f"{name} ({number(x, y)})", value=repr((name, x, y))) for (name, x, y) in
                    game.tiles
                ]
            )
            self.add_item(self.tile_selector)

            self.cell_selector = discord.ui.Select(
                placeholder="Выберите ячейку",
                options=[
                    discord.SelectOption(label=f"{number(x, y)}", value=str(number(x, y))) for (x, y) in
                    empty_cells(game)
                ]
            )
            self.add_item(self.cell_selector)

        @discord.ui.button(label="Переместить", style=discord.ButtonStyle.green, row=2)
        async def move_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            followup: discord.Webhook = interaction.followup
            if not self.tile_selector.values:
                await followup.send("Нужно выбрать плитку", ephemeral=True)
                return
            tile_name, x, y = eval(self.tile_selector.values[0])
            if not self.cell_selector.values:
                await followup.send("Нужно выбрать ячейку", ephemeral=True)
                return
            new_x, new_y = pos(int(self.cell_selector.values[0]))
            self.game.tiles.remove((tile_name, int(x), int(y)))
            self.game.tiles.append((tile_name, new_x, new_y))
            save_game(interaction.guild.id, interaction.user.id, self.game)
            await self.move_message.edit(
                content=f"Плитка {tile_name} перемещена в ячейку №{number(new_x, new_y)}",
                view=None
            )
            await refresh_image(self.game_message, interaction.user, interaction.guild)

        @discord.ui.button(label="Отмена", style=discord.ButtonStyle.gray, row=2)
        async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.move_message.edit(
                content=f"Перемещение отменено",
                view=None
            )

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        response: discord.InteractionResponse = interaction.response
        await response.defer()
        check = interaction.user.id == self.user.id
        if not check:
            await response.send_message("Нет братан", ephemeral=True)
        return check


class CombineOptionsView(discord.ui.View):
    def __init__(self, game: MergeGame, comb_message: discord.Message, game_message: discord.Message, user: discord.User):
        super().__init__()
        self.game = game
        self.comb_message = comb_message
        self.game_message = game_message
        self.user = user

        self.tile1_selector = discord.ui.Select(
            placeholder="Выберите первую плитку",
            options=[
                discord.SelectOption(label=f"{name} ({number(x, y)})", value=repr((name, x, y))) for (name, x, y) in game.tiles
            ]
        )
        self.add_item(self.tile1_selector)

        self.tile2_selector = discord.ui.Select(
            placeholder="Выберите вторую плитку",
            options=[
                discord.SelectOption(label=f"{name} ({number(x, y)})", value=repr((name, x, y))) for (name, x, y) in game.tiles
            ]
        )
        self.add_item(self.tile2_selector)

    @discord.ui.button(label="Комбинировать", style=discord.ButtonStyle.green, row=2)
    async def combine_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        followup: discord.Webhook = interaction.followup
        if not self.tile1_selector.values:
            await followup.send("Нужно выбрать первую плитку", ephemeral=True)
            return
        tile1_name, x1, y1 = eval(self.tile1_selector.values[0])
        if not self.tile2_selector.values:
            await followup.send("Нужно выбрать вторую плитку", ephemeral=True)
            return
        tile2_name, x2, y2 = eval(self.tile2_selector.values[0])

        if tile1_name != tile2_name:
            await followup.send("Можно комбинировать только одинаковые плитки", ephemeral=True)
            return

        elif (tile1_name, x1, y1) == (tile2_name, x2, y2):
            await followup.send("Нельзя комбинировать плитку саму с собой", ephemeral=True)
            return

        try:
            new_tile = tiles_lib.get_tile_by_level(tiles_lib.get_tile_level(tile1_name)+1)
        except ValueError:
            await followup.send("Максимальный уровень плитки достигнут (возможно в будущем добавят больше плиток)", ephemeral=True)
            return

        self.game.tiles.remove((tile1_name, x1, y1))
        self.game.tiles.remove((tile2_name, x2, y2))
        self.game.tiles.append((new_tile.name, x1, y1))
        save_game(interaction.guild.id, interaction.user.id, self.game)
        await self.comb_message.edit(
            content=f"Плитки {tile1_name} и {tile2_name} объединены в плитку {new_tile.name}",
            view=None
        )
        await refresh_image(self.game_message, interaction.user, interaction.guild)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.gray, row=2)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.comb_message.edit(
            content=f"Комбинирование отменено",
            view=None
        )

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        response: discord.InteractionResponse = interaction.response
        await response.defer()
        check = interaction.user.id == self.user.id
        if not check:
            await response.send_message("Нет братан", ephemeral=True)
        return check


class InfoOptionsView(discord.ui.View):
    def __init__(self, game: MergeGame, info_message: discord.Message, game_message: discord.Message, user: discord.User):
        super().__init__()
        self.game = game
        self.info_message = info_message
        self.game_message = game_message
        self.user = user

        self.info_selector = discord.ui.Select(
            placeholder="Выберите плитку",
            options=[
                discord.SelectOption(label=f"{name} ({number(x, y)})", value=repr((name, x, y))) for (name, x, y) in game.tiles
            ]
        )
        self.add_item(self.info_selector)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.gray, row=2)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.info_message.delete()

    @discord.ui.button(label="Информация", style=discord.ButtonStyle.green, row=2)
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        followup: discord.Webhook = interaction.followup
        if not self.info_selector.values:
            await followup.send("Нужно выбрать плитку", ephemeral=True)
            return
        tile_name, x, y = eval(self.info_selector.values[0])
        tile = tiles_lib.get_tile_by_name(tile_name)
        embed = discord.Embed(
            title=tile.name,
            color=discord.Color.dark_magenta(),
            description=tile.info+f"\nСейчас производит: {tile.calc_daily_money(self.game, x, y)}$"
        )
        await followup.send(embed=embed)

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        response: discord.InteractionResponse = interaction.response
        await response.defer()
        check = interaction.user.id == self.user.id
        if not check:
            await response.send_message("Нет братан", ephemeral=True)
        return check


class MergeGameView(discord.ui.View):
    def __init__(self, game: MergeGame, message: discord.Message, user: discord.User):
        super().__init__(timeout=60*10)
        self.game = game
        self.message = message
        self.user = user

    async def on_timeout(self) -> None:
        save_game(self.message.guild.id, self.user.id, self.game)
        await self.message.edit(view=None)
        self.stop()

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        response: discord.InteractionResponse = interaction.response
        await response.defer()
        check = interaction.user.id == self.user.id
        if not check:
            await response.send_message("Нет братан", ephemeral=True)
        return check

    @discord.ui.button(label=None, style=discord.ButtonStyle.blurple, emoji="❌", row=0)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        save_game(self.message.guild.id, self.user.id, self.game)
        await self.message.edit(view=None)
        self.stop()

    @discord.ui.button(label=None, style=discord.ButtonStyle.blurple, emoji="🔄", row=0)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await refresh_image(self.message, interaction.user, interaction.guild)

    @discord.ui.button(label="MOVE", style=discord.ButtonStyle.primary, row=1)
    async def move_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        move_message = await interaction.channel.send("Выберите плитку и ячейку")
        view = MoveOptionsView(self.game, move_message, self.message, self.user)
        await move_message.edit(view=view)

    @discord.ui.button(label="COMBINE", style=discord.ButtonStyle.primary, row=1)
    async def comb_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        comb_message = await interaction.channel.send("Выберите плитки для комбинирования")
        view = CombineOptionsView(self.game, comb_message, self.message, self.user)
        await comb_message.edit(view=view)

    @discord.ui.button(label="INFO", style=discord.ButtonStyle.danger, row=1)
    async def info_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        info_message = await interaction.channel.send("Выберите плитку о которой хотите получить информацию")
        view = InfoOptionsView(self.game, info_message, self.message, self.user)
        await info_message.edit(view=view)

# endregion


# region cog
class MergeCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Игрульки"
        self.__cog_description__ = "Команды для запуска игр"
        self.bot = bot

    @commands.command(aliases=["m"])
    async def merge(self, ctx: commands.Context):
        message = await ctx.send("<:emj:1268135319945875581> Щас всё будет...")
        await refresh_image(message, ctx.author, ctx.guild)

    @commands.command(name="settile", aliases=["st"])
    async def set_tile(self, ctx: commands.Context, name: str = "smol", num: int = 1, user: discord.Member = None):
        if num > grid_size**2 or num < 1:
            await ctx.send(f"Цифра не на поле, введите число от 1 до {grid_size**2}")
            return
        user = user or ctx.author
        game = load_game(ctx.guild.id, user.id)
        if pos(num) in chosen_cells(game):
            remove_tile_pos(game, pos(num))
        game.tiles.append((name, *pos(num)))
        save_game(ctx.guild.id, user.id, game)
        await ctx.send(f"Тайл {name} добавлен на {num} клетку")

    @commands.command(name="deltile", aliases=["rt"])
    async def del_tile(self, ctx: commands.Context, num: int = 1, user: discord.Member = None):
        user = user or ctx.author
        game = load_game(ctx.guild.id, user.id)
        if pos(num) in chosen_cells(game):
            remove_tile_pos(game, pos(num))
        save_game(ctx.guild.id, user.id, game)
        await ctx.send(f"Тайл удален с {num} клетки")


async def setup(bot):
    await bot.add_cog(MergeCog(bot))
# endregion
