import discord
from discord.ext import commands
from discord import Interaction
from memoryV1.files_db import InventoryData as inv
from library.things_lib import Things
from library import logger
import config
import traceback
import math


class UseThingView(discord.ui.View):
    def __init__(self, message: discord.Message, owner_id: int, ctx: commands.Context):
        super().__init__(timeout=60*10)

        self.message = message
        self.owner_id = owner_id
        self.ctx = ctx

        self.selected_thing = None
        self.selected_user = None

        options = []
        things = inv.get_inv(message.guild.id, owner_id)
        for thing, uses in things.items():
            options.append(discord.SelectOption(label=f"{thing} ({uses}шт)", value=thing))
        self.select_thing = discord.ui.Select(
            placeholder='Выберите вещь...',
            options=options,
            row=0
        )
        self.select_user = discord.ui.UserSelect(
            placeholder='На кого использовать (опционально)',
            min_values=1,
            max_values=1,
            row=1
        )
        self.confirm_button = discord.ui.Button(
            label="Использовать",
            style=discord.ButtonStyle.green,
            row=2
        )
        self.confirm_button.callback = self.confirm_callback
        self.select_thing.callback = self.select_thing_callback
        self.select_user.callback = self.select_user_callback
        self.add_item(self.select_thing)
        self.add_item(self.select_user)
        self.add_item(self.confirm_button)

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        response: discord.InteractionResponse = interaction.response
        followup: discord.Webhook = interaction.followup
        await response.defer()
        if interaction.user.id == self.owner_id:
            return True
        else:
            await followup.send("Вы не можете использовать эти штучки", ephemeral=True)
            return False

    async def on_timeout(self) -> None:
        await self.message.edit(view=None)
        self.stop()

    async def confirm_callback(self, interaction: discord.Interaction):
        has_thing = inv.has_thing(self.ctx.guild.id, self.ctx.author.id, self.selected_thing)
        nothing_happens = False
        if not await Things.execute_thing(self.ctx, self.selected_user, self.selected_thing):
            if inv.use_thing(self.ctx.guild.id, self.ctx.author.id, self.selected_thing):
                nothing_happens = True
        if has_thing:
            embed = discord.Embed(
                title=f"Вы использовали {self.selected_thing}" + (f" на {self.selected_user.display_name}" if self.selected_user else ""),
                description="Ничего не произошло..." if nothing_happens else None,
                color=discord.Color.from_rgb(17, 189, 63)
            )
        else:
            embed = discord.Embed(
                title=f"У вас нет {self.selected_thing}",
                color=discord.Color.from_rgb(116, 118, 125)
            )
        await self.message.edit(embed=embed, content=None, view=None)

    async def select_thing_callback(self, interaction: discord.Interaction):
        self.selected_thing = self.select_thing.values[0]

    async def select_user_callback(self, interaction: discord.Interaction):
        self.selected_user = self.select_user.values[0]


