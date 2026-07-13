from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

import datetime
import pe_api

from collections import deque

import glob
import os

from typing import List, Tuple, Optional


# create Image object
general_color = 'dark_blue'  # grey,light_blue,blue,orange,purple,yellow,green
general_font = 'images_elements/Roboto-Bold.ttf'

# create the coloured overlays
colors = {
    'dark_blue': {'c': (27, 53, 81), 'p_font': 'rgb(255,255,255)', 's_font': 'rgb(255, 212, 55)'},
    'grey': {'c': (70, 86, 95), 'p_font': 'rgb(255,255,255)', 's_font': 'rgb(93,188,210)'},
    'light_blue': {'c': (93, 188, 210), 'p_font': 'rgb(27,53,81)', 's_font': 'rgb(255,255,255)'},
    'blue': {'c': (23, 114, 237), 'p_font': 'rgb(255,255,255)', 's_font': 'rgb(255, 255, 255)'},
    'orange': {'c': (242, 174, 100), 'p_font': 'rgb(0,0,0)', 's_font': 'rgb(0,0,0)'},
    'purple': {'c': (114, 88, 136), 'p_font': 'rgb(255,255,255)', 's_font': 'rgb(255, 212, 55)'},
    'red': {'c': (255, 0, 0), 'p_font': 'rgb(0,0,0)', 's_font': 'rgb(0,0,0)'},
    'yellow': {'c': (255, 255, 0), 'p_font': 'rgb(0,0,0)', 's_font': 'rgb(27,53,81)'},
    'yellow_green': {'c': (232, 240, 165), 'p_font': 'rgb(0,0,0)', 's_font': 'rgb(0,0,0)'},
    'green': {'c': (65, 162, 77), 'p_font': 'rgb(217, 210, 192)', 's_font': 'rgb(0, 0, 0)'}
}


# Add some text on the image
def text_adder(img, text, fill, coords, font_size=20):
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(general_font, font_size)
    draw.text(coords, text, fill=fill, font=font)
    return img


# Set the profile picture on the image
def set_profile_picture(img, url, border):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle(((border + 20, border + 20), (h - border - 20, h - border - 20)), fill=(0,0,0))

    response = requests.get(url)

    picture = Image.open(BytesIO(response.content))

    picture = picture.resize((h - 4 * border - 4, h - 4 * border - 4))
    img.paste(picture, (border * 2 + 2, border * 2 + 2))

    return img


# The progress bar of the problem solved
def set_progress_bar(img, solved, total, border, height=40):
    w, h = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle(((h - border, h - 2 * border - height), (w - 2 * border, h - 2 * border)), fill=(50, 50, 50), outline=(0, 0, 0), width=4)

    draw.rectangle(((h - border + 5, h - 2 * border - height + 5), ((h - border - 5) + solved / total * (w - 2 * border - 5 - (h - border - 5)), h - 2 * border - 5)), fill=(150, 100, 50))
    return img


# Add the rectangles covering the area allowing to darken the image
def add_center_fill(img, border=10):
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle(((border, border), (w - border, h - border)), fill=(255, 255, 255, 60))
    return img


# The main function used to create the profile picture images
def generate_profile_image(username, solved_by, total_problems, rank_in_discord, total_in_discord, recent_solves, discord_picture_url):

    percentage = round(solved_by / total_problems * 100)
    general_border = 20

    image = Image.open('images_elements/background.jpg')
    w, h = image.size

    image = add_center_fill(image, general_border)

    image = set_profile_picture(image, discord_picture_url, general_border)
    image = set_progress_bar(image, solved_by, total_problems, general_border)

    image = text_adder(image, username, (220, 220, 220), (h, general_border * 2 + 10), 30)
    image = text_adder(image, "SOLVED PROBLEMS: {0}/{1} ({2}%)".format(solved_by, total_problems, percentage),
                       (220, 220, 220), (h, general_border * 2 + 60), 20)
    image = text_adder(image, "LEVEL: {0}".format(int(solved_by / 25)), (220, 220, 220), (h, general_border * 2 + 85),
                       20)

    image = text_adder(image, "RANK IN DISCORD: {0}/{1}".format(rank_in_discord, total_in_discord), (220, 220, 220),
                       (h + w / 3 + 40, general_border * 2 + 60), 20)
    if recent_solves < 10:
        recent_text = f"SOLVES IN THE 10 RECENT: {recent_solves}"
    else:
        recent_text = f"RUN OF RECENT PROBLEMS: {recent_solves}"
    image = text_adder(image, recent_text, (220, 220, 220),
                        (h + w / 3 + 40, general_border * 2 + 85), 20)


    image.save("images_saves/{0}.png".format(username))
    return "images_saves/{0}.png".format(username)


