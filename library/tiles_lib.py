from types import MethodType

image_folder = "library/images/"


tiles = []


def tile(name: str, daily_money: int, image_path: str = None) -> callable:
    def decorator(func):
        new_tile = Tile(name, daily_money, image_path, func.__doc__)
        new_tile.calc_daily_money = MethodType(func, new_tile)
        tiles.append(new_tile)
    return decorator


class Tile:
    def __init__(self, name: str, daily_money: int, image_path: str, info: str):
        self.name = name
        self.daily_money = daily_money
        self.image_path = image_path
        self.info = info

    def __str__(self):
        return self.name

    def calc_daily_money(self, game, x: int, y: int):
        raise NotImplementedError("Not implemented yet")


def get_tile_by_name(name: str) -> Tile:
    for t in tiles:
        if t.name == name:
            return t
    return None


def get_tile_level(name: str) -> int:
    for i in range(len(tiles)):
        if tiles[i].name == name:
            return i + 1
    return 0


def get_tile_by_level(level: int) -> Tile:
    if level > len(tiles) or level < 1:
        raise ValueError("Level out of range")
    return tiles[level - 1]


def calculate_daily_money(game):
    count_money = 0
    for (name, x, y) in game.tiles:
        tile_obj = get_tile_by_name(name)
        if tile_obj is None:
            continue
        count_money += tile_obj.calc_daily_money(game, x, y)
    return count_money


def get_tile_on_pos(game, x: int, y: int) -> Tile:
    for (name, tile_x, tile_y) in game.tiles:
        if x == tile_x and y == tile_y:
            return get_tile_by_name(name)
    return None


def get_near_tiles(game, x: int, y: int) -> list[str]:
    near = []
    for x, y in [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]:
        near_tile = get_tile_on_pos(game, x, y)
        if near_tile is not None:
            near.append((near_tile.name, x, y))
    return near


@tile("Smol", 1, image_folder+"cat1.png")
def smol(self: Tile, game, x: int, y: int):
    """
    Обычная плитка, появляется каждые 12 часов на случайной свободной клетке
    Производит 1$ за 12 часов
    """
    return self.daily_money


@tile("Mini", 3, image_folder+"cat2.png")
def mini(self: Tile, game, x: int, y: int):
    """
    Плитка покруче, может появиться случайно вместо обычной плитки
    Производит 3$ за 12 часов
    """
    return self.daily_money


@tile("Pot", 7, image_folder+"cat3.png")
def pot(self: Tile, game, x: int, y: int):
    """
    Нормальная плитка, может появиться случайно вместо обычной плитки
    Производит 7$ за 12 часов, дает 2$ за каждую такую же плитку рядом
    """
    return self.daily_money + [name for name, x, y in get_near_tiles(game, x, y)].count(self.name)*2
