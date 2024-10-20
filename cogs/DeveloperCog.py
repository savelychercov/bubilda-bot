import discord
import traceback
from discord.ext import commands
from config import admin_ids
from memoryV1 import files_db
from memoryV2 import DB
import config
from library.other_tools import loaded_extensions
from library import logger
import sys
import os
import io
import contextlib
import json
from datetime import datetime


backups_path = "backups/"
paths_to_backup = [files_db.files_path, DB.files_path]


def get_backup_str(files: list[str]):
    backup_json = {}
    for name in files:
        with open(name, "r", encoding="utf-8") as f:
            backup_json[name] = f.read()
    return backup_json


def make_backup(backup_name: str):
    if not os.path.exists(backups_path):
        os.makedirs(backups_path)
    filenames = []
    for path in paths_to_backup:
        files_db.check_path(path)
        for filename in os.listdir(path):
            filenames.append(path+filename)
    with open(backups_path + backup_name + ".json", "w+", encoding="utf-8") as f:
        json.dump(get_backup_str(filenames), f)
    return backups_path + backup_name + ".json"


def restore_backup(backup_name: str):
    if not os.path.exists(backups_path) or backup_name not in get_backup_names():
        raise FileNotFoundError
    with open(backups_path + backup_name + ".json", "r", encoding="utf-8") as f:
        backup_json = json.load(f)
    files_db.check_path(files_db.files_path)
    DB.check_path(DB.files_path)
    for name in backup_json:
        with open(name, "w+", encoding="utf-8") as f:
            f.write(backup_json[name])


def get_backup_names():
    if not os.path.exists(backups_path):
        return []
    names = []
    for filename in os.listdir(backups_path):
        names.append(filename.replace(".json", ""))
    return names


def delete_backup(backup_name: str):
    if not os.path.exists(backups_path) or backup_name not in get_backup_names():
        raise FileNotFoundError
    os.remove(backups_path + backup_name + ".json")


def clear_data():
    for path in paths_to_backup:
        if not os.path.exists(path):
            continue
        for filename in os.listdir(path):
            os.remove(path + filename)


