import discord
from discord.ext import commands, tasks
import library.wb_lib as wb
import json
import pprint
from library.logger import log, err
from datetime import datetime, timedelta
import config
import httpx
import time
import asyncio


class WbCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_task = None
        self.wb_bot = None

    @tasks.loop(minutes=10)
    async def try_update_table(self):
        try:
            print(f"Checking for updates... {datetime.now()}")
            data = await self.get_spreadsheet_data()
            current_date = wb.SheetsBot.get_yesterday_date()
            if current_date == data["last_update"]:
                print("No updates")
                return

            last_update_date = datetime.strptime(data["last_update"], "%Y-%m-%d")
            current_datetime = datetime.strptime(current_date, "%Y-%m-%d")
    
            dates_to_update = []
            while last_update_date < current_datetime:
                date = last_update_date + timedelta(days=1)
                last_update_date = date
                dates_to_update.append(date.strftime("%Y-%m-%d"))
    
            if not dates_to_update:
                print("No updates 2")
                return
    
            print(f"Updating for dates: {dates_to_update}")
    
            try:
                wb_bot = await self.try_get_wb_bot()
            except wb.gspread.exceptions.WorksheetNotFound as e:
                err(e, "Worksheet not found")
                return
    
            for date in dates_to_update:
                start_time = time.time()
                stats = await wb_bot.get_fullstats(date)
                try:
                    await wb_bot.update_table_with_data(date, stats)
                except wb.DateNotFound:
                    log(f"Date not found in table: {date}")
                except httpx.ReadTimeout:
                    log(f"Cannot fetch data for date: {date}")

                await self.set_spreadsheet_data(last_update=date)

                log(f"Updated {date} in {wb_bot.spreadsheet.url} ({time.time() - start_time:.2f} sec)")
        except Exception as e:
            err(e, "Error in try_update_table")

    def cog_load(self):
        if config.testing: return
        self.event_task = self.try_update_table.start()

    def cog_unload(self):
        if self.event_task:
            self.event_task.cancel()
            self.event_task = None

    @try_update_table.after_loop
    async def restart_task(self):
        if self.try_update_table.failed():
            log("Task \'try_update_table\' failed, restarting...")
            self.event_task = self.try_update_table.start()
        else:
            log("Task \'try_update_table\' stopped")

    @staticmethod
    async def get_spreadsheet_data() -> dict[str, str]:
        """
            spreadsheet_data.json:
            {
                "wb_token": ...,
                "spreadsheet_url": ...,
                "worksheet": ...,
                "last_update": ...
            }
        """
        with open("library/spreadsheet_data.json", "r", encoding="utf-8") as f:
            sheet_data = json.load(f)
        return sheet_data

    @staticmethod
    async def set_spreadsheet_data(**kwargs: dict[str, str]):
        with open("library/spreadsheet_data.json", "r", encoding="utf-8") as f:
            sheet_data = json.load(f)
        for key, value in kwargs.items():
            sheet_data[key] = value
        with open("library/spreadsheet_data.json", "w", encoding="utf-8") as f:
            json.dump(sheet_data, f, indent=4)

    async def try_get_wb_bot(self):
        if self.wb_bot is not None:
            return self.wb_bot
        sheet_data = await self.get_spreadsheet_data()
        wb_token = sheet_data["wb_token"]
        spreadsheet_url = sheet_data["spreadsheet_url"]
        worksheet_name = sheet_data["worksheet"]
        self.wb_bot = wb.SheetsBot(wb_token, spreadsheet_url, worksheet_name, "library/gspread_credentials.json")
        return self.wb_bot

    @commands.group(name="sheets", brief="Работа с таблицами (dev)", invoke_without_command=True)
    async def sheets(self, ctx: commands.Context):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Низя")
            return
        await ctx.send_help(ctx.command)

    @sheets.command(name="update", brief="Обновить дату (dev)", aliases=["u"])
    async def sheets_update(self, ctx: commands.Context, date: str = None):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Низя")
            return
        if date is None:
            await ctx.send("Укажите дату!")
            return
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            await ctx.send("Неправильно указана дата, пример: "+wb.SheetsBot.get_yesterday_date())
            return
        await ctx.send("Обновляю...")
        wb_bot = await self.try_get_wb_bot()
        stats = await wb_bot.get_fullstats(date)
        try:
            await wb_bot.update_table_with_data(date, stats)
        except wb.DateNotFound:
            log(f"Date not found in table: {date}")
        await ctx.send("Дата обновлена")

    @sheets.command(name="last", brief="Задать дату для обновлений (dev)", aliases=["l"])
    async def set_last_update(self, ctx: commands.Context, date: str = None):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Низя")
            return
        if date is None:
            await ctx.send("Укажите дату! Например: "+wb.SheetsBot.get_yesterday_date())
            return
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            await ctx.send("Неправильно указана дата, пример: " + wb.SheetsBot.get_yesterday_date())
            return
        await self.set_spreadsheet_data(last_update=date)
        await ctx.send("Дата перезаписана")

    @sheets.command(name="spreadsheet", brief="Изменить таблицу (dev)", aliases=["sp"])
    async def sheets_url(self, ctx: commands.Context, *, url: str = None):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Низя")
            return
        if url is None:
            await ctx.send("Текущая таблица: " + (await self.get_spreadsheet_data())["spreadsheet_url"])
            await ctx.send("Укажите ссылку на таблицу если хотите ее изменить")
            return
        try:
            if wb.SheetsBot.check_spreadsheet_url(url) is False:
                await ctx.send("Таблица не найдена")
                return
        except PermissionError:
            await ctx.send("Нет доступа к таблице, добавьте бота как редактора (wbsheetsbot@wbsheetsbot441305-m5.iam.gserviceaccount.com)")
            return
        await self.set_spreadsheet_data(spreadsheet_url=url)
        self.wb_bot = None
        await ctx.send("Таблица установлена на " + url)

    @sheets.command(name="worksheet", brief="Изменить рабочий лист (dev)", aliases=["wks"])
    async def sheets_name(self, ctx: commands.Context, *, name: str = None):
        if ctx.author.id not in config.admin_ids:
            await ctx.send("Низя")
            return
        await self.set_spreadsheet_data(worksheet=name)
        self.wb_bot = None
        await ctx.send("Имя рабочего листа установлено на " + name)


async def setup(bot):
    await bot.add_cog(WbCog(bot))
