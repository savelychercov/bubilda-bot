import discord
from discord.ext import commands
from discord import app_commands
import random
import transliterate
from PIL import Image, UnidentifiedImageError
from memoryV2.DB import check_path, files_path
import io

import config
from library.other_tools import get_discord_color, T_COLOR, repair_png
from library.graphics import SearchContent


regional_indicator_emojis = {
    'a': '\U0001F1E6',
    'b': '\U0001F1E7',
    'c': '\U0001F1E8',
    'd': '\U0001F1E9',
    'e': '\U0001F1EA',
    'f': '\U0001F1EB',
    'g': '\U0001F1EC',
    'h': '\U0001F1ED',
    'i': '\U0001F1EE',
    'j': '\U0001F1EF',
    'k': '\U0001F1F0',
    'l': '\U0001F1F1',
    'm': '\U0001F1F2',
    'n': '\U0001F1F3',
    'o': '\U0001F1F4',
    'p': '\U0001F1F5',
    'q': '\U0001F1F6',
    'r': '\U0001F1F7',
    's': '\U0001F1F8',
    't': '\U0001F1F9',
    'u': '\U0001F1FA',
    'v': '\U0001F1FB',
    'w': '\U0001F1FC',
    'x': '\U0001F1FD',
    'y': '\U0001F1FE',
    'z': '\U0001F1FF',
    ' ': '\U0001F7E6',
    '0': '0️⃣',
    '1': '1️⃣',
    '2': '2️⃣',
    '3': '3️⃣',
    '4': '4️⃣',
    '5': '5️⃣',
    '6': '6️⃣',
    '7': '7️⃣',
    '8': '8️⃣',
    '9': '9️⃣'
}


class OtherCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Другое"
        self.__cog_description__ = "Сборник рандомных команд не вхоящих в другие коги"
        self.bot = bot

        @self.bot.listen()
        async def on_message(message: discord.Message):
            if message.guild is None or message.author == self.bot.user:
                return
            if message.guild.id in config.emoji_enabled_guilds:
                if random.random() < config.emoji_add_chance:
                    try:
                        await message.add_reaction("<:emj:1268135319945875581>")
                    except discord.errors.Forbidden | discord.errors.HTTPException:
                        pass

        @self.bot.listen()
        async def on_message(message: discord.Message):
            if not message.attachments:
                return

            if message.author == bot.user:
                return

            try:
                await message.add_reaction("😯")
            except:
                pass

            async with message.channel.typing():
                for attachment in message.attachments:
                    if not attachment.filename.endswith('.png'):
                        continue

                    check_path(files_path)
                    file_name = files_path + attachment.filename
                    try:
                        Image.open(io.BytesIO(await attachment.read()))
                        continue
                    except UnidentifiedImageError:
                        pass

                    await attachment.save(file_name, use_cached=False)
                    repair_png(file_name)
                    await message.channel.send(file=discord.File(file_name))

    @app_commands.command(description="Отправить анонимное сообщение в чат")
    @app_commands.rename(
        member="кому",
        channel="куда",
        text="сообщение",
        file="картинка-файл",
        url="картинка-ссылка",
        color="цвет-сообщения"
    )
    @app_commands.describe(
        member="Участник, которому предназначено сообщение (не обязательно)",
        channel="Канал в который отправится сообщение (не обязательно)",
        text="Текст",
        file="Медиа как файл (например изображение)",
        url="Медиа как ссылка (например гиф)",
        color="Цвет сообщения (слева эмбеда)"
    )
    async def anon(
            self,
            interaction: discord.Interaction,
            text: str = None,
            member: discord.Member = None,
            channel: discord.TextChannel = None,
            file: discord.Attachment = None,
            url: str = None,
            color: T_COLOR = None
    ):
        response: discord.InteractionResponse = interaction.response
        await response.defer(ephemeral=True)
        channel = channel or interaction.channel
        color = get_discord_color(color) if color is not None else discord.Color.green()

        if text is None and file is None and url is None:
            await interaction.followup.send("Нужно указать текст или картинку бро", ephemeral=True)
            return

        embed = discord.Embed(
            color=color,
            title="Анонимное сообщение"+(f" для {member.display_name}" if member else ""),
            description=text if text else None,
        )
        embeds = [embed]

        if url:
            image2_embed = discord.Embed(color=color)
            image2_embed.set_image(url=url)
            embeds.append(image2_embed)
        if file:
            image_embed = discord.Embed(color=color)
            image_embed.set_image(url=file.proxy_url)
            embeds.append(image_embed)

        embed.set_footer(text="Чтобы отправить такое же: /anon")
        try:
            await channel.send(content=member.mention if member else None, embeds=embeds)
        except discord.Forbidden:
            await interaction.followup.send("Не удалось отправить сообщение :cry:\n(мне запрещено отправлять сообщения в этом канале)", ephemeral=True)
        except discord.HTTPException:
            await interaction.followup.send("Не удалось отправить сообщение :cry:", ephemeral=True)
        else:
            await interaction.followup.send("Сообщение доставлено :shushing_face:", ephemeral=True)

    @commands.command(name="poke", brief="Тыкнуть - poke @user")
    async def poke(self, ctx, member: discord.Member):
        embed = discord.Embed(
            title=str(ctx.author.display_name) + " тыкнул " + str(member.display_name),
            color=discord.Colour.purple()
        )
        embed.set_image(url=SearchContent.get_gif("poke", 20))
        await ctx.send(embed=embed)

    @app_commands.command(description="Слешкоманда пинга")
    async def slash_ping(self, interaction: discord.Interaction):
        response: discord.InteractionResponse = interaction.response
        embed = discord.Embed(
            color=discord.Color.green(),
            title=f'Pong! {round(self.bot.latency * 1000)}ms')
        await response.send_message(embed=embed)

    @commands.command(brief="Написать текст через эмодзи")
    async def write(self, ctx: commands.Context, *, text):
        text = transliterate.translit(text, "ru", reversed=True)
        if ctx.message.reference is None or ctx.message.reference.resolved is None:
            await ctx.message.add_reaction("❌")
            return
        alphabet = "abcdefghijklmnopqrstuvwxyz 0123456789"
        letters = [letter for letter in text.lower() if letter in alphabet]
        emojis = [regional_indicator_emojis[letter] for letter in letters]
        if not emojis:
            await ctx.message.add_reaction("❌")
            return
        for emoji in emojis:
            try:
                await ctx.message.reference.resolved.add_reaction(emoji)
            except discord.errors.Forbidden:
                await ctx.message.add_reaction("<:poker_question:1225039226593345576>")
                return
        await ctx.message.add_reaction("✅")


async def setup(bot):
    await bot.add_cog(OtherCog(bot))
