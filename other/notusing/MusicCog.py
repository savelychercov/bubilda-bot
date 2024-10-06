import discord
from discord.ext import commands
import youtube_dl


class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def test(self, ctx):
        pass


async def setup(bot):
    await bot.add_cog(MusicCog(bot))


if __name__ == "__main__":
    link = input("Insert the link: ")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([link])