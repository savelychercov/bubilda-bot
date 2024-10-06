import io
import discord
from discord.ext import commands
from discord import app_commands
from library.graphics import SearchContent, covert_image_to_ascii
from PIL import Image


class GraphicsCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Графика"
        self.__cog_description__ = "Команды для поиска картинок и гифок"
        self.bot = bot

    @commands.command(brief="Найти гиф по запросу - gif (текст)")
    async def gif(self, ctx, *, arg):
        await ctx.send(SearchContent.get_gif(str(arg)))

    @commands.command(brief="Найти фото по запросу - img (текст)")
    async def img(self, ctx, *, arg):
        await ctx.send(SearchContent.get_image(str(arg)))

    @app_commands.command(description="Конвертировать картинку в символы")
    @app_commands.rename(
        img_file="картинка",
        cols="столбцы",
        scale="размер",
        more_levels="доп_уровни_цвета",
    )
    async def to_ascii(
            self,
            interaction: discord.Interaction,
            img_file: discord.Attachment,
            cols: int = 80,
            scale: float = 0.43,
            more_levels: bool = False):
        """Конвертировать картинку в ASCII

        Parameters
        ----------
        img_file: discord.Attachment
            Собственно картинка
        cols: int
            Количество столбцов
        scale: float
            Размер
        more_levels: bool
            Больше уровней черно-белого
        """
        await interaction.response.defer()
        image: Image = Image.open(io.BytesIO(await img_file.read()))
        try:
            text = "```\n" + ("\n".join(covert_image_to_ascii(image, cols, scale, more_levels))) + "\n```"
            count = 1
            while len(text) > 2000:
                text = "```\n" + ("\n".join(covert_image_to_ascii(image, cols - count, scale, more_levels))) + "\n```"
                count += 1
        except Exception as e:
            await interaction.followup.send(e)
            return

        await interaction.followup.send(text)


async def setup(bot):
    await bot.add_cog(GraphicsCog(bot))
