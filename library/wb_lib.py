import asyncio
from datetime import datetime, timedelta
from pprint import pp
import gspread
import pytz
from gspread.exceptions import APIError
from tabulate import tabulate
import time
import functools
import json
import httpx
import os


url_buyout_statistics = "https://seller-analytics-api.wildberries.ru/api/v2/nm-report/detail"
url_nomenclatures = "https://content-api.wildberries.ru/content/v2/get/cards/list"
url_campaign_fullstats = "https://advert-api.wildberries.ru/adv/v2/fullstats"
url_campaign_ids = "https://advert-api.wildberries.ru/adv/v1/promotion/count"
url_stocks = "https://statistics-api.wildberries.ru/api/v1/supplier/stocks"
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

temp_path = "library/temp/"  # "temp/" - if debug


def rate_limited(time_limit=60, max_requests=1):
    def decorator(func):
        state = {"last_call_time": 0.0, "request_count": 0}

        filename = temp_path + func.__name__ + "_rate_limit.json"

        if not os.path.exists(temp_path):
            os.makedirs(temp_path)

        # Загружаем сохранённое состояние, если файл существует
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f1:
                    state.update(json.load(f1))
            except (json.JSONDecodeError, IOError):
                print("Ошибка чтения файла состояния. Используется значение по умолчанию.")

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal state

            # Получаем текущее время
            current_time = time.time()

            # Если прошло больше времени, сбрасываем счетчик
            if current_time - state["last_call_time"] > time_limit:
                state["last_call_time"] = current_time
                state["request_count"] = 0

            # Проверяем, не превышен ли лимит запросов
            if state["request_count"] >= max_requests:
                wait_time = time_limit - (current_time - state["last_call_time"])
                print(f"Лимит запросов для функции {func.__name__} достигнут. Ожидание {wait_time:.2f} секунд до следующего запроса...")
                await asyncio.sleep(wait_time)
                # После ожидания сбрасываем время и счетчик
                state["last_call_time"] = time.time()
                state["request_count"] = 0

            # Выполняем сам запрос
            result = await func(*args, **kwargs)

            # Увеличиваем счетчик запросов
            state["request_count"] += 1

            # Сохраняем текущее состояние в файл
            try:
                with open(filename, "w", encoding="utf-8") as f2:
                    json.dump(state, f2)
            except IOError:
                # print("Ошибка записи состояния в файл.")
                raise

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

    @staticmethod
    def check_spreadsheet_url(url: str) -> bool:
        try:
            gc = gspread.service_account(filename="library/gspread_credentials.json")
            gc.open_by_url(url)
            return True
        except gspread.exceptions.SpreadsheetNotFound:
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
            nms = []
            for day in campaign_data['days']:
                for app in day['apps']:
                    for nm in app['nm']:
                        if nm['nmId'] not in nms:
                            nms.append(nm['nmId'])
            return nms
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
        return {
            nm: sum([data["sum"] for data in data_list])
            for nm, data_list in data.items()
            if data_list
        }

    @staticmethod
    def sample_buyout_stats_for_nomenclatures(buyout_stats, nomenclatures):
        data = {}
        for nm in nomenclatures:
            data[nm] = buyout_stats.get(nm, 0)
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
                response = await client.post(url_nomenclatures, headers=headers, json=payload, timeout=30)
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
            response = await client.get(url_campaign_ids, headers=headers, timeout=30)
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
    async def get_buyout_statistics(self, date: str | datetime, nms: list[int]) -> dict:
        print("Trying to get buyout statistics")
        if not isinstance(nms, list):
            nms = list(nms)

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
            if nms:
                payload["nmIDs"] = nms
            async with httpx.AsyncClient() as client:
                response = await client.post(url_buyout_statistics, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            if response.json()["data"].get("isNextPage", False):
                current_page += 1
            else:
                has_next_page = False

        r = response.json()  # noqa

        data_headers_to_select = [
            "ordersCount",
            "ordersSumRub",
            "buyoutsCount",
            "buyoutsSumRub",
            "addToCartCount",
            "avgOrdersCountPerDay",
            "avgPriceRub",
            "cancelCount",
            "cancelSumRub",
            "openCardCount",
        ]

        data_dict = {}
        for nm_id in nms:
            for nm in r["data"]["cards"]:
                if nm["nmID"] == nm_id:
                    data_dict[nm["nmID"]] = {h: nm["statistics"]["selectedPeriod"][h] for h in data_headers_to_select}
                    break
            else:
                data_dict[nm_id] = {h: None for h in data_headers_to_select}

        print(f"Got {len(data_dict)} buyout statistics")

        return self.sample_buyout_stats_for_nomenclatures(data_dict, nms)

    @rate_limited(time_limit=60, max_requests=1)
    async def get_campaign_statistics(self, dates: str | datetime | list, nms: list[int]) -> dict:
        advert_ids = await self.get_campaigns_ids()
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
            response = await client.post(url_campaign_fullstats, headers=headers, json=payload, timeout=30)
        if response.status_code != 200: print(response.json())
        response.raise_for_status()
        print("Got campaign statistics")
        return self.sample_ad_stats_for_nomenclatures(response.json(), nms)

    @staticmethod
    def get_keys(data_dict: dict, keys: list[str]):
        return {k: data_dict[k] for k in keys}

    @rate_limited(time_limit=60, max_requests=1)
    async def get_all_stocks(self, nms: list[int]):
        print("Trying to get stocks")
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json"
        }
        params = {"dateFrom": "2017-03-25T00:00:00"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url_stocks, headers=headers, params=params, timeout=30)
        if response.status_code != 200: print(response.json())
        response.raise_for_status()
        print("Got stocks")

        KEYS = {
            "quantity": "sum",
            "Price": "one",
            "Discount": "one",
            "inWayToClient": "sum",
            "inWayFromClient": "sum",
            "quantityFull": "sum",
        }

        stocks = {}
        for stock in response.json():
            if stock["nmId"] not in stocks:
                stocks[stock["nmId"]] = self.get_keys(stock, KEYS)
            else:
                for k in KEYS:
                    if KEYS[k] == "sum":
                        stocks[stock["nmId"]][k] += stock[k]

        for nm in nms:
            if nm not in stocks:
                stocks[nm] = {k: None for k in KEYS}
        return stocks

    async def get_fullstats(self, date: str) -> dict[int, dict[str, int]]:
        nms_for_statistics = [nm.id for nm in await self.get_all_nomenclatures()]

        ad_expenses, buyout_stats, stocks = await asyncio.gather(
            self.get_campaign_statistics(date, nms_for_statistics),
            self.get_buyout_statistics(date, nms_for_statistics),
            self.get_all_stocks(nms_for_statistics)
        )

        fullstats = {}
        for nm in nms_for_statistics:
            fullstats[nm] = {}
            fullstats[nm]["adExpenses"] = ad_expenses.get(nm, 0)
            fullstats[nm] |= buyout_stats[nm]
            fullstats[nm] |= stocks[nm]

        if not os.path.exists(temp_path):
            os.makedirs(temp_path)
        with open(f"{temp_path}/{date}fullstats.json", "w", encoding="utf-8") as f:
            json.dump(fullstats, f, indent=4)

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
        print("Getting data from table...")
        table_data = await asyncio.to_thread(self.wks.get_all_values)
        print(f"Got {len(table_data)} rows from table.")

        print("Retrieving a list of items from a table...")
        table_nomenclatures = await self.extract_nomenclatures()
        print(f"Founded {len(table_nomenclatures)} nomenclatures in table.")

        date_obj = datetime.strptime(date, "%Y-%m-%d")
        formatted_date = f"{date_obj.day} {MONTHS[date_obj.strftime('%B')]}"

        header_row = table_data[0]
        try:
            print(f"Searching data column for {date}...")
            header_row = [header.lower() for header in header_row]
            date_column_index = header_row.index(formatted_date) + 1
            print(f"Data column {formatted_date} founded: index {date_column_index}")
        except ValueError:
            raise ValueError(f"Data {formatted_date} not founded in table headers")

        print("Begin updating data...")
        updates = []
        for row_index, row in enumerate(table_data):
            if len(row) > 1 and row[1].isdigit():
                nm_id = int(row[1])

                if nm_id in data:
                    ad_expenses = data[nm_id].get('adExpenses', 0)
                    if ad_expenses is None:
                        ad_expenses = 0
                    orders_count = data[nm_id].get('ordersCount', 0)
                    if orders_count is None:
                        orders_count = 0
                    stocks = data[nm_id].get('quantity', 0)
                    if stocks is None:
                        stocks = 0

                    if date == self.get_yesterday_date():
                        updates.append({
                            'range': self.cell(date_column_index, row_index + 3),
                            'values': [[stocks]]
                        })
                    updates.append({
                        'range': self.cell(date_column_index, row_index + 2),
                        'values': [[ad_expenses]]
                    })
                    updates.append({
                        'range': self.cell(date_column_index, row_index + 1),
                        'values': [[orders_count]]
                    })

        if updates:
            try:
                await asyncio.to_thread(self.wks.batch_update, updates)
                print("Data successfully updated")
            except APIError as e:
                print(f"APIError: {e}")
        else:
            print("No updates")

    async def print_table(self):
        data = self.wks.get_all_values()
        print(tabulate(data, tablefmt="grid"))


async def main():
    with open("spreadsheet_data.json", "r", encoding="utf-8") as f:
        sheet_data = json.load(f)
    t = sheet_data["wb_token"]

    headers = {
        "Authorization": t,
        "Content-Type": "application/json"
    }

    cursor = {
        "limit": 100
    }

    nomenclatures = []

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
            response = await client.post(url_nomenclatures, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        for i in range(len(data.get('cards', []))):
            nomenclatures.append(Nomenclature(data['cards'][i]))

        total = data["cursor"]["total"]
        if total < cursor['limit']:
            break

        cursor['updatedAt'] = data['cursor']['updatedAt']
        cursor['nmID'] = data['cursor']['nmID']

    nms = [nm.id for nm in nomenclatures]  # list of nomenclature ids

    headers = {
        "Authorization": t,
        "Content-Type": "application/json"
    }
    params = {"dateFrom": "2017-03-25T00:00:00"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url_stocks, headers=headers, params=params, timeout=30)

    with open("temp_stocks.json", "w", encoding="utf-8") as f:
        json.dump(response.json(), f, indent=4, ensure_ascii=False)

    response.raise_for_status()

    KEYS = {
        "quantity": "sum",
        "Price": "one",
        "Discount": "one",
        "inWayToClient": "sum",
        "inWayFromClient": "sum",
        "quantityFull": "sum",
    }

    stocks = {}
    for stock in response.json():
        if stock["nmId"] not in stocks:
            stocks[stock["nmId"]] = {k: stock[k] for k in KEYS}
        else:
            for k in KEYS:
                if KEYS[k] == "sum":
                    stocks[stock["nmId"]][k] += stock[k]

    for nm in nms:
        if nm not in stocks:
            stocks[nm] = {k: None for k in KEYS}

    with open("temp_counted_stocks.json", "w", encoding="utf-8") as f:
        json.dump(stocks, f, indent=4, ensure_ascii=False)

    """with open("temp_stocks.json", "r", encoding="utf-8") as f:
        stocks = json.load(f)

    for stock in stocks:
        nmid = 267706059
        if stock["nmId"] == nmid:
            print(json.dumps(stock, indent=4, ensure_ascii=False))"""


if __name__ == "__main__":
    asyncio.run(main())
