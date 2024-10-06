from dataclasses import dataclass

import config

keys_key = config.keys_key
marry_key = config.marry_key
balance_key = config.balance_key
daily_key = config.daily_key
coinflip_key = config.coinflip_key
dates_key = config.dates_key
pisi_key = config.pisi_key
shop_key = config.shop_key
inventory_key = config.inventory_key


def readall(filename: str):
    try:
        with open("memory/" + filename + ".txt", "r", encoding="utf-8") as file:
            lines = {}
            for line in file:
                key, data = line.split("|")
                key, data = key.strip(), data.strip()
                lines[key] = data
            return lines
    except:
        return None


def read_key(filename: str, key: str):
    key = key.lower()
    try:
        with open("memory/" + filename + ".txt", "r", encoding="utf-8") as file:
            for line in file:
                local_key, data = line.split("|")
                local_key, data = local_key.strip(), data.strip()
                if local_key == key:
                    return data
            return None
    except:
        return None


def delete_key(filename: str, key: str):
    key = key.lower()
    try:
        file = readall(filename)
        file.pop(key)
        with open("memory/" + filename + ".txt", "w+", encoding="utf-8") as f:
            for k in file:
                f.write(k + " | " + file[k] + "\n")
        return True
    except:
        return False


def clear_keys(filename: str):
    open("memory/" + filename + ".txt", "w+", encoding="utf-8")


def new_key(filename: str, key: str, data: str):
    key, data = str(key.lower()), str(data)
    delete_key(filename, key)

    try:
        with open("memory/" + filename + ".txt", "a+", encoding="utf-8") as f:
            f.write(key + " | " + data + "\n")
    except:
        with open("memory/" + filename + ".txt", "w+", encoding="utf-8") as f:
            f.write(key + " | " + data + "\n")


"""-------------------------------------------------------------------------------------------"""


class KeysData:
    @staticmethod
    def new_key(filename: str, key: str, data: str):
        new_key(keys_key + filename, key, data)

    @staticmethod
    def read_all(filename: str):
        return readall(keys_key + filename)

    @staticmethod
    def read_key(filename: str, key: str):
        return read_key(keys_key + filename, key)

    @staticmethod
    def delete_key(filename: str, key: str):
        return delete_key(keys_key + filename, key)

    @staticmethod
    def clear_keys(filename: str):
        clear_keys(keys_key + filename)


def married_on_user(filename: str, user: str):
    marriages = readall(marry_key + filename)
    try:
        return marriages[user]
    except KeyError:
        if marriages:
            for member in marriages:
                if marriages[member] == user:
                    return member
            return False
        else:
            return False


class MarryData:
    @staticmethod
    def new_marry(filename: str, user: str, married_on: str):
        new_key(marry_key + filename, user, married_on)

    @staticmethod
    def check_marry(filename: str, user: str):
        return married_on_user(filename, user)

    @staticmethod
    def divorce(filename: str, user: str):
        return delete_key(marry_key + filename, user) or delete_key(marry_key + filename, married_on_user(filename, user))

    @staticmethod
    def married_users(filename: str):
        return readall(marry_key + filename)


"""-------------------------------------------------------------------------------------------"""


def default(money):
    try:
        float(money)
    except:
        return None
    return "{:1.0f}".format(money)


start_balance = config.start_balance


class BalanceData:

    @staticmethod
    def set_balance(filename: str, user: str, balance: float | int | str):
        balance = default(balance)
        new_key(balance_key + filename, user, balance)

    @staticmethod
    def get_balance(filename: str, user: str):
        filename = str(filename)
        user = str(user)

        balance = read_key(balance_key + filename, user)
        if balance is None:
            balance = start_balance
            new_key(balance_key + filename, user, balance)
        return int(balance)

    @staticmethod
    def add_balance(filename: str, user: str, money: float | int):
        filename = str(filename)
        user = str(user)
        old_balance = read_key(balance_key + filename, user)
        if old_balance is None: old_balance = start_balance
        old_balance = int(old_balance)
        if old_balance + money < 0:
            return old_balance + money
        new_key(balance_key + filename, user, default(int(old_balance) + money))

    def allbalance(filename: str):
        return readall(balance_key + filename)

    def checkdaily(filename: str, user: str, today: str):
        check = read_key(daily_key + filename, user)
        new_key(daily_key + filename, user, today)
        if check == today:
            return False
        else:
            return True


