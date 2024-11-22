import asyncio
from datetime import datetime, timedelta
from pprint import pp
import gspread
import pytz
from tabulate import tabulate
import time
import functools
import json
import httpx


url_buyout_statistics = "https://seller-analytics-api.wildberries.ru/api/v2/nm-report/detail"
url_nomenclatures = "https://content-api.wildberries.ru/content/v2/get/cards/list"
url_campaign_fullstats = "https://advert-api.wildberries.ru/adv/v2/fullstats"
url_campaign_ids = "https://advert-api.wildberries.ru/adv/v1/promotion/count"
MONTHS = {
    "January": "января",
    "February": "февраля",
    "March": "марта",
    "April": "апреля",
    "May": "мая",
    "June": "июня",
    "July": "июля",
    "August": "августа",
    "September": "сентября",
    "October": "октября",
    "November": "ноября",
    "December": "декабря",
}


def rate_limited(time_limit=60, max_requests=1):
    def decorator(func):
        last_call_time = 0  # Время последнего вызова
        request_count = 0    # Количество запросов в текущем интервале

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal last_call_time, request_count

            # Получаем текущее время
            current_time = time.time()

            # Если прошло больше времени, сбрасываем счетчик
            if current_time - last_call_time > time_limit:
                last_call_time = current_time
                request_count = 0

            # Проверяем, не превышен ли лимит запросов
            if request_count >= max_requests:
                wait_time = time_limit - (current_time - last_call_time)
                print(f"Лимит запросов достигнут. Ожидание {wait_time:.2f} секунд до следующего запроса...")
                await asyncio.sleep(wait_time)
                # После ожидания сбрасываем время и счетчик
                last_call_time = time.time()
                request_count = 0

            # Выполняем сам запрос
            result = await func(*args, **kwargs)

            # Увеличиваем счетчик запросов
            request_count += 1

            return result

        return wrapper
    return decorator


class DateNotFound(Exception):
    pass


class Nomenclature:
    def __init__(self, nomenclature: dict):
        self.id = nomenclature["nmID"]
        self.imt_id = nomenclature["imtID"]
        self.name = nomenclature["title"]
        self.brand = nomenclature["brand"]
        if nomenclature.get("photos", False) and len(nomenclature["photos"]) > 0:
            self.main_photo_url = nomenclature["photos"][0]["big"]
        else:
            self.main_photo_url = None
        self.raw_dict = nomenclature

    def __repr__(self):
        return f"{"-" * 10}\nNomenclature:\nName: {self.name}\nBrand: {self.brand}\nID: {self.id}\nIMT: {self.imt_id}\nURL: {self.main_photo_url}\n{"-" * 10}"