def add_box_user_solve(problem: int, fill: bool, img: Image, fill_color: Optional[Tuple[int, int, int]] = None) -> None:

    width_pos = 1
    height_pos = 1

    border = 10

    while problem > 300:
        problem -= 300
        height_pos += 10
    
    while problem > 100:
        problem -= 100
        width_pos += 10

    while problem > 10:
        problem -= 10
        height_pos += 1

    while problem > 1:
        problem -= 1
        width_pos += 1

    w = height_pos * 10 + (((height_pos - 1) // 10)) * 10
    h = width_pos * 10 + (((width_pos - 1) // 10)) * 10

    draw = ImageDraw.Draw(img, "RGBA")

    if not fill:
        filler = (0, 0, 0)
    elif fill_color is None:
        filler = (220, 220, 220)
    else:
        filler = fill_color
        
    # print(filler, problem)
    
    outliner_color = 255
    outliner = (outliner_color, outliner_color, outliner_color)

    draw.rectangle(((h + border, w + border), (h + border + 10, w + border + 10)), fill=filler, outline=outliner, width=1)


def add_day_timestamp(image, data: list, timestamp: float, frame: int, total_frame: int, dimensions: tuple):

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle(((390, 370), (580, 390)), outline=(255, 255, 255), fill=(0, 0, 0), width=1)

    splits = 24
    cp = [(46, 127, 24), (200, 37, 56)][::-1] # color palette

    minimal_date = datetime.datetime(1990, 1, 1, 0, 0, 0)

    heat_map = [0 for _ in range(splits)]
    
    solves_at_this_point = list(filter(lambda element: minimal_date.timestamp() < element[1].timestamp() < timestamp, data))
    timestamps = list(map(lambda element: element[1], solves_at_this_point))
    
    for t in timestamps:
        heat_map[t.hour] += 1

    draw = ImageDraw.Draw(image, "RGBA")
    h = heat_map
    for i in range(splits):
        p = max(max(heat_map), 1)
        c = (cp[0][0] * h[i]/p + cp[1][0] * (1 - h[i]/p), cp[0][1] * h[i]/p + cp[1][1] * (1 - h[i]/p), cp[0][2] * h[i]/p + cp[1][2] * (1 - h[i]/p))
        c = (int(c[0]), int(c[1]), int(c[2]))
        draw.rectangle(((391 + i/splits * (579 - 391), 371), (391 + (i+1)/splits * (579 - 391), 389)), c)
        
    text_adder(image, "Solves per hour of the day (UTC)", (255, 255, 255), (390, 348), 12)


def add_max_solve(image, data: list, timestamp: float, frame: int, total_frame: int):

    best = 0
    day_duration = 86400

    queue = deque()

    minimal_date = datetime.datetime(1980, 1, 1, 0, 0, 0)

    for element in data: 
        d = element[1]
        if (d - minimal_date).total_seconds() < 1000:
            continue
        if d.timestamp() > timestamp:
            break
        queue.append(d)
        while d.timestamp() - queue[0].timestamp() > day_duration:
            queue.popleft()
        if len(queue) > best:
            best = len(queue)

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle(((390, 310), (580, 330)), outline=(255, 255, 255), fill=(0, 0, 0), width=1)

    text_adder(image, str(best), (255, 255, 255), (480, 312), 12)
    text_adder(image, "Max solves in a 24H range", (255, 255, 255), (390, 290), 12)


def add_min_and_max_solve_difference(image, data: List[List], timestamp: float, frame: int, total_frame: int) -> None:

    to_keep_solves = list(filter(lambda element: element[1].timestamp() < timestamp, data))

    min_difference = 10000000000000
    max_difference = 0

    for index in range(len(to_keep_solves) - 1):


        timestamp_before = to_keep_solves[index][1].timestamp()
        timestamp_after = to_keep_solves[index + 1][1].timestamp()

        minimal_date = datetime.datetime(1985, 1, 1, 0, 0, 0)
        if timestamp_before < minimal_date.timestamp():
            continue

        difference = timestamp_after - timestamp_before

        min_difference = min(min_difference, difference)
        max_difference = max(max_difference, difference)

    def format_date(d: datetime.timedelta) -> str:
        if d.days > 1:
            return f"{d.days} days"
        if d.seconds // 3600 >= 1:
            return f"{d.seconds // 3600} hours"
        return f"{d.seconds // 60} minutes"

    if len(to_keep_solves) <= 1:
        min_difference = 0
        max_difference = 0

    min_time_diff = datetime.timedelta(seconds=min_difference)
    max_time_diff = datetime.timedelta(seconds=max_difference)

    difference_text = format_date(min_time_diff) + " / " + format_date(max_time_diff)

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle(((390, 190), (580, 210)), outline=(255, 255, 255), fill=(0, 0, 0), width=1)

    text_adder(image, difference_text, (255, 255, 255), (430, 192), 12)
    text_adder(image, "Min / Max time between 2 solves", (255, 255, 255), (390, 170), 12)


def add_solve_count(image, solves_at_this_point: set):

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle(((390, 250), (580, 270)), outline=(255, 255, 255), fill=(0, 0, 0), width=1)

    text_adder(image, str(len(solves_at_this_point)), (255, 255, 255), (480, 252), 12)
    text_adder(image, "Solves", (255, 255, 255), (390, 230), 12)


def add_watermark(image):
    w, h = image.width, image.height
    text_adder(image, "Project Euler Discord Community", (255, 255, 255), (390 + 5, h - 35), 10)
    text_adder(image, "discord.gg/huGnueastb", (255, 255, 255), (390 + 5, h - 50), 15)



def image_for_timestamp_user_solve(data: list, timestamp: float, username: str, frame: int, total_frame: int, frame_to_write: int, last_pb: int):

    dimensions = (600, 470)
    
    solves_at_this_point = list(filter(lambda element: element[1].timestamp() < timestamp, data))
    solves_at_this_point = list(map(lambda element: element[0], solves_at_this_point))
    solves_at_this_point = set(solves_at_this_point)
    
    image = Image.new('RGB', dimensions)
    draw = ImageDraw.Draw(image, "RGB")
    draw.rectangle(((0, 0), dimensions), (0, 0, 0))

    for i in range(1, last_pb + 1):
        add_box_user_solve(i, i in solves_at_this_point, image)

    draw.rectangle(((3*100 + 6*10, 20), (3*100 + 6*10 + 20, dimensions[1] - 20)))

    text_adder(image, "Time", (255, 255, 255), (390, 20), 15)
    draw.rectangle(((360+1, 20+1), (380-1, 20 + (dimensions[1] - 40) * (max(frame, 1)) / total_frame - 1)), (170, 170, 170))

    current_date = datetime.datetime.fromtimestamp(timestamp)
    text_adder(image, datetime.datetime.strftime(current_date, "%Y-%m-%d"), (255, 255, 255), (390, 40), 13)

    add_day_timestamp(image, data, timestamp, frame, total_frame, dimensions)
    add_watermark(image)
    add_max_solve(image, data, timestamp, frame, total_frame)
    add_solve_count(image, solves_at_this_point)
    add_min_and_max_solve_difference(image, data, timestamp, frame, total_frame)

    text_adder(image, username, (255, 255, 255), (390, 70), 25)
    text_adder(image, "Frame {0}".format(len(os.listdir(f"graphs/{username}/"))), (255, 255, 255), (390, 100), 10)

    image_path = f"graphs/{username}/frame{frame_to_write}.png"
    image.save(image_path)

    return image_path


def concatenate_image_gif(username: str):

    images = glob.glob(f"graphs/{username}/*.png")
    images = sorted(images, key=lambda x: int(x.split("frame")[1].split(".")[0]))
    
    save_path = f"graphs/{username}/{username}.gif"

    gif = []

    for image in images:
        img = Image.open(image)
        gif.append(img.convert("P", palette=Image.ADAPTIVE))

    gif[0].save(save_path, save_all=True, optimize=False, append_images=gif[1:], disposal=2, loop=0, transparency=True)



def project_euler_grid(cells_to_fill: List[Tuple[int, Tuple[int, int, int]]], last_problem) -> str:

    """
    A list of cells to fill, with the associated color
    """

    dimensions = (360, 470)

    img = Image.new("RGB", dimensions)
    draw = ImageDraw.Draw(img, "RGB")
    draw.rectangle(((0, 0), dimensions), (0, 0, 0))

    fill_option = [False for i in range(last_problem + 1)]
    color_option = [None for i in range(last_problem + 1)]
    
    for cell_index, cell_color in cells_to_fill:
        fill_option[cell_index] = True
        color_option[cell_index] = cell_color

    for problem in range(1, last_problem + 1):
        add_box_user_solve(problem, fill_option[problem], img, color_option[problem])

    path = "images_saves/temp/"
    sz = len(os.listdir(path))
    path = path + f"temp{sz}.png"

    img.save(path)
    return path



if __name__ == '__main__':
    project_euler_grid([15, 100])