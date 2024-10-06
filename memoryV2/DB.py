from dataclasses import dataclass
from typing import Any
import datetime


class DataBase:
    """DataBase class for easy work with files"""
    def __init__(self, key: str, slice_key: str = "♦"):
        self.key = key
        self.slice_key = slice_key

    def clear_all_keys(self, filename: str | int):
        filename = str(filename)
        open("memoryV2/" + self.key + filename + ".txt", "w+", encoding="utf-8").close()

    def read_all_keys(self, filename: str | int):
        filename = str(filename)
        try:
            with open("memoryV2/" + self.key + filename + ".txt", "r", encoding="utf-8") as file:
                lines = {}
                for line in file:
                    if not line.strip():
                        continue
                    key, data = line.split(self.slice_key)
                    # key, data = key.strip(), data.strip()
                    lines[key] = data
                return lines
        except FileNotFoundError:
            return {}

    def set_all_keys(self, filename: str | int, keys: dict[str | int, str | int]):
        filename = str(filename)

        with open("memoryV2/" + self.key + filename + ".txt", "w+", encoding="utf-8") as file:
            for key, value in keys.items():
                string = str(key) + self.slice_key + str(value)+"\n"
                file.write(string)

    def new_key(self, filename: str | int, new_key: str | int, value: str | int):
        new_key, value = str(new_key), str(value)

        if self.slice_key in new_key:
            raise ValueError(f"Key can't contain {self.slice_key}!")

        data = self.read_all_keys(filename)
        data[new_key] = value
        self.set_all_keys(filename, data)

    def read_key(self, filename: str | int, key: str | int) -> str | None:
        filename = str(filename)
        key = str(key)
        return self.read_all_keys(filename).get(key, None)

    def del_key(self, filename: str | int, key: str | int) -> str:
        filename = str(filename)
        key = str(key)

        data = self.read_all_keys(filename)
        value = data.get(key, None)

        if value is not None:
            del data[key]
            self.set_all_keys(filename, data)

        return value


class DefinedDataBase():
    def __init__(self, key_type: type, data_class: dataclass, key: str, slice_key: str = "♦"):
        self.__db = DataBase(key, slice_key)
        self.key_type = key_type
        self.data_class = data_class

    def get_dataclass_from_str(self, string: str | None) -> dataclass:
        if string is None:
            return None
        cls = self.data_class
        string = "cls"+string[string.find("("):]
        return eval(string)

    @staticmethod
    def get_str_from_dataclass(data_class: dataclass):
        if data_class is None:
            raise ValueError("dataclass can't be None")
        return str(data_class)

    def get_all_obj(self, filename: str | int) -> dict[str | int, dataclass]:
        raw_dict = self.__db.read_all_keys(filename)
        obj_dict = {}
        for key, value in raw_dict.items():
            obj_dict[self.key_type(key)] = self.get_dataclass_from_str(value)
        return obj_dict

    def set_all_obj(self, filename: str | int, obj_dict: dict[str | int, dataclass]) -> None:
        raw_dict = {}
        for key, value in obj_dict.items():
            raw_dict[str(key)] = self.get_str_from_dataclass(value)
        self.__db.set_all_keys(filename, raw_dict)

    def clear_all_obj(self, filename: str | int) -> None:
        data = self.get_all_obj(filename)
        self.__db.clear_all_keys(filename)
        return data

    def get_obj(self, filename: str | int, key: str | int) -> dataclass:
        return self.get_dataclass_from_str(self.__db.read_key(str(filename), str(key)))

    def set_obj(self, filename: str | int, key: str | int, obj: dataclass) -> None:
        self.__db.new_key(str(filename), str(key), self.get_str_from_dataclass(obj))

    def del_obj(self, filename: str | int, key: str | int) -> dataclass:
        return self.get_dataclass_from_str(self.__db.del_key(str(filename), str(key)))


if __name__ == "__main__":
    @dataclass
    class Test:
        name: str
        a: int
        b: int

    db = DefinedDataBase(int, Test, "test")

    t = Test(name="test", a=1, b=2)
    t2 = Test(name="test2", a=3, b=4)
    t3 = Test(name="test3", a=5, b=6)
    t4 = Test(name="test4", a=7, b=8)

    db.set_obj(10973538923984, 2245823949889, t)
    db.set_obj(10973538923984, 2243523949888, t2)
    db.set_obj(10973538923984, 2245823949887, t3)
    db.set_obj(10973538923984, 2245823412886, t4)
    print(db.get_all_obj(10973538923984))
