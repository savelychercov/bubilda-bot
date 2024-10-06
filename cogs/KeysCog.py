import discord
from discord.ext import commands
from memory.files import KeysData
from library import logger
from library.graphics import SearchContent
from library.gpt import *
import config
from random import *
from math import *


def rand(chance=100):
    return randrange(0, 100) <= chance


def messagehandler(msg, ctx: commands.Context, test=False):
    msg = str(msg)
    rep = True
    name = ctx.author.display_name
    text = "test" if test else str(ctx.content)
    while True:
        if msg.find("{") != -1 and msg.find("}") != -1:
            lBrace = msg.find("{") + 1
            rBrace = msg[lBrace:].find("}") + lBrace
            command = msg[lBrace:rBrace]
            if command:

                result = ""
                if command.find("%") != -1:
                    chance = 0
                    try:
                        chance = float(command.replace("%", ""))
                    except:
                        return "chanceError", False
                    if not rand(chance): rep = False
                elif command == "name":
                    result = name
                elif command == "text":
                    if test:
                        result = "testtext"
                    else:
                        result = text
                else:
                    try:
                        result = eval(command)
                    except Exception as e:
                        print(e)
                        logger.err(e, f"Key error:\n")
                        return "commandError", False

                localresult = result
                if localresult != "notSend":
                    msg = msg[:lBrace - 1] + str(localresult) + msg[rBrace + 1:]
                else:
                    msg = ""
            else:
                return "commandEmptyError", False
        else:
            break
    return msg, rep


class KeysCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Создание ответов"
        self.__cog_description__ = "Этими командами можно создавать ключи (слова) на которые будет реагировать бот, когда увидит их в чате"
        self.bot = bot

        @bot.listen()
        async def on_message(ctx):
            if ctx.author != bot.user and not ctx.content.startswith(config.prefix):
                try:
                    mem = KeysData.read_all(str(ctx.guild.id))
                    if not mem: return
                except:
                    return

                for key in mem:
                    if str(ctx.content).lower().find(key) != -1 or key.find("{all}") != -1:
                        message, rep = messagehandler(mem[key], ctx)
                        if message and rep:
                            await ctx.reply(message)

        """@bot.listen()
        async def on_message_delete(ctx):
            if ctx.author != bot.user:
                usr = str(ctx.author) + " / " + str(ctx.created_at)[:18]
                msg = str(ctx.content)
                keyFiles.newkey("deleted", usr, msg)
                print(usr + " - " + msg)"""

    @commands.command(name="newkey", aliases=["key", "new"], brief="Создать новый ключ - key (ключ) | (сообщение)")
    async def newkey(self, ctx, *, arg="help"):
        if arg == "help":
            await ctx.send("Нужно писать: b.new ваша фраза | фраза бота")
        else:
            try:
                com, words = str(arg).split("|")
                com, words = com.strip(), words.strip()
                if com and words:
                    match messagehandler(words, ctx, True)[0]:
                        case "commandEmptyError":
                            await ctx.send("Ошибка: пустая команда")
                        case "commandError":
                            await ctx.send("Ошибка: неправильная команда")
                        case "chanceError":
                            await ctx.send("Ошибка: шанс указан неправильно")
                        case _:
                            KeysData.new_key(str(ctx.guild.id), com, words)
                            await ctx.send("Создано!")
            except:
                await ctx.send("Нужно писать: b.new ваша фраза | фраза бота")

    @commands.command(name="delkey", aliases=["del", "deletekey", "delete"], brief="Удалить ключ - del (ключ)")
    async def delkey(self, ctx, *, arg):
        if KeysData.delete_key(str(ctx.guild.id), str(arg)):
            await ctx.send('Ключ "' + str(arg) + '" удален!')
        else:
            await ctx.send("Такого ключа нет!")

    @commands.command(name="clearkeys", aliases=["clrkeys", "deleteall", "clear"], brief="Удалить все ключи")
    async def clear(self, ctx):
        try:
            KeysData.clear_keys(str(ctx.guild.id))
            await ctx.send("Все ключи удалены!")
        except:
            await ctx.send("Ключей нет!")

    @commands.command(name="keys", aliases=["allkeys", "all"], brief="Показать все ключи")
    async def keys(self, ctx):
        keys = KeysData.read_all(str(ctx.guild.id))
        if keys:
            answ = "Все ключи:\n"
            for key in keys:
                answ = answ + key + " | " + keys[key] + "\n"
            await ctx.send(answ)
        else:
            await ctx.send("Ключей нет!")


async def setup(bot):
    await bot.add_cog(KeysCog(bot))