class InventoryCog(commands.Cog):
    def __init__(self, bot):
        self.__cog_name__ = "Инвентарь"
        self.__cog_description__ = "Команды для взаимодействия с инвентарем"
        self.bot = bot

    @commands.hybrid_command(brief='Использовать предмет: use "название предмета" @игрок')
    async def use(self, ctx: commands.Context, thing: str, member: discord.Member = None):
        if not await Things.execute_thing(ctx, member, thing):  # Try to use directly
            if inv.use_thing(ctx.guild.id, ctx.author.id, thing):  # If it not found
                await ctx.send("Ничего не произошло...")
            else:
                await ctx.send(f"У вас нет {thing}")

    @use.error
    async def use_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send('Используйте кавычки: use \"Название предмета\"')
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title=":arrow_down: Использовать предмет :arrow_down:",
                color=discord.Color.from_rgb(125, 68, 64)
            )
            use_message = await ctx.send("Загрузка...")
            view = UseThingView(use_message, ctx.author.id, ctx)
            await use_message.edit(content=None, embed=embed, view=view)
        else:
            raise error

    @commands.command(brief='Узнать что делает предмет: info "название предмета"', aliases=["inf"])
    async def info(self, ctx: commands.Context, *, thing: str = None):
        if thing is None:
            await ctx.send('Укажите предмет: info Название предмета')
            return
        elif '"' in thing:
            thing = thing.replace('"', '').replace("«", '').replace("»", '')

        emoji = Things.get_emoji(thing, ":person_shrugging:")

        help_str = Things.get_help(thing, "Справочник говорит что такого предмета нет")
        if help_str is None:
            help_str = "Я пока не знаю что делает этот предмет\nПопробуйте сами и узнаете"

        embed = discord.Embed(
            title=f"{emoji} **{thing}**",
            color=discord.Color.orange(),
            description=help_str
        )
        embed.set_footer(text=f"Чтобы использовать - use \"{thing}\" @User (опционально)",
                         icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True, brief="Посмотреть свой инвентарь", aliases=["inv"])
    async def inventory(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        things_on_page_count = 5
        pages_count = 0

        class InventoryPagination(discord.ui.View):
            def __init__(self, enabled_pagination: bool, enabled_use: bool):
                super().__init__(timeout=60 * 10)
                self.page = 0
                disabled_pagination = not enabled_pagination

                use_button = discord.ui.Button(
                    label="Использовать",
                    style=discord.ButtonStyle.gray,
                    emoji="📦",
                    disabled=not enabled_use)
                use_button.callback = self.use_button_callback

                previous_button = discord.ui.Button(
                    label=None, style=discord.ButtonStyle.gray, emoji="◀", disabled=disabled_pagination)
                previous_button.callback = self.previous_button_callback
                next_button = discord.ui.Button(
                    label=None, style=discord.ButtonStyle.gray, emoji="▶", disabled=disabled_pagination)
                next_button.callback = self.next_button_callback
                self.add_item(previous_button)
                self.add_item(use_button)
                self.add_item(next_button)

            async def on_timeout(self) -> None:
                await message.edit(view=None)
                self.stop()

            async def interaction_check(self, interaction: Interaction, /) -> bool:
                response: discord.InteractionResponse = interaction.response
                followup: discord.Webhook = interaction.followup
                await response.defer()
                if interaction.user.id == ctx.author.id:
                    return True
                else:
                    await followup.send("Вы не можете использовать эту кнопку", ephemeral=True)
                    return False

            async def previous_button_callback(self, interaction: discord.Interaction):
                if self.page > 0:
                    self.page -= 1
                    await update_page(self.page)

            async def next_button_callback(self, interaction: discord.Interaction):
                if self.page < pages_count - 1:
                    self.page += 1
                    await update_page(self.page)

            async def use_button_callback(self, interaction: discord.Interaction):
                embed = discord.Embed(
                    title=":arrow_down: Использовать предмет :arrow_down:",
                    color=discord.Color.from_rgb(125, 68, 64)
                )
                use_message = await interaction.channel.send("Загрузка...")
                view = UseThingView(use_message, ctx.author.id, ctx)
                await use_message.edit(content=None, embed=embed, view=view)

        pagination_view = None

        async def update_page(page: int = 0):
            nonlocal pages_count, pagination_view
            inv_dict = inv.get_inv(message.guild.id, member.id)
            pages_count = math.ceil(len(inv_dict) / things_on_page_count) if inv_dict else 1
            if pagination_view is None:
                pagination_view = InventoryPagination(
                    pages_count > 1,
                    len(inv_dict) > 0 and ctx.author.id == member.id)
            if len(inv_dict) > 5:
                left = min(page * things_on_page_count, len(inv_dict)-1)
                right = min((page + 1) * things_on_page_count, len(inv_dict))
                inv_dict = dict(list(inv_dict.items())[left:right])

            embed = discord.Embed(title=f"**Инвентарь: ({page + 1}/{pages_count})**", color=discord.Color.from_rgb(125, 68, 64))
            embed.set_footer(text=f"Инвентарь {member.display_name}", icon_url=member.display_avatar.url)
            if not inv_dict:
                embed.description = "*-пусто-*"
            else:
                for th in inv_dict.keys():
                    emoji = Things.get_emoji(th, ":person_shrugging:")
                    embed.add_field(
                        name=f"- {th}\n{emoji}",
                        value=f"Осталось использований: {inv_dict[th]}" if inv_dict[th] > 0 else "",
                        inline=False)
            await message.edit(content=None, embed=embed, view=pagination_view)

        message = await ctx.send(":arrows_counterclockwise:")
        await update_page()

    @inventory.command(brief="Добавить в инвентарь (dev)", aliases=["give", "set"])
    async def add(self, ctx: commands.Context, member: discord.Member, thing: str, uses: int = -1):
        if ctx.author.id not in config.admin_ids:
            return

        if thing == "all":
            for i in Things.things.keys():
                inv.set_thing(ctx.guild.id, member.id, i, uses)
        else:
            inv.set_thing(ctx.guild.id, member.id, thing, uses)

        await ctx.send(f"{thing} добавлено ({uses if uses > 0 else '∞'})")

    @inventory.command(brief="Удалить из инвентаря (dev)", aliases=["delete", "del", "rm"])
    async def remove(self, ctx: commands.Context, member: discord.Member, thing: str):
        if ctx.author.id not in config.admin_ids:
            return

        if inv.del_thing(ctx.guild.id, member.id, thing):
            await ctx.send(f"{thing} удалено")
        else:
            await ctx.send(f"Там нет {thing}")

    @inventory.command(brief="Очистить инвентарь (dev)")
    async def clear(self, ctx: commands.Context, member: discord.Member):
        if ctx.author.id not in config.admin_ids:
            return

        inv.set_inv(ctx.guild.id, member.id, {})
        await ctx.send("Инвентарь очищен")


async def setup(bot):
    await bot.add_cog(InventoryCog(bot))