class ConfigConfirmButtons(discord.ui.View):
    def __init__(self, newlines: list[str], message: discord.Message):
        self.lines = newlines
        self.message = message
        super().__init__(timeout=30)
        confirm_button = discord.ui.Button(label="Подтвердить", style=discord.ButtonStyle.green, emoji="✅")
        confirm_button.callback = self.confirm_callback
        self.add_item(confirm_button)
        cancel_button = discord.ui.Button(label="Отмена", style=discord.ButtonStyle.gray, emoji="❌")
        cancel_button.callback = self.cancel_callback
        self.add_item(cancel_button)

    async def interaction_check(self, interaction: discord.Interaction):
        response: discord.InteractionResponse = interaction.response
        followup: discord.Webhook = interaction.followup
        await response.defer()
        if interaction.user.id in admin_ids:
            return True
        else:
            await followup.send("Низя", ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        await self.message.edit(content="Действие отменено по истечению времени", view=None)
        self.stop()

    async def confirm_callback(self, interaction: discord.Interaction):
        followup: discord.Webhook = interaction.followup
        with open('config.py', 'w') as file:
            file.writelines(self.lines)
        await self.message.edit(view=None)
        await followup.send(f"Действие подтверждено. Чтобы применить изменения - {config.prefix}restart")
        self.stop()

    async def cancel_callback(self, interaction: discord.Interaction):
        followup: discord.Webhook = interaction.followup
        await self.message.edit(view=None)
        await followup.send("Отменено")
        self.stop()


class DeveloperCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "DEV"
        self.__cog_description__ = "Приколы управления когами бубылды"
        self.bot: commands.Bot = bot

    @commands.group(brief="Показать бекапы (dev)", invoke_without_command=True)
    async def backups(self, ctx: commands.Context):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
            return
        backups = get_backup_names()
        if len(backups) == 0:
            await ctx.send("Нет бекапов")
            return
        embed = discord.Embed(
            color=discord.Color.blurple(),
            description="- "+"\n- ".join(backups),
            title="**Бекапы**")
        await ctx.send(embed=embed)

    @backups.command(brief="Сделать бекап (dev)")
    async def make(self, ctx: commands.Context, name: str = None):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
        if name is None:
            name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        if name in get_backup_names():
            await ctx.send("Бекап с таким именем уже существует")
            return
        make_backup(name)
        await ctx.send("Бекап создан")

    @backups.command(brief="Восстановить бекап (dev)")
    async def restore(self, ctx: commands.Context, name: str):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
        try:
            name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
            make_backup(name)
            await ctx.send(f"Бекап создан с именем {name}")
            clear_data()
            restore_backup(name)
            await ctx.send(f"Бекап с именем {name} восстановлен")
        except FileNotFoundError:
            await ctx.send(f"Бекап с именем {name} не найден")
            raise

    @backups.command(brief="Удалить бекап (dev)")
    async def delete(self, ctx: commands.Context, name: str):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
        try:
            delete_backup(name)
        except FileNotFoundError:
            await ctx.send(f"Бекап с именем {name} не найден")
            return
        await ctx.send(f"Бекап с именем {name} удален")

    @backups.command(brief="Получить бекап (dev)")
    async def send(self, ctx: commands.Context, name: str):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
        if name not in get_backup_names():
            await ctx.send(f"Бекап с именем {name} не найден")
            return
        await ctx.send(file=discord.File(backups_path + name + ".json"))

    @backups.command(brief="Загрузить бекап (dev)", name="load")
    async def load_backup_command(self, ctx: commands.Context):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
        if not ctx.message.attachments:
            await ctx.send("Прикрепите файл бекапа")
            return
        file = ctx.message.attachments[0]
        if file.filename in get_backup_names():
            await ctx.send("Бекап c таким именем уже существует")
            return
        await file.save(backups_path + file.filename)
        await ctx.send(f"Бекап с именем {file.filename} загружен")

    @backups.command(brief="Загрузить пустой бекап (dev)")
    async def clear(self, ctx: commands.Context):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
        name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        make_backup(name)
        clear_data()
        await ctx.send(f"Бекап с именем {name} создан, все данные очищены")

    @commands.command(brief="Изменить никнейм (dev)")
    async def changenick(self, ctx, member: discord.Member, *, nickname):
        if ctx.author.id in admin_ids:
            try:
                await member.edit(nick=nickname)
                await ctx.send("Ник " + str(member.name) + " изменен на " + str(nickname))
            except:
                await ctx.send("Низя")
        else:
            await ctx.send("Низя")

    @commands.command(brief="Получить стек вызовов (dev)", aliases=["trace", "tb"])
    async def traceback(self, ctx: commands.Context, t: str = "new"):
        if ctx.author.id in admin_ids:
            if t == "new":
                await ctx.send(f"```py\n{traceback.format_exc()}```")
            elif t == "last":
                await ctx.send(f"```py\n{config.last_traceback}```")
            else:
                await ctx.send("Непон")
        else:
            await ctx.send("Низя")

    @commands.command(brief="Изменить количество денег (dev)")
    async def setbalance(self, ctx, user: discord.User, money):
        if ctx.author.id in admin_ids:
            try:
                filename = str(ctx.guild.id)
                user = str(user.id)
                money = float(money)
                files_db.BalanceData.set_balance(filename, user, money)
            except:
                await ctx.send("Чота нетак")
        else:
            await ctx.send("Низя")

    @commands.command(brief="Вызвать ошибку (dev)")
    async def errortest(self, ctx: commands.Context):
        try:
            a = 1 / 0
        except Exception as e:
            raise e
        finally:
            await ctx.send("Ошибка создана")

    @commands.command(brief="Остановка бота (dev)", aliases=["stop"])
    async def shutdown(self, ctx: commands.Context):
        if ctx.author.id not in admin_ids:
            await ctx.send("Не балуйся")

        embed = discord.Embed(
            color=discord.Color.blurple(),
            title="**Остановка**")
        await ctx.send(embed=embed)
        await self.bot.close()
        sys.exit(1)

    @commands.group(invoke_without_command=True, brief="Работа с когами (dev)", aliases=["cog"])
    async def cogs(self, ctx):
        msg = ""
        for name in config.loaded_cogs:
            if name.find("_") != -1:
                msg = f"{msg}• {name}\n"
            else:
                msg = f"{msg}• {name}\n"
        embed = discord.Embed(
            color=discord.Color.blurple(),
            title="Загруженные коги:",
            description=msg)
        await ctx.send(embed=embed)

    @cogs.command(brief="Перезагрузить коги (dev)", aliases=["rel", "r"])
    async def reload(self, ctx: commands.Context):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
            return

        try:
            for cog in config.loaded_cogs:
                await self.bot.unload_extension(f"cogs.{cog}")
            for cog in loaded_extensions():
                await self.bot.load_extension(f"cogs.{cog}")
            await ctx.send("Коги перезагружены")

        except Exception as e:
            await ctx.author.send("Ошибка перезагрузки когов:\n```py\n" + traceback.format_exc() + "```")

    @cogs.command(brief="Загрузить ког (dev)", aliases=["l"])
    async def load(self, ctx, directory="cogs"):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
            return
        if not ctx.message.attachments:
            await ctx.send("Прикрепи файл сначала")
            return
        try:
            for attach in ctx.message.attachments:
                await attach.save(f"{directory}/{attach.filename}")
                await ctx.send(f'Файл "{attach.filename}" загружен в {directory}')
        except Exception as e:
            logger.err(e, "Ошибка загрузки файла")

    @cogs.command(brief="Удалить ког (dev)", aliases=["rm", "delete"])
    async def remove(self, ctx, filename=None):
        if ctx.author.id in admin_ids:
            if filename is None:
                await ctx.send("Введи название файла дуралей")
                return
            try:
                os.remove(f"cogs/{filename}")
                await ctx.send(f'Файл "{filename}" удален')
            except:
                await ctx.send("Нет такова")
        else:
            await ctx.send("Низя")

    @commands.command(name='exec', brief="Выполнить код (dev)")
    async def exec_code(self, ctx: commands.Context, *, code: str):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
            return
        str_io = io.StringIO()
        with contextlib.redirect_stdout(str_io):
            try:
                exec(code)
                output = str_io.getvalue()
                if output:
                    await ctx.send(f'Результат:\n```\n{output}\n```')
                else:
                    await ctx.send('Код выполнен без вывода.')
            except Exception as e:
                logger.err(e, "Exec code error\n")
                await ctx.send(f'Ошибка:\n```\n{e}\n```')

    last_config_lines: list[str] = None
    last_config_change: str = None

    @commands.group(brief="Показать переменные конфига (dev)", invoke_without_command=True)
    async def config(self, ctx: commands.Context):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
            return
        not_show = ["prefix", "token", "prefix", "last_traceback", "LazyBubilda", "Bubilda", "loaded_cogs", "coins",
                    "filekeys", "libs", "guild_roles", "measure"]
        config_vars = {key: value for key, value in vars(config).items() if not key.startswith('__')}
        config_str = "• " + "\n• ".join(
            f"{key} = {repr(value)}" for key, value in config_vars.items() if key not in not_show)
        await ctx.send(f"Доступные для редактирования переменные:\n```py\n{config_str}```")

    @config.command(name="replace", brief="Заменить значение конфига (dev)", aliases=["edit"])
    async def replace_arg(self, ctx: commands.Context, variable_name: str = None, new_value: str = None):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
            return

        if not variable_name:
            await ctx.send(f"Укажите имя переменной из {config.prefix}config")
            return

        if not new_value:
            await ctx.send(f"Укажите новое значение")
            return

        try:
            new_value = eval(new_value)
        except NameError:
            pass

        with open('config.py', 'r') as file:
            lines = file.readlines()
            self.last_config_lines = lines.copy()

        variable_line = next((line for line in lines if line.startswith(variable_name)), None)

        if variable_line:
            old_value = getattr(config, variable_name)
            warning = ""
            if not type(new_value) == type(old_value):
                warning = f"Тип нового значения не совпадает со старым: {type(new_value)} != {type(old_value)}"

            index = lines.index(variable_line)
            new_line = f"{variable_name} = {repr(new_value)}\n"
            lines[index] = new_line
            message = await ctx.send("Загрузка...")
            self.last_config_change = f"```py\n{variable_line}\n˅˅˅\n{new_line}```"
            await message.edit(
                content=f"Значение переменной будет изменено на:\n{self.last_config_change}\n{warning}",
                view=ConfigConfirmButtons(newlines=lines, message=message))
        else:
            await ctx.send(f"Переменная '{variable_name}' не найдена в файле config.py.")

    @config.command(brief="Отменить изменения конфига (dev)", aliases=["undo"])
    async def cancel(self, ctx: commands.Context):
        if ctx.author.id not in admin_ids:
            await ctx.send("Низя")
            return

        if self.last_config_lines is not None:
            message = await ctx.send("Загрузка...")
            await message.edit(
                content=f"Отмена последнего изменения конфига:\n{self.last_config_change}",
                view=ConfigConfirmButtons(newlines=self.last_config_lines, message=message))
        else:
            await ctx.send("Нечего отменять")
            return


async def setup(bot):
    await bot.add_cog(DeveloperCog(bot))
