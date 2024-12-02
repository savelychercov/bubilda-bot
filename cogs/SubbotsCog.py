import os
import subprocess
import discord
from discord.ext import commands, tasks
import config
from library import logger


class BotManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bots_folder = "./subbots"  # Папка с ботами
        if not os.path.exists(self.bots_folder):
            os.makedirs(self.bots_folder)
        self.running_bots = {}  # Словарь для хранения запущенных процессов
        self.event_task = None

    @tasks.loop(seconds=10)
    async def check_subbots(self):
        """
        Периодически проверяет, завершился ли какой-либо бот с ошибкой,
        и отправляет последние сообщения из stdout и stderr.
        """
        with logger.LogAllErrors("Subbots check error:"):
            to_remove = []
            for bot_name, process in self.running_bots.items():
                if process.poll() is not None:  # Проверяем, завершился ли процесс
                    return_code = process.returncode
                    # Считываем остатки stdout и stderr
                    stdout = process.stdout.read() if process.stdout else ""
                    stderr = process.stderr.read() if process.stderr else ""

                    if return_code != 0:
                        # Бот завершился с ошибкой
                        error_message = f"⚠️ Бот `{bot_name}` завершился с ошибкой. Код: {return_code}\n"
                        if stdout:
                            error_message += f"Вывод stdout:\n```\n{stdout.strip()}\n```"
                        if stderr:
                            error_message += f"Вывод stderr:\n```\n{stderr.strip()}\n```"

                        # Отправляем сообщение в Discord
                        logger.log(error_message)

                    else:
                        # Бот завершился успешно
                        logger.log(f"✅ Бот `{bot_name}` завершился успешно.")

                    to_remove.append(bot_name)

            # Удаляем завершившиеся процессы из словаря
            for bot_name in to_remove:
                self.running_bots.pop(bot_name)

    def cog_load(self):
        self.event_task = self.check_subbots.start()

    def cog_unload(self):
        if self.event_task:
            self.event_task.cancel()

    @commands.group(
        name="subbots",
        aliases=["sb", "bots"],
        brief="Выводит список доступных и запущенных ботов (dev)",
        invoke_without_command=True)
    async def list_subbots(self, ctx: commands.Context):
        """
        Выводит список доступных и запущенных ботов.
        """
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return

        bot_folders = [f for f in os.listdir(self.bots_folder) if os.path.isdir(os.path.join(self.bots_folder, f))]
        available_bots = "\n".join(bot_folders) if bot_folders else "Нет доступных ботов."
        running = "\n".join(self.running_bots.keys()) if self.running_bots else "Нет запущенных ботов."
        await ctx.send(f"**Доступные боты:**\n{available_bots}\n\n**Запущенные боты:**\n{running}")

    @list_subbots.command(name="start", brief="Запускает указанного бота (dev)", aliases=["s"])
    async def start_subbot(self, ctx: commands.Context, bot_name: str):
        """
        Запускает указанного бота.
        """
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return

        bot_path = os.path.join(self.bots_folder, bot_name, "main.py")
        bot_dir = os.path.join(self.bots_folder, bot_name)
        if os.name == "posix":
            # venv_path = os.path.join(self.bots_folder, bot_name, "venv", "bin", "python")
            venv_path = os.path.join("venv", "bin", "python")
        elif os.name == 'nt':
            # venv_path = os.path.join(self.bots_folder, bot_name, "venv", "Scripts", "python.exe")
            venv_path = os.path.join("venv", "Scripts", "python.exe")
        else:
            await ctx.send(f"Неподдерживаемая операционная система: {os.name}")
            return
        if not os.path.exists(venv_path):
            await ctx.send(f"Виртуальное окружение для бота `{bot_name}` по пути `{venv_path}` не найдено! Используется python по умолчанию.")
            venv_path = "python"

        if not os.path.exists(bot_path):
            await ctx.send(f"Бот `{bot_name}` не найден!")
            return

        if bot_name in self.running_bots:
            await ctx.send(f"Бот `{bot_name}` уже запущен!")
            return

        try:
            await ctx.send(f"Запускаю бота `{bot_name}`...")
            # Запуск бота с использованием интерпретатора из его виртуального окружения
            process = subprocess.Popen(
                [venv_path, bot_path],  # Используем python из виртуального окружения
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8",
                text=True,
                cwd=bot_dir
            )
            self.running_bots[bot_name] = process
            await ctx.send(f"Бот `{bot_name}` успешно запущен!")
        except Exception as e:
            await ctx.send(f"Ошибка при запуске бота `{bot_name}`: {e}")

    @list_subbots.command(name="stop", brief="Останавливает указанного бота (dev)", aliases=["kill", "k"])
    async def stop_subbot(self, ctx: commands.Context, bot_name: str):
        """
        Останавливает указанного бота.
        """
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return

        if bot_name not in self.running_bots:
            await ctx.send(f"Бот `{bot_name}` не запущен!")
            return

        # Завершаем процесс
        process = self.running_bots.pop(bot_name)
        process.terminate()
        await ctx.send(f"Бот `{bot_name}` остановлен.")

    '''@list_subbots.command(name="log", brief="Выводит лог указанного бота (dev)", aliases=["l"])
    async def subbot_log(self, ctx: commands.Context, bot_name: str):
        """
        Выводит лог указанного бота.
        Если лог больше 2000 символов, отправляет его в виде файла.
        """
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя <:funnycat:1051348714423328778>")
            return

        if bot_name not in self.running_bots:
            await ctx.send(f"Бот `{bot_name}` не запущен!")
            return

        process = self.running_bots[bot_name]
        try:
            # Чтение содержимого stdout и stderr без закрытия потоков
            stdout = process.stdout.read() if process.stdout else ""
            stderr = process.stderr.read() if process.stderr else ""

            log_output = f"**Лог `{bot_name}`:**\n{stdout}\n{stderr}"

            if len(log_output) <= 2000:
                await ctx.send(f"```\n{log_output.strip()}\n```")
            else:
                # Сохраняем лог в файл
                log_file_path = f"{bot_name}_log.txt"
                with open(log_file_path, "w", encoding="utf-8") as log_file:
                    log_file.write(log_output)

                # Отправляем файл в чат
                await ctx.send(
                    content=f"Лог `{bot_name}` слишком большой. Вот файл с логом:",
                    file=discord.File(log_file_path)
                )

                # Удаляем файл после отправки
                os.remove(log_file_path)

        except Exception as e:
            await ctx.send(f"Ошибка при чтении лога для `{bot_name}`: {e}")'''


async def setup(bot):
    await bot.add_cog(BotManagerCog(bot))
