import discord
import sys
import time
import traceback
from discord.ext import commands
from discord.ext.commands import Context
import library.logger as logger
from config import admin_ids, auto_sync_slash_commands
import config
from library.other_tools import loaded_extensions
import os

bot = commands.Bot(intents=discord.Intents.all(), command_prefix=config.prefix)
bot.remove_command("help")


async def setup_hook() -> None:
    exts = loaded_extensions()
    config.loaded_cogs = exts
    if exts:
        for extension in exts:
            await bot.load_extension("cogs." + extension.replace(".py", ""))
        print("Cogs loaded")
    if not auto_sync_slash_commands: return
    print("Syncing commands...")
    bot.tree.copy_global_to(guild=discord.Object(id=1050725563117084732))
    test_count = len(await bot.tree.sync(guild=discord.Object(id=1050725563117084732)))
    print(f"| {test_count}:For test guild,")
    all_count = len(await bot.tree.sync())
    print(f"| {all_count}:For all,")
    print("| Synced commands:", ", ".join([i.name for i in await bot.tree.fetch_commands()]))

bot.setup_hook = setup_hook


def get_description_command(command, is_dev, is_slash):
    if not is_slash:
        help_text = command.brief if hasattr(command, "brief") and command.brief is not None else "None"
    else:
        help_text = command.description if hasattr(command, "description") and command.description is not None else "None"
    if hasattr(command, "brief") and command.brief is not None and "(dev)" in command.brief and not is_dev: return ""
    if command.parent is not None:
        return f"> {command.parent} **{command.name}** - {help_text}\n"
    else:
        return f"• {config.prefix if not is_slash else '/'}**{command.name}** - {help_text}\n"


def get_description(commands, is_dev, is_slash):
    description = ""
    for command in commands:
        description += get_description_command(command, is_dev, is_slash)
    return description


"""---------------------------------КОМАНДЫ----------------------------------------"""


@bot.command(brief="Вызвать это сообщение")  # 6000 - max
async def help(ctx: Context, *, cog_name: str = None):
    is_dev = ctx.author.id in admin_ids

    if cog_name is None:
        title_embed = discord.Embed(
            color=discord.Color.blue(),
            title="Все что может бот:",
            description="Здесь описаны все команды бота",
        )
        cog_embeds = [title_embed]

        bot_commands = bot.all_commands
        default_desc = ""
        for command_name in bot_commands:
            command = bot_commands[command_name]
            if command.cog is not None: continue
            if command.brief is not None and "(dev)" in command.brief and not is_dev: continue
            default_desc += get_description_command(command, is_dev, False)

        cog_embeds.append(discord.Embed(
            color=discord.Color.blue(),
            title="Встроенные команды",
            description=default_desc))

        for cog in bot.cogs:
            cog = bot.get_cog(cog)
            description = ""
            description += get_description(cog.walk_commands(), is_dev, False)
            description += get_description(cog.walk_app_commands(), is_dev, True)
            if description == "": continue
            cog_embeds.append(discord.Embed(
                color=discord.Color.blue(),
                title=f"{cog.qualified_name}",
                description=description))

        total_len = 0
        embeds_to_send = []
        for embed in cog_embeds:
            total_len += len(embed)

            if total_len > 5000 or len(embeds_to_send) == 10:
                await ctx.send(embeds=embeds_to_send)
                embeds_to_send = [embed]
                total_len = len(embed)
            else:
                embeds_to_send.append(embed)

        await ctx.send(embeds=embeds_to_send)
    else:
        cog = bot.get_cog(cog_name)
        if cog is None:
            await ctx.send("Такого кога нет")
            return
        description = ""
        for command in cog.walk_commands():
            if command.brief is not None and "(dev)" in command.brief and not is_dev: continue
            if command.parent is not None:
                description += f"> {command.parent} **{command.name}** - {command.brief}\n"
            else:
                description += f"• {config.prefix}**{command.name}** - {command.brief}\n"
        for command in cog.walk_app_commands():
            if command.description is not None and "(dev)" in command.description and not is_dev: continue
            if command.parent is not None:
                description += f"> {command.parent} **{command.name}** - {command.description}\n"
            else:
                description += f"• /**{command.name}** - {command.description}\n"
        embed = discord.Embed(
            color=discord.Color.blue(),
            title=f"{cog.qualified_name}",  # ({cog.name})",
            description=description)
        await ctx.send(embed=embed)


@bot.command(brief="Пинг бубылды")
async def ping(ctx):
    start = time.monotonic()
    msg = await ctx.send("Pinging...")
    end = time.monotonic()
    total_ping = round((end - start) * 1000, 2)
    embed = discord.Embed(
        color=discord.Color.green(),
        title="PONG! in " + "{:1.0f}".format(total_ping) + "ms")
    await msg.edit(content=None, embed=embed)


@bot.command(brief="Сказать - say (текст)")
async def say(ctx, *, arg="Чё сказать то"):
    await ctx.send(arg)


@bot.command(brief="ID эмодзи", name="id")
async def emoji_id(ctx, *, arg="<:funnycat:1051348714423328778>"):
    if "<" in arg:
        arg = arg.replace("<", "")
        arg = arg.replace(">", "")
    await ctx.send(arg)


@bot.command(brief="Перезагрузка бота (dev)", aliases=["reload"])
async def restart(ctx: commands.Context):
    if ctx.author.id not in admin_ids:
        await ctx.send("Не балуйся")

    embed = discord.Embed(
        color=discord.Color.blurple(),
        title="**Перезагрузка**")
    await ctx.send(embed=embed)
    os.execv(sys.executable, ["python"] + sys.argv)


@bot.command(brief="Синхронизировать слеш команды (dev)")
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: Context, spec: str = None):
    if spec in ["~", "this"]:
        synced = await ctx.bot.tree.sync(guild=ctx.guild)
    elif spec in ["*", "test"]:
        ctx.bot.tree.copy_global_to(guild=ctx.guild)
        synced = await ctx.bot.tree.sync(guild=ctx.guild)
    elif spec in ["^", "clear"]:
        ctx.bot.tree.clear_commands(guild=ctx.guild)
        await ctx.bot.tree.sync(guild=ctx.guild)
        synced = []
    else:
        synced = await ctx.bot.tree.sync()

    await ctx.send(
        f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
    )


"""--------------------------------КОНЕЦ ФАЙЛА--------------------------------------"""


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(config.prefix + "help"))
    if config.send_is_ready_message:
        if not config.id_to_send_ready_message: print("Please set id_to_send_ready_message in config.py")
        await bot.get_user(config.id_to_send_ready_message).send(bot.user.display_name + " is ready!")
    print("Bubilda is ready!")


@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, 'on_error'):
        return
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send("Подождите " + "{:1.0f}".format(error.retry_after + 1) + "с")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(
            embed=discord.Embed(title=f'{ctx.author.name}, команды **{str(ctx.message.content).removeprefix(config.prefix).split(" ")[0]}**' + ' не существует.', color=0x0c0c0c))
    elif isinstance(error.original, NotImplementedError):
        await ctx.send(embed=discord.Embed(title="Команда находится в разработке", color=0x0c0c0c))
    else:
        logger.err(error.original, "Not handled error: \n")


@bot.event
async def on_error(event: str, *args, **kwargs):
    print(f"Error in '{event}': \n" + traceback.format_exc())
    logger.log(f"Error in '{event}' event:\n```python\n" + traceback.format_exc() + "```")


bot.run(config.token)
