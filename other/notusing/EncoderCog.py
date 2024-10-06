import discord
from discord.ext import commands

skip_letters = ["\n"]
def encode(text: str, key: int):
    encoded_text = ""
    for ltr in text:
        if not ltr in skip_letters:
            encoded_text += chr((ord(ltr)+key)%1114111)
        else: 
            encoded_text += ltr

    return encoded_text

class EncoderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief = "Закодировать сообщение")
    async def encode(self, ctx, key, *, arg):
        if not key: 
            await ctx.send("Сначала введите ключ")
            return
        if not arg.strip():
            await ctx.send("После ключа введите сообщение")
            return
        await ctx.send(encode(arg,int(key)))

    @commands.command(brief = "Раскодировать сообщение")
    async def decode(self, ctx, key, *, arg):
        if not key: 
            await ctx.send("Сначала введите ключ")
            return
        if not arg.strip():
            await ctx.send("После ключа введите сообщение")
            return
        await ctx.send(encode(arg,-int(key)))

async def setup(bot):
   await bot.add_cog(EncoderCog(bot))