class SheetsBot:
    def __init__(self, token: str, spreadsheet_url: str, worksheet_name: str, creds_path: str = 'credentials.json'):
        self.gc = gspread.service_account(filename=creds_path)
        self.token = token
        self.spreadsheet = self.gc.open_by_url(spreadsheet_url)
        try:
            self.wks = self.spreadsheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            raise
        self.nms_for_statistics = None
        self.advert_ids = None

    def check_spreadsheet_url(self, url: str) -> bool:
        try:
            self.gc.open_by_url(url)
            return True
        except gspread.exceptions.SpreadsheetNotFound:
            return False

    def check_worksheet_name(self, name: str) -> bool:
        try:
            self.spreadsheet.worksheet(name)
            return True
        except gspread.exceptions.WorksheetNotFound:
            return False

    def set_worksheet_name(self, name: str) -> bool:
        try:
            self.wks = self.spreadsheet.worksheet(name)
            return True
        except gspread.exceptions.WorksheetNotFound:
            return False

    @staticmethod
    def get_yesterday_date() -> str:
        moscow_tz = pytz.timezone('Europe/Moscow')
        return (datetime.now(moscow_tz) - timedelta(days=1)).strftime("%Y-%m-%d")

    @staticmethod
    def cell(x, y):
        letters = ""
        while x > 0:
            x, remainder = divmod(x - 1, 26)
            letters = chr(65 + remainder) + letters
        return f"{letters}{y}"

    @staticmethod
    def sample_ad_stats_for_nomenclatures(raw_ad_stats, nomenclatures):
        def get_nomenclatures_from_campaign(campaign_data: dict) -> list[int]:
            nomenclatures = []
            for day in campaign_data['days']:
                for app in day['apps']:
                    for nm in app['nm']:
                        if nm['nmId'] not in nomenclatures:
                            nomenclatures.append(nm['nmId'])
            return nomenclatures
        keys = [
            "advertId",
            "views",
            "clicks",
            "ctr",
            "sum",
            "orders",
            "atbs",
            "shks",
            "sum_price"
        ]
        data = {}
        for nm in nomenclatures:
            data[nm] = []
            for ad_stat in raw_ad_stats:
                if nm in get_nomenclatures_from_campaign(ad_stat):
                    data[nm].append({key: ad_stat[key] for key in keys})
        return data

    @staticmethod
    def sample_buyout_stats_for_nomenclatures(buyout_stats, nomenclatures):
        data = {}
        for nm in nomenclatures:
            for buyout_nm in buyout_stats:
                if nm == buyout_nm:
                    data[nm] = buyout_stats[buyout_nm]
        return data

    @rate_limited(time_limit=60, max_requests=100)
    async def get_all_nomenclatures(self, count: int = None) -> list[Nomenclature]:
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }

        if count is None or count > 100:
            cursor = {
                "limit": 100
            }
        else:
            cursor = {
                "limit": count
            }

        nomenclatures = []

        print("Trying to get all nomenclatures")

        while True:
            print("Getting nomenclatures...")
            payload = {
                "settings": {
                    "cursor": cursor,
                    "filter": {
                        "withPhoto": -1
                    }
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url_nomenclatures, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            for i in range(len(data.get('cards', []))):
                nomenclatures.append(Nomenclature(data['cards'][i]))

            total = data["cursor"]["total"]
            if total < cursor['limit']:
                break

            cursor['updatedAt'] = data['cursor']['updatedAt']
            cursor['nmID'] = data['cursor']['nmID']

        print(f"Got {len(nomenclatures)} nomenclatures")

        return nomenclatures

    @rate_limited(time_limit=60, max_requests=5)
    async def get_campaigns_ids(self) -> list[int]:
        print("Trying to get campaigns ids")
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url_campaign_ids, headers=headers)
        if response.status_code != 200: print(response.json())
        response.raise_for_status()

        advert_ids: dict[int, tuple[str, datetime]] = {}
        for advert_list in response.json()["adverts"]:
            for advert in advert_list["advert_list"]:
                ad_id = int(advert["advertId"])
                status = advert_list["status"]
                advert_ids[ad_id] = (status, datetime.strptime(advert["changeTime"], "%Y-%m-%dT%H:%M:%S.%f%z"))
        sorted_ids = sorted(advert_ids.items(), key=lambda x: x[1][1], reverse=True)
        print(f"Got {len(sorted_ids)} campaign ids")
        return [i[0] for i in sorted_ids]

    @rate_limited(time_limit=60, max_requests=3)
    async def get_buyout_statistics(
            self,
            date: str | datetime,
            nomenclatures: list[int]) -> dict[int, dict[str, int]]:

        print("Trying to get buyout statistics")
        if not isinstance(nomenclatures, list):
            nomenclatures = list(nomenclatures)

        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }

        current_page = 1
        has_next_page = True

        while has_next_page:

            payload = {
                "timezone": "Europe/Moscow",
                "period": {
                    "begin": f"{date} 00:00:00",
                    "end": f"{date} 23:59:59"
                },
                "page": current_page
            }
            if nomenclatures:
                payload["nmIDs"] = nomenclatures
            async with httpx.AsyncClient() as client:
                response = await client.post(url_buyout_statistics, headers=headers, json=payload)
            response.raise_for_status()
            if response.json()["data"].get("isNextPage", False):
                current_page += 1
            else:
                has_next_page = False

        r = response.json()  # noqa

        data_headers_to_select = [
            "ordersCount",
            # "ordersSumRub",
            # "buyoutsCount",
            # "buyoutsSumRub",
            # 'addToCartCount',
            # 'avgOrdersCountPerDay',
            # 'avgPriceRub',
            # 'begin',
            # 'cancelCount',
            # 'cancelSumRub',
            # 'end',
            # 'openCardCount',
        ]

        data_dict = {}
        for nm_id in nomenclatures:
            for nm in r["data"]["cards"]:
                if nm["nmID"] == nm_id:
                    data_dict[nm["nmID"]] = {h: nm["statistics"]["selectedPeriod"][h] for h in data_headers_to_select}
                    break
            else:
                data_dict[nm_id] = {h: None for h in data_headers_to_select}

        print(f"Got {len(data_dict)} buyout statistics")
        return data_dict

    @rate_limited(time_limit=60, max_requests=1)
    async def get_campaign_statistics(self, advert_ids: list[int], dates: str | datetime | list) -> dict:
        print("Trying to get campaign statistics")
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }

        if isinstance(dates, datetime):
            dates = [dates.strftime("%Y-%m-%d")]
        elif isinstance(dates, list):
            for i, d in enumerate(dates):
                if isinstance(d, datetime):
                    dates[i] = d.strftime("%Y-%m-%d")
            dates = dates
        elif isinstance(dates, str):
            dates = [dates]
        else:
            raise ValueError("Invalid date format")

        payload = []
        for ad_id in advert_ids:
            payload.append({
                "id": ad_id,
                "dates": dates
            })

        async with httpx.AsyncClient() as client:
            response = await client.post(url_campaign_fullstats, headers=headers, json=payload)
        if response.status_code != 200: print(response.json())
        response.raise_for_status()
        print("Got campaign statistics")
        return response.json()

    async def get_fullstats(self, date: str) -> dict[int, dict[str, int]]:
        if self.nms_for_statistics is None:
            self.nms_for_statistics = [nm.id for nm in await self.get_all_nomenclatures()]
        if self.advert_ids is None:
            self.advert_ids = await self.get_campaigns_ids()
        raw_ad_stats = await self.get_campaign_statistics(self.advert_ids, date)
        nomenclatures_ad_stats = self.sample_ad_stats_for_nomenclatures(raw_ad_stats, self.nms_for_statistics)
        nomenclatures_ad_expenses = {nm: sum([data["sum"] for data in data_list]) for nm, data_list in
                                     nomenclatures_ad_stats.items() if data_list}

        buyout_stats = await self.get_buyout_statistics(date, self.nms_for_statistics)
        nomenclatures_buyout_stats = self.sample_buyout_stats_for_nomenclatures(buyout_stats, self.nms_for_statistics)

        fullstats = {}
        for nm in self.nms_for_statistics:
            fullstats[nm] = {}
            fullstats[nm]["adExpenses"] = nomenclatures_ad_expenses.get(nm, None)
            fullstats[nm] |= nomenclatures_buyout_stats[nm]
        return fullstats

    async def write_fullstats_to_table(self, date, fullstats) -> None:
        table = [[date, f"Обновлено в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"],
                 ["Номенклатуры", "Заказы", "Траты по рекламе"]]
        for nm in fullstats:
            table.append([
                nm,
                fullstats[nm]["ordersCount"],
                fullstats[nm]["adExpenses"]
            ])

        self.wks.update(table, self.cell(1, 1))

    async def extract_nomenclatures(self) -> dict[int, tuple[int, int]]:
        data = self.wks.get_all_values()
        nomenclatures = {}  # nm: x, y

        for i in range(len(data)):  # y
            row = data[i]
            if len(row) > 1 and row[1].isdigit():
                nomenclatures[int(row[1])] = (1, i+1)

        return nomenclatures

    async def update_table_with_data(self, date: str, data: dict[int, dict[str, float | int]]) -> None:
        print("Загрузка данных из таблицы...")
        table_data = await asyncio.to_thread(self.wks.get_all_values)
        print(f"Получено {len(table_data)} строк из таблицы.")

        print("Извлечение списка номенклатур из таблицы...")
        table_nomenclatures = await self.extract_nomenclatures()
        print(f"Найдено {len(table_nomenclatures)} номенклатур в таблице.")

        # Форматируем дату
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = f"{date_obj.day} {MONTHS[date_obj.strftime('%B')]}"

        # Поиск столбца с датой
        header_row = table_data[0]
        try:
            print(f"Поиск столбца с датой {date}...")
            header_row = [header.lower() for header in header_row]
            date_column_index = header_row.index(formatted_date) + 1
            print(f"Столбец с датой {formatted_date} найден: индекс {date_column_index}.")
        except ValueError:
            raise ValueError(f"Дата {formatted_date} не найдена в заголовке таблицы.")

        print("Начало обновления данных...")
        for row_index, row in enumerate(table_data):
            if len(row) > 1 and row[1].isdigit():
                nm_id = int(row[1])

                if nm_id in data:
                    ad_expenses = data[nm_id].get('adExpenses', 0)
                    orders_count = data[nm_id].get('ordersCount', 0)

                    # Обновляем "РК расходы"
                    if not table_data[row_index + 2][date_column_index]:
                        await asyncio.to_thread(
                            self.wks.update,
                            self.cell(date_column_index, row_index + 2),
                            [[ad_expenses]],
                        )

                    # Обновляем "Факт"
                    if not table_data[row_index + 1][date_column_index]:
                        await asyncio.to_thread(
                            self.wks.update,
                            self.cell(date_column_index, row_index + 1),
                            [[orders_count]],
                        )

        print("Обновление данных завершено.")

    async def print_table(self):
        data = self.wks.get_all_values()
        print(tabulate(data, tablefmt="grid"))

    async def main(self):
        date = self.get_yesterday_date()
        fullstats = await self.get_fullstats(date)
        pp(fullstats)
        await self.write_fullstats_to_table(date, fullstats)


