import discord
from discord.ext import commands
from memory.files import MarryData
from library.graphics import SearchContent

class Buttons(discord.ui.View):
    def __init__(self, user, author, *, timeout=3600):
        self.author = author
        self.user = user
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="Принять",style=discord.ButtonStyle.green,emoji="💞")
    async def accept_button(self,interaction:discord.Interaction,button:discord.ui.Button):
        if self.user == interaction.user:   
            await interaction.response.send_message("Принято")

    @discord.ui.button(label="Отклонить",style=discord.ButtonStyle.red,emoji="😥")
    async def decline_button(self,interaction:discord.Interaction,button:discord.ui.Button):
        if self.user == interaction.user:
            await interaction.response.send_message("Отклонено")

    @discord.ui.button(label="Отменить",style=discord.ButtonStyle.gray,emoji="❌")
    async def cancel_button(self,interaction:discord.Interaction,button:discord.ui.Button):
        if self.author == interaction.user:
            await interaction.response.send_message("Отменено")

class MarryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(brief="Заключить брак - marry @user message")
    async def marry(self, ctx, user: discord.Member, *, message = "У вас есть час чтобы принять запрос"):
        gId = str(ctx.guild.id)
        
        marriedOn = MarryData.check_marry(gId, str(ctx.author.id))
        marryWith = MarryData.check_marry(gId, str(user.id))
        if marriedOn:
            await ctx.send("Вы уже женаты на "+self.bot.get_user(int(marriedOn)).display_name)
        elif marryWith:
            await ctx.send(user.display_name+" уже женат на "+self.bot.get_user(int(marryWith)).display_name)
        elif ctx.author == user:
            await ctx.send("Вы не можете жениться на себе!")
        else:
            embed = discord.Embed(
                color=discord.Color.purple(),
                title=user.display_name+", пользователь "+str(ctx.author.display_name)+" хочет жениться на вас",
                description=message
            )
            embed.set_author(name="Wedding Bubilda", icon_url="https://cdn.discordapp.com/attachments/1050725563561676840/1053651366314246164/bub.jpg")
            embed.set_image(url=SearchContent.get_gif("marry", 15))
            msg = await ctx.send(embed=embed,view=Buttons(user = user, author = ctx.author))

            def check(m: discord.Message):
                return m.author.id == self.bot.user.id and m.content in ["Принято","Отклонено","Отменено"]

            repmsg = await self.bot.wait_for('message', check = check)
            await msg.edit(embed=embed,view=None)
            match repmsg.content:
                case "Принято":
                    MarryData.new_marry(gId, str(ctx.author.id), str(user.id))
                    await ctx.send(ctx.author.display_name+" и "+user.display_name+" поженились!")
                case "Отклонено":
                    await ctx.send(user.display_name+" отклонил запрос на брак")
                case "Отменено":
                    await ctx.send(ctx.author.display_name+" отменил запрос на брак")
    
    @commands.command(brief="Развестись")
    async def divorce(self, ctx):
        gId = str(ctx.guild.id)
        
        marriedOn = MarryData.check_marry(gId, str(ctx.author.id))
        if marriedOn:
            if MarryData.divorce(gId, str(ctx.author.id)):
                await ctx.send("Вы развелись с "+str(self.bot.get_user(int(marriedOn)).display_name))
        else:
            await ctx.send("Вы не женаты")

    @commands.command(brief="Показать на ком вы женаты")
    async def mymarry(self, ctx):
        marriedOn = MarryData.check_marry(str(ctx.guild.id), str(ctx.author.id))
        if marriedOn: await ctx.send("Вы женаты на "+str(self.bot.get_user(int(marriedOn)).display_name))
        else: await ctx.send("Вы не женаты")
    
    @commands.command(brief="Показать все браки")
    async def marriages(self, ctx):
        marriages = MarryData.married_users(str(ctx.guild.id))
        if marriages:
            marriagesmessage = "\n"
            for user in marriages:
                marriagesmessage = marriagesmessage+"**• "+self.bot.get_user(int(user)).display_name+" женат на "+self.bot.get_user(int(marriages[user])).display_name+"**\n\n"
            embed = discord.Embed(
                color=discord.Color.yellow(),
                title="Все браки:",
                description=marriagesmessage
            )
            if marriagesmessage != "\n": await ctx.send(embed=embed)
        else: await ctx.send("На этом сервере нет браков")

async def setup(bot):
   await bot.add_cog(MarryCog(bot))