class CoinflipData:

    @staticmethod
    def new_bid(filename: str, user: str, money: int | float):
        money = default(money)
        new_key(coinflip_key + filename, user, money)

    @staticmethod
    def del_bid(filename: str, user: str):
        return delete_key(coinflip_key + filename, user)

    @staticmethod
    def check_bid(filename: str, user: str):
        bid = read_key(coinflip_key + filename, user)
        if bid is None:
            return False
        else:
            return bid

    @staticmethod
    def get_bids(filename: str):
        return readall(coinflip_key + filename)


class DatesData:

    @staticmethod
    def get_dates(filename: str):
        return readall(dates_key + filename)

    @staticmethod
    def new_date(filename: str, date: str, name: str):
        new_key(dates_key + filename, name, date)

    @staticmethod
    def del_date(filename: str, name: str):
        return delete_key(dates_key + filename, name)


class PencilsData:

    @staticmethod
    def get_all_pisi(filename: str):
        return readall(pisi_key + filename)

    @staticmethod
    def set_pisa(filename: str, user: str, heigth: int):
        new_key(pisi_key + filename, user, heigth)

    @staticmethod
    def checkdaily_pisa(filename: str, user: str, today: str):
        filename = str(filename)
        user = str(user)
        check = read_key(pisi_key + daily_key + filename, user)
        new_key(pisi_key + daily_key + filename, user, today)
        if check == today:
            return False
        else:
            return True

    @staticmethod
    def add_heigth(filename: str | int, user: str | int, height: int):
        old_height = read_key(pisi_key + str(filename), str(user))
        if old_height is None: old_height = 0
        new_key(pisi_key + str(filename), str(user), int(old_height) + height)

    @staticmethod
    def get_pisa(filename: str | int, user: str | int):
        height = read_key(pisi_key + str(filename), str(user))
        if height is None:
            height = 0
            new_key(pisi_key + filename, user, height)
        return int(height)

    @staticmethod
    def log(filename: str, user: str, date: str, value):
        file = pisi_key + "log" + str(filename)
        user = str(user)
        if (t := read_key(file, user)) is not None:
            if (last := t.split("/")[-1]).split(":")[0] == date:
                new_key(file, user,
                    "/".join(t.split("/")[:-1]) + "/" + last.split(":")[0] + ":" + str(int(last.split(":")[1]) + value))
            else:
                new_key(file, user, t + "/" + date + ":" + str(value))
        else:
            new_key(file, user, "0/" + date + ":" + str(value))

    @staticmethod
    def get_last_plus(filename: str | int, user: str | int):
        log_str = read_key(pisi_key + "log" + str(filename), str(user))

        if log_str is None:
            return 0

        try:
            return int(log_str.split("/")[-1].split(":")[1])
        except IndexError:
            return int(int(log_str.split("/")[-1]))


@dataclass
class ShopSlot:
    id: int
    thing: str
    amount: int
    price: float
    user_id: int


class ShopData:

    # shop:
    # id | thing:amount:price:user_id
    # id: int (counter)
    # thing: str
    # amount: int
    # price: float
    # user_id: str

    @staticmethod
    def get_shop(filename: str | int) -> list[ShopSlot]:
        raw_dict = readall(shop_key + str(filename))

        if raw_dict is None:
            return []

        shop_list = []
        for slot_id, item in raw_dict.items():
            thing, amount, price, user_id = item.split(":")
            shop_list.append(ShopSlot(int(slot_id), thing, int(amount), float(price), int(user_id)))

        shop_list = sorted(shop_list, key=lambda x: x.id)

        return shop_list

    @staticmethod
    def set_shop(filename: str | int, shop_list: list[ShopSlot]):
        clear_keys(shop_key + str(filename))

        shop_list = sorted(shop_list, key=lambda x: x.id)

        for slot in shop_list:
            new_key(
                shop_key + str(filename),
                str(slot.id),
                f"{slot.thing}:{slot.amount}:{slot.price}:{slot.user_id}")

    @staticmethod
    def get_slot(filename: str | int, slot_id: int) -> ShopSlot:
        slot_data = read_key(shop_key + str(filename), str(slot_id))
        if slot_data is None:
            return None

        thing, amount, price, user_id = slot_data.split(":")
        slot = ShopSlot(slot_id, thing, int(amount), float(price), int(user_id))
        return slot

    @staticmethod
    def add_to_shop(filename: str | int, thing: str, amount: int, price: float | int, user_id: int):
        slots_list = ShopData.get_shop(filename)
        ids = [x.id for x in slots_list]
        slot_id = 1
        while slot_id in ids:
            slot_id += 1
        new_slot = ShopSlot(slot_id, thing, amount, price, user_id)
        slots_list.append(new_slot)
        ShopData.set_shop(filename, slots_list)
        return slot_id

    @staticmethod
    def remove_slot(filename: str | int, slot_id: int):
        slots_list = ShopData.get_shop(filename)

        for i in slots_list:
            if i.id == slot_id:
                slots_list.remove(i)
                break

        ShopData.set_shop(filename, slots_list)

    @staticmethod
    def remove_slot_by_user(filename: str | int, user_id: int | str):
        user_id = int(user_id)
        slots_list = ShopData.get_shop(filename)

        for i in slots_list:
            if i.user_id == user_id:
                slots_list.remove(i)

        ShopData.set_shop(filename, slots_list)


class InventoryData:

    # inv:
    # user_id | thing1:uses1, thing2:uses2, thingN:usesN
    # thing: str
    # uses: int

    @staticmethod
    def get_inv(filename: str | int, user: str | int) -> dict[str, int]:
        inv_str = read_key(inventory_key + str(filename), str(user))

        if inv_str is None or inv_str == "":
            return {}

        inv = {}
        for item in inv_str.split("/"):
            thing, uses = item.split(":")
            inv[thing] = int(uses)

        return inv

    """def get_all_invs(filename: str | int) -> dict[int, dict[str, int]]:
        strs_dict = readall(filekeys.inventorykey + str(filename))
        if strs_dict is None:
            return {}

        invs = {}
        for user_id, inv_str in strs_dict.items():
            invs[int(user_id)] = {}
            for item in inv_str.split("/"):
                thing, uses = item.split(":")
                invs[int(user_id)][thing] = int(uses)

        return invs"""

    @staticmethod
    def set_inv(filename: str | int, user: str | int, inv: dict[str, int]) -> None:
        new_key(
            inventory_key + str(filename),
            str(user), "/".join([f"{thing}:{uses}" for thing, uses in inv.items()]))

    @staticmethod
    def has_thing(filename: str | int, user: str | int, thing: str) -> bool:
        inv = InventoryData.get_inv(filename, user)
        return thing in inv

    @staticmethod
    def set_thing(filename: str | int, user: str | int, thing: str, uses: int) -> None:
        inv = InventoryData.get_inv(filename, user)
        inv[thing] = uses
        InventoryData.set_inv(filename, user, inv)

    @staticmethod
    def add_thing_or_uses(filename: str | int, user: str | int, thing: str, uses: int) -> None:
        inv = InventoryData.get_inv(filename, user)
        if thing in inv:
            inv[thing] = inv[thing] + uses
        else:
            inv[thing] = uses
        InventoryData.set_inv(filename, user, inv)

    @staticmethod
    def del_thing(filename: str | int, user: str | int, thing: str) -> bool:
        inv = InventoryData.get_inv(filename, user)

        if thing in inv:
            del inv[thing]
            InventoryData.set_inv(filename, user, inv)
            return True

        return False

    @staticmethod
    def get_uses(filename: str | int, user: str | int, thing: str) -> int:
        inv = InventoryData.get_inv(filename, user)

        if thing not in inv:
            return 0

        return inv[thing]

    @staticmethod
    def add_uses(filename: str | int, user: str | int, thing: str, uses: int) -> None:
        inv = InventoryData.get_inv(filename, user)
        if thing in inv:
            inv[thing] = str(inv[thing] + uses)
            InventoryData.set_inv(filename, user, inv)

    @staticmethod
    def use_thing(filename: str | int, user: str | int, thing: str, minus=True) -> None:
        inv = InventoryData.get_inv(filename, user)

        if thing not in inv:
            return False

        if minus: inv[thing] = inv[thing] - 1

        if inv[thing] == 0:
            del inv[thing]

        InventoryData.set_inv(filename, user, inv)
        return True
