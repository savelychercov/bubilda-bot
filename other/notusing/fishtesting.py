from dataclasses import dataclass
import random


fish_price_aberration =0.5

@dataclass
class FishData:
    name: str
    description: str
    emoji: str
    image: str
    cost: int
    size: tuple[int, int]


@dataclass
class Fish:
    name: str
    description: str
    emoji: str
    image: str
    cost: int
    size: int


def fish_gen(fish_data: FishData) -> Fish:
    size = random.randint(fish_data.size[0], fish_data.size[1])
    average_size = (fish_data.size[0] + fish_data.size[1]) / 2
    max_delta = average_size - fish_data.size[0]
    delta_size = size - average_size
    aberration_coeff = delta_size / max_delta
    cost = round(aberration_coeff * fish_price_aberration * fish_data.cost + fish_data.cost)
    fish = Fish(
        name=fish_data.name,
        description=fish_data.description,
        emoji=fish_data.emoji,
        image=fish_data.image,
        cost=cost,
        size=size
    )
    return fish


def get_random_fish(power: int) -> Fish:
    if power == 1:
        fish_data = random.choice(small_fish)
    elif power == 2:
        fish_data = random.choice(medium_fish)
    else:  # power == 3:
        fish_data = random.choice(large_fish)
    return fish_gen(fish_data)


small_fish = [  # 194, 194, 194
    FishData(name="Рыба клоун",
             description="Клоун как ты",
             emoji=":tropical_fish:",
             image="https://www.stellexshop.ru/upload/iblock/ed0/erz977qq64a5iugh7gjgn928ld83r7dz/nemo480.jpg",
             cost=1000,
             size=(5, 14)),
    FishData(name="Карасик",
             description="Просто рыба, что с него взять",
             emoji=":fish:",
             image="https://static.wikia.nocookie.net/fortnite/images/7/7b/%D0%9E%D1%80%D0%B0%D0%BD%D0%B6%D0%B5%D0%B2%D0%B0%D1%8F_%D1%80%D1%8B%D0%B1%D0%BA%D0%B0.png/revision/latest?cb=20210221072224&path-prefix=ru",
             cost=1000,
             size=(5, 15)),
    FishData(name="Рак",
             description="Снова сфидил",
             emoji=":lobster:",
             image="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT96PNeWr_a5P5-5oYA1jI5CpK_mdnqNV6Vpg&s",
             cost=500,
             size=(3, 10)),
]

medium_fish = [  # 98, 160, 240
    FishData(name="Синий лобстер",
             description="Как из мема",
             emoji=":lobster:",
             image="https://pikuco.ru/upload/test_stable/5a5/5a53a24f65bbcf7c756be1ccf8fb8da8.webp",
             cost=5000,
             size=(20, 35)),
    FishData(name="Рыба фугу",
             description="Смешная рыба",
             emoji=":blowfish:",
             image="https://flomaster.top/o/uploads/posts/2024-02/thumbs/1708701959_flomaster-top-p-samie-smeshnie-ribi-vkontakte-risunok-1.jpg",
             cost=3000,
             size=(10, 20)),
]

large_fish = [  # 255, 182, 79
    FishData(name="Мегаладон",
             description="ЭТО РЕАЛЬНО МЕГАЛАДОН!!!",
             emoji=":lobster:",
             image="https://i.ytimg.com/vi/sngjQpWrxAc/maxresdefault.jpg",
             cost=10000,
             size=(200, 400)),
    FishData(name="Рыба Адун",
             description="Синий",
             emoji=":fish:",
             image="https://media.tenor.com/Gr2xrowbvHgAAAAM/%D0%BF%D0%B0%D0%BF%D0%B8%D1%87-%D0%B0%D0%B4%D1%83%D0%BD.gif",
             cost=3000,
             size=(20, 35)),
]

if __name__ == "__main__":
    for i in range(10):
        fish_data = small_fish[1]
        fish = fish_gen(fish_data)
        print(
            f"{fish.name}, {fish.size}см ({fish.size-(fish_data.size[0]+fish_data.size[1])/2}) - {fish.cost}$"
        )