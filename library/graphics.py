import argparse
import random
import json
import numpy as np
import requests
from PIL import Image
from pexels_api import API
import ascii_magic
import config

pexels_api_key = config.pexels_apikey
tenor_api_key = config.tenor_apikey
client_key = "Bubilda"
defaultAnswer = config.main_emoji
gray_scale1 = "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,\"^`'. "
gray_scale2 = '@%#*+=-:. '


class SearchContent:
    @staticmethod
    def get_gif(searchfor="funny cat", limit=10):
        r = requests.get(
            "https://tenor.googleapis.com/v2/search?q=%s&key=%s&client_key=%s&limit=%s" % (
                searchfor, tenor_api_key, client_key, limit)
        )
        if r.status_code == 200:
            urls = []
            topgifs = json.loads(r.content)
            for i in range(len(topgifs['results'])):
                urls.append(topgifs['results'][i]['media_formats']['gif']['url'])
            if urls:
                return random.choice(urls)
            else:
                return defaultAnswer
        else:
            return defaultAnswer

    @staticmethod
    def get_image(searchfor="funny cat", limit=20, default=True):
        try:
            api = API(pexels_api_key)
            api.search(searchfor, page=1, results_per_page=limit)
            photos = api.get_entries()
            urls = [photo.medium for photo in photos]
            if not len(urls): return defaultAnswer if default else False
            return random.choice(urls)
        except:
            return defaultAnswer if default else False


def get_average_l(image: Image) -> int:
    """
    Given PIL Image, return average value of grayscale value
    """
    # get image as numpy array
    im = np.array(image)

    # get shape
    w, h = im.shape

    # get average
    return np.average(im.reshape(w * h))


def covert_image_to_ascii(image: Image, cols: int, scale: float, more_levels: bool) -> list:
    global gray_scale1, gray_scale2
    image = image.convert('L')

    W, H = image.size[0], image.size[1]

    w = W / cols
    h = w / scale
    rows = int(H / h)

    if cols > W or rows > H:
        raise ValueError("Image too small for specified cols!")

    aimg = []
    for j in range(rows):
        y1 = int(j * h)
        y2 = int((j + 1) * h)
        if j == rows - 1:
            y2 = H
        aimg.append("")

        for i in range(cols):
            x1 = int(i * w)
            x2 = int((i + 1) * w)
            if i == cols - 1:
                x2 = W
            img = image.crop((x1, y1, x2, y2))
            avg = int(get_average_l(img))
            if more_levels:
                gray_scale_val = gray_scale1[int((avg * 69) / 255)]
            else:
                gray_scale_val = gray_scale2[int((avg * 9) / 255)]
            aimg[j] += gray_scale_val

    with open("out.txt", "w") as f:
        for i in range(len(aimg)):
            f.write(aimg[i] + "\n")
    return aimg
