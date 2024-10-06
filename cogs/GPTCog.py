import discord
from discord.ext import commands
from library import gpt
import traceback
from library import logger
import openai
import config
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from memoryV2 import DB

default_tune_tuple = (
    "You are a discord bot named Bubilda",
)


@dataclass
class Settings:
    tune_string: tuple[str] = default_tune_tuple
    names: tuple[str] = ("bubilda", "бубылда", "бубилда")
    context_window: int = 10
    cooldown_time: int = 2
    enabled: bool = True
    banned_users: set[int] = field(default_factory=set)


db = DB.DefinedDataBase(int, Settings, "gptsettings")

allowed_servers = [1050725563117084732]

cooldown_time = 2

regex_for_names = '^[a-zA-Z0-9_-]{1,64}$'

last_call = datetime.now()


def get_settings(guild_id: int | str) -> Settings:
    return db.get_obj("", guild_id)


def slice_text(text: str, length: int = 1990) -> list[str]:
    if not text:
        return [""]
    return [text[i:i + length] for i in range(0, len(text), length)]


class GPTCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "GPT"
        self.__cog_description__ = "Команды управления ответами бубылды"
        self.bot: commands.Bot = bot

        @self.bot.listen()
        async def on_message(message: discord.Message):
            global last_call

            if message.guild is None:
                return

            allowed_guilds = db.get_all_obj("").keys()
            if message.guild.id not in allowed_guilds or allowed_guilds == []:
                if message.author.id not in config.admin_ids:
                    return

            preferences = get_settings(message.guild.id)
            if not preferences or not preferences.enabled or message.author.id in preferences.banned_users:
                return

            appeal = any([name in message.content.lower() for name in preferences.names])

            term_1 = message.author != bot.user \
                     and not message.content.startswith(config.prefix) \
                     and appeal

            if message.reference is not None and message.reference.resolved is not None:
                term_2 = message.reference.resolved.author.id == bot.user.id
            else:
                term_2 = False

            is_answer = any((term_1, term_2))

            if not is_answer:
                return

            if datetime.now() < last_call + timedelta(seconds=cooldown_time):
                await message.channel.send("Подождите немного...")
                return

            last_call = datetime.now()

            try:
                async with message.channel.typing():
                    last_messages = await gpt.get_last_messages(self.bot, message.channel, message, preferences.context_window)
                    messages_context = gpt.get_full_context_window(preferences.tune_string, last_messages, message)
                    answer_text, gif_url, embed = gpt.gen_answer_universal(messages_context)
                    if not any((answer_text, gif_url, embed)):
                        answer_text = "Я не смог ничего придумать"

            except openai.PermissionDeniedError:
                answer_text = "Меня забанили в GPT сорри"
            except openai.BadRequestError:
                logger.log(f"Bad request: {message.content}")
                answer_text = "Я не смог ничего придумать из за ошибки"
            except Exception as e:
                logger.err(e, "Unexpected exception")
                answer_text = "UnexpectedError"
            else:
                if answer_text or embed:
                    texts = slice_text(answer_text)
                    if len(texts) < 2:
                        if texts[0].startswith("discord.Embed"):
                            try:
                                embed = eval(texts[0])
                                await message.channel.send(embed=embed)
                                return
                            except: pass
                        await message.channel.send(texts[0], embed=embed)
                    else:
                        if embed: await message.channel.send(embed=embed)
                        for text in texts:
                            await message.channel.send(text)
                if gif_url: await message.channel.send(gif_url)
                return

            await message.channel.send(answer_text)

    @commands.command(brief="Вывести последние сообщения (dev)")
    async def lastmessages(self, ctx: commands.Context):
        preferences = get_settings(ctx.guild.id)
        last_messages = await gpt.get_last_messages(self.bot, ctx.channel, ctx.message, preferences.context_window)
        messages_context = gpt.get_full_context_window(preferences.tune_string, last_messages, ctx.message)
        messages_strs = map(str, messages_context)
        with open("last_messages.txt", "w", encoding="utf-8") as f:
            for message in messages_strs:
                f.write(message + "\n")
        await ctx.send(file=discord.File("last_messages.txt"))

    @commands.command(brief="Ответ от GPT", aliases=["gpt", "ans"])
    async def answer(self, ctx: commands.Context, *, arg=None):
        if arg is None:
            await ctx.send("Попробуйте: answer <текст>")

        async with ctx.typing():
            try:
                answer_text = gpt.gen_answer_from_messages(ctx.author.name, arg)
            except openai.PermissionDeniedError:
                logger.log(f"PermissionDeniedError:\n{traceback.format_exc()}")
                answer_text = "PermissionDeniedError"
            except Exception:
                logger.log(f"Unexpected exception:\n{traceback.format_exc()}")
                answer_text = "UnexpectedError"

            await ctx.send(content=answer_text)

    @commands.group(brief="Настройки GPT (dev)", invoke_without_command=True, aliases=["gpts"])
    async def gptsettings(self, ctx: commands.Context):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Не влезай убьет")
            return
        prefs = get_settings(ctx.guild.id)
        if not prefs:
            prefs = Settings(enabled=False)
            db.set_obj("", ctx.guild.id, prefs)

        embed = discord.Embed(
            title="Настройки GPT Бубылды",
            description="\n".join([f"{i + 1}: {pr}" for i, pr in enumerate(prefs.tune_string)]),
            color=discord.Color.gold()
        )
        embed.add_field(name="Имена", value=" | ".join(prefs.names), inline=False)
        embed.set_footer(text=f'Включено: {"Да" if prefs.enabled else "Нет"}')
        await ctx.send(embed=embed)

    @gptsettings.command(brief="Изменить строку промта", aliases=["pref", "preferences"])
    async def preference(self, ctx: commands.Context, index: int, *, text: str = ""):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Не влезай убьет")
            return
        prefs = get_settings(ctx.guild.id)
        if not prefs:
            prefs = Settings(enabled=False)
            db.set_obj("", ctx.guild.id, prefs)
        prefs_list = list(prefs.tune_string)

        if text == "clear":
            prefs_list = []
        elif text == "default":
            prefs_list = default_tune_tuple
        elif index < 1:
            if text:
                prefs_list.insert(0, text)
            else:
                await ctx.send("Такой индекс нельзя удалить")
        elif index > len(prefs.tune_string):
            if text:
                prefs_list.append(text)
            else:
                await ctx.send("Такой индекс нельзя удалить")
        else:
            if text == "":
                pref = prefs_list.pop(index - 1)
                await ctx.send(f"Удалено: {pref}")
            else:
                prefs_list[index - 1] = text
        prefs.tune_string = tuple(prefs_list)
        db.set_obj("", ctx.guild.id, prefs)
        await ctx.send(f"Установлено: {text}")

    @gptsettings.command(brief="Вкл/выкл GPT", aliases=["enable"])
    async def enabled(self, ctx: commands.Context, is_enabled: bool = False):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Не влезай убьет")
            return
        prefs = get_settings(ctx.guild.id)
        if not prefs:
            prefs = Settings(enabled=False)
            db.set_obj("", ctx.guild.id, prefs)
        prefs.enabled = is_enabled
        db.set_obj("", ctx.guild.id, prefs)
        await ctx.send(f"Установлено на {is_enabled}")

    @gptsettings.command(brief="Список имен", aliases=["name"])
    async def names(self, ctx: commands.Context, *names: str):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Не влезай убьет")
            return
        prefs = get_settings(ctx.guild.id)
        if not prefs:
            prefs = Settings(enabled=False)
            db.set_obj("", ctx.guild.id, prefs)

        if not names:
            embed = discord.Embed(
                title="Список имен",
                description=" ".join(prefs.names),
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            return

        prefs.names = names
        db.set_obj("", ctx.guild.id, prefs)
        await ctx.send("Имена успешно изменены на [" + " | ".join(prefs.names) + "]")

    @gptsettings.command(brief="Забанить")
    async def ban(self, ctx: commands.Context, user: discord.User):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя")
            return
        prefs = get_settings(ctx.guild.id)
        if not prefs:
            prefs = Settings(enabled=False)
            db.set_obj("", ctx.guild.id, prefs)
        prefs.banned_users.add(user.id)
        db.set_obj("", ctx.guild.id, prefs)
        await ctx.send(f"{user.display_name} забанен")

    @gptsettings.command(brief="Разбанить")
    async def unban(self, ctx: commands.Context, user: discord.User):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Нельзя")
            return
        prefs = get_settings(ctx.guild.id)
        if not prefs:
            prefs = Settings(enabled=False)
            db.set_obj("", ctx.guild.id, prefs)
        try:
            prefs.banned_users.remove(user.id)
        except KeyError:
            await ctx.send(f"{user.display_name} не забанен")
            return
        db.set_obj("", ctx.guild.id, prefs)
        await ctx.send(f"{user.display_name} разбанен")

    @commands.command(brief="Получить ссылку на картинку из сообщения (dev)")
    async def imageurl(self, ctx: commands.Context):
        text = "Вот ссылки на прикрепленные картинки:\n"
        urls = [attachment.url for attachment in ctx.message.attachments if
                attachment.content_type.startswith('image/')]
        await ctx.send(text + "\n".join(urls))

    @commands.command(brief="Получить ответ на запрос с картинками")
    async def look(self, ctx: commands.Context):
        image_urls = [attachment.url for attachment in ctx.message.attachments if
                      attachment.content_type.startswith('image/')]
        if not image_urls:
            await ctx.send("Нужно прикрепить картинки")
            return
        await ctx.send(gpt.gen_answer_from_image(ctx.author.name, ctx.message.content, image_urls))


async def setup(bot):
    await bot.add_cog(GPTCog(bot))
