import discord
from typing import Literal
from memoryV2.DB import DataBase
import random
import config
from datetime import datetime, timedelta
from os import listdir

T_COLOR = Literal['blue', 'blurple', 'default', 'fuchsia', 'gold', 'green', 'greyple', 'magenta', 'orange', 'pink',
    'purple', 'random', 'red', 'teal', 'yellow']

all_colors = ['blue', 'blurple', 'default', 'fuchsia', 'gold', 'green', 'greyple', 'magenta', 'orange', 'pink',
              'purple', 'random', 'red', 'teal', 'yellow']

"""for color in dir(discord.Colour):
    if "_" not in color and color not in ["value", "b", "g", "r"]:
        all_colors.append(color)"""


def get_discord_color(color: T_COLOR) -> discord.Colour:
    if color in all_colors:
        return getattr(discord.Colour, color)()
    else:
        return discord.Colour.default()


def loaded_extensions():
    return [name[:-3] for name in listdir('./cogs') if name.endswith('.py')]


def get_random_time(min_hours: int, max_hours: int):
    if max_hours == 0:
        hours = 0
    elif min_hours+1-max_hours == 0:
        hours = min_hours
    else:
        hours = random.randint(min_hours, max_hours - 1)

    if config.random_minutes > 0:
        minutes = random.randint(0, config.random_minutes)
    else: minutes = 0

    next_event_time = datetime.now() + timedelta(
        hours=hours,
        minutes=minutes,
        seconds=10)
    return next_event_time


EventTimeDB = DataBase("event_time")


class EventTimeClass:
    def __init__(self):
        self.time_format = "%Y-%m-%d %H:%M:%S.%f"
        self.next_event_time: datetime = self.read_time()
        if self.next_event_time is None or self.next_event_time < datetime.now():
            self.update_time()

    def get_time(self) -> datetime:
        return self.next_event_time

    def check_time(self) -> bool:
        if self.next_event_time < datetime.now():
            self.update_time()
            return True
        return False

    def read_time(self) -> datetime:
        if EventTimeDB.read_key("", "time") is None:
            return None
        time_str = EventTimeDB.read_key("", "time").strip()
        if time_str is None:
            return None
        return datetime.strptime(time_str, self.time_format)

    def update_time(self) -> None:
        self.next_event_time = get_random_time(config.min_send_time, config.max_send_time)
        EventTimeDB.new_key("", "time", self.next_event_time.strftime(self.time_format))


EventTime = EventTimeClass()


if __name__ == "__main__":
    raise NotImplementedError("this file should not be run directly")
