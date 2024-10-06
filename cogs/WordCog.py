import traceback
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord import app_commands
import wordcloud
from library import logger
from config import admin_ids

stop_words = [
    "я",
    "ты",
    "он",
    "она",
    "мы",
    "вы",
    "они",
    "что",
    "как",
    "в",
    "к",
    "на",
    "из",
    "то",
    "от",
    "с",
    "до",
    "не",
    "но",
    "за",
    "по",
    "да",
    "это",
    "а",
    "и",
    "ну",
    "тебе",
    "нет",
    "тебя",
    "меня",
    "мне",
    "вас",
    "cloud",
    "у",
    "b",
]


class WordCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Ког облака слов"
        self.__cog_description__ = "Содержит команды для создания облака слов из сообщений в чате"
        self.bot = bot

    @commands.group(brief="Создать облако слов", invoke_without_command=True)
    async def cloud(self, ctx: commands.Context, count=500):
        if count < 1:
            await ctx.send("Минимальное количество сообщений: 1")
            return
        if count > 5000 and ctx.author.id not in admin_ids:
            await ctx.send("Максимальное количество сообщений: 5000")
            return

        send_message = await ctx.send("Собираю сообщения...")

        messages = []
        counter = 0
        update_step = count // 10
        last_update = 0
        async for mes in ctx.channel.history(limit=count):
            if mes.author != self.bot.user and mes.content != "":
                messages.append(mes.content.strip())
            counter += 1
            if counter >= last_update + update_step and count >= 500:
                await send_message.edit(content=f"Собираю сообщения... ({counter}/{count})")
                last_update = counter

        await send_message.edit(content="Вырезаю слова из сообщений...")

        text = ""
        for message in messages:
            low = message.lower()
            if "http" in low:
                continue

            while message.count(":") > 1:
                left = message.find(":")
                right = message.find(":", left + 1)
                message = message[:left] + message[right + 1:]

            text += f" {message.strip()}"

        await send_message.edit(content="Создаю облако слов...")

        try:
            wordcloud\
                .WordCloud(width=800, height=800, collocations=False, background_color="#170c26", stopwords=stop_words) \
                .generate(text) \
                .to_file("memory/last_word_cloud.png")
        except ValueError:
            await send_message.edit(content="Не удалось создать облако слов")
            return

        await send_message.delete()
        await ctx.send(file=discord.File("memory/last_word_cloud.png"))

    @cloud.command(brief="Задать определенный день", aliases=["day", "d"])
    async def days(self, ctx: commands.Context, start_day: str, stop_day: str = None, count: int = 5000):
        if count < 1:
            await ctx.send("Минимальное количество сообщений: 1")
            return
        if count > 5000 and ctx.author.id not in admin_ids:
            await ctx.send("Максимальное количество сообщений: 5000")
            return

        try:
            start_date = datetime.strptime(start_day, "%d.%m.%Y")
            if stop_day is not None:
                stop_date = datetime.strptime(stop_day, "%d.%m.%Y")
                if stop_date < start_date:
                    await ctx.send("Неверный формат даты, попробуйте cloud d <дд.мм.гггг> <дд.мм.гггг> <количество>")
                    return
            else:
                stop_date = start_date+timedelta(days=1)
        except ValueError:
            await ctx.send("Неверный формат даты, попробуйте cloud day <дд.мм.гггг> <количество>")
            return

        send_message = await ctx.send("Собираю сообщения...")

        messages = []
        counter = 0
        update_step = count//10
        last_update = 0
        try:
            async for mes in ctx.channel.history(after=start_date, before=stop_date, limit=count):
                if mes.author != self.bot.user and mes.content != "":
                    messages.append(mes.content.strip())
                counter += 1
                if counter >= last_update + update_step and count > 1000:
                    await send_message.edit(content=f"Собираю сообщения... ({counter}/{count})")
                    last_update = counter
        except OSError:
            await send_message.edit(content="Не удалось собрать сообщения (неправильная дата)")
            return
        except discord.errors.HTTPException:
            await send_message.edit(content="Не удалось собрать сообщения (неправильная дата)")
            return
        except:
            await send_message.edit(content="Не удалось собрать сообщения (непредвиденная ошибка)")
            return

        await send_message.edit(content="Вырезаю слова из сообщений...")

        text = ""
        for message in messages:
            low = message.lower()
            if "http" in low:
                continue

            while message.count(":") > 1:
                left = message.find(":")
                right = message.find(":", left + 1)
                message = message[:left] + message[right + 1:]

            text += f" {message.strip()}"

        await send_message.edit(content="Создаю облако слов...")

        try:
            wordcloud\
                .WordCloud(width=800, height=800, collocations=False, background_color="#170c26", stopwords=stop_words) \
                .generate(text) \
                .to_file("memory/last_word_cloud.png")
        except ValueError:
            await send_message.edit(content="Не удалось создать облако слов")
            return
        except:
            logger.log(traceback.format_exc())
            await send_message.edit(content="Не удалось создать облако слов")
            return

        await send_message.delete()
        await ctx.send(file=discord.File("memory/last_word_cloud.png"))

    @cloud.command(brief="Облако по одному пользователю", aliases=["u"])
    async def user(self, ctx: commands.Context, user: discord.User = None, count: int = 5000):
        if user is None:
            await ctx.send("Укажите пользователя: cloud u <@пользователь> <количество>")
            return

        if count < 1:
            await ctx.send("Минимальное количество сообщений: 1")
            return
        if count > 5000 and ctx.author.id not in admin_ids:
            await ctx.send("Максимальное количество сообщений: 5000")
            return

        send_message = await ctx.send("Собираю сообщения...")

        messages = []
        counter = 0
        update_step = count // 10
        last_update = 0
        async for mes in ctx.channel.history(limit=count):
            if mes.author != self.bot.user and mes.content != "" and mes.author == user:
                messages.append(mes.content.strip())
            counter += 1
            if counter >= last_update + update_step and count >= 500:
                await send_message.edit(content=f"Собираю сообщения... ({counter}/{count})")
                last_update = counter

        await send_message.edit(content="Вырезаю слова из сообщений...")

        text = ""
        for message in messages:
            low = message.lower()
            if "http" in low:
                continue

            while message.count(":") > 1:
                left = message.find(":")
                right = message.find(":", left + 1)
                message = message[:left] + message[right + 1:]

            text += f" {message.strip()}"

        await send_message.edit(content="Создаю облако слов...")

        try:
            wordcloud\
                .WordCloud(width=800, height=800, collocations=False, background_color="#170c26", stopwords=stop_words) \
                .generate(text) \
                .to_file("memory/last_word_cloud.png")
        except ValueError:
            await send_message.edit(content="Не удалось создать облако слов")
            return

        await send_message.delete()
        await ctx.send(file=discord.File("memory/last_word_cloud.png"))

    @app_commands.command()
    @app_commands.rename(
        limit="кол-во",
        member="пользователь",
        start_date="нач_дата",
        end_date="кон_дата",
        oldest_first="старые")
    async def s_cloud(
            self,
            interaction: discord.Interaction,
            limit: int = 1000,
            member: discord.Member = None,
            start_date: str = None,
            end_date: str = None,
            oldest_first: bool = False
    ):
        """
        Создает облако слов из сообщений

        Parameters
        -----------
        limit: int
            Количество сообщений (1-5000)
        member: discord.Member
            Выбрать сообщения конкретного пользователя
        start_date: str
            Дата начала ГГГГ-ММ-ДД
        end_date: str
            Дата окончания ГГГГ-ММ-ДД
        oldest_first: bool
            Сначала старые сообщения (True/False)
        """
        response: discord.InteractionResponse = interaction.response
        if limit > 5000 or limit < 1:
            await response.send_message(content="Количество сообщений не может быть больше 5000 или меньше 1")
            return

        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
        if start_date and end_date and start_date > end_date:
            await response.send_message(content="Начальная дата не может быть больше конечной даты")
            return

        await response.send_message(content="Загружаю сообщения...")

        counter = 0
        update_step = limit // 10
        last_update = 0
        messages = []
        try:
            async for mes in interaction.channel.history(
                    limit=limit,
                    after=start_date,
                    before=end_date,
                    oldest_first=oldest_first):
                if mes.author != self.bot.user and mes.content != "":
                    if not member or mes.author == member:
                        messages.append(mes.content.strip())
                counter += 1
                if counter >= last_update + update_step and limit >= 1000:
                    await interaction.edit_original_response(content=f"Собираю сообщения... ({counter}/{limit})")
                    last_update = counter
        except OSError:
            await interaction.edit_original_response(content="Не удалось собрать сообщения (неправильная дата)")
            return
        except discord.errors.HTTPException as e:
            await interaction.edit_original_response(
                content="Не удалось собрать сообщения (неправильная дата):\n" + str(e))
            return
        except:
            print(traceback.format_exc())
            await interaction.edit_original_response(content="Не удалось собрать сообщения (непредвиденная ошибка)")
            return

        await interaction.edit_original_response(content="Создаю облако слов...")

        text = ""
        for message in messages:
            low = message.lower()
            if "http" in low:
                continue

            while message.count(":") > 1:
                left = message.find(":")
                right = message.find(":", left + 1)
                message = message[:left] + message[right + 1:]

            text += f" {message.strip()}"

        try:
            wordcloud \
                .WordCloud(width=800, height=800, collocations=False,
                           background_color="#170c26", stopwords=stop_words) \
                .generate(text) \
                .to_file(f"last_word_cloud{interaction.guild.id}.png")
        except ValueError as e:
            await interaction.edit_original_response(content=f"Не удалось создать облако слов ({e})")
            return
        except:
            logger.log(traceback.format_exc())
            await interaction.edit_original_response(content="Не удалось создать облако слов")
            return

        await interaction.channel.send(file=discord.File(f"last_word_cloud{interaction.guild.id}.png"))

        desc = f"Собрано сообщений: {len(messages)}\n"
        desc += f"Количество уникальных слов: {len(set(text.split()))}\n"
        if member:
            desc += f"Пользователь: {member.mention}\n"
        if start_date:
            desc += f"С: {start_date}\n"
        if end_date:
            desc += f"До: {end_date}\n"
        if oldest_first:
            desc += "Сначала старые сообщения\n"

        embed = discord.Embed(title="Облако слов", description=desc, color=discord.Color.brand_green())
        await interaction.edit_original_response(content="Вот смотри:", embed=embed)


async def setup(bot):
    await bot.add_cog(WordCog(bot))