async def test():
    with open("library/spreadsheet_data.json", "r", encoding="utf-8") as f:
        sheet_data = json.load(f)
    t = sheet_data["token"]
    url = sheet_data["spreadsheet_url"]
    worksheet = sheet_data["worksheet"]
    try:
        bot = SheetsBot(t, url, worksheet, "gspread_credentials.json")
    except gspread.exceptions.WorksheetNotFound:
        print("Worksheet not found")
        return
    start = time.time()
    for date in ["2024-11-12", "2024-11-13", "2024-11-14", "2024-11-15", "2024-11-16", "2024-11-17", "2024-11-18", "2024-11-19", "2024-11-20"]:
        stats = await bot.get_fullstats(date)
        await bot.update_table_with_data(date, stats)
    print(f"Обновлено за: {round(time.time() - start, 2)}s")


"""async def test():
    t = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjIwMjQxMDE2djEiLCJ0eXAiOiJKV1QifQ.eyJlbnQiOjEsImV4cCI6MTc0NzA3MjcyNCwiaWQiOiIwMTkzMTljZC05OGZjLTc0ZTQtODlkYy01ZWY5OTJkZTFmNzQiLCJpaWQiOjkyMDQ3Mzk2LCJvaWQiOjI2MDAzMSwicyI6NzAsInNpZCI6IjdlNTVjYTBlLWY1ZWUtNGZkYS05MTYxLTcyYmU0ZDYzNGIzMyIsInQiOmZhbHNlLCJ1aWQiOjkyMDQ3Mzk2fQ.uFmN-AO_ITEWu0izi51u5nxkK2YpBygTkitGAz5hwU7Hq0Og_GgCayRT5C83o6Aq6hfshU-2TMsT_VExFR3BtQ"
    url = "https://docs.google.com/spreadsheets/d/1BYgOEkCIogghLS-iu93aIAhfchMjzY_zSvc8XfWuH2c"
    worksheet = "План продаж"
    bot = SheetsBot(t, url, worksheet, "gspread_credentials.json")
    data = bot.wks.get_all_values()
    # print(tabulate(data, tablefmt="grid"))"""

if __name__ == "__main__":
    asyncio.run(test())
