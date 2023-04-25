from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests

import datetime

import glob


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
def generate_profile_image(username, solved_by, total_problems, rank_in_discord, total_in_discord, solves_in_last_ten, discord_picture_url):

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
    image = text_adder(image, "SOLVES IN THE 10 RECENT: {0}".format(solves_in_last_ten), (220, 220, 220),
                       (h + w / 3 + 40, general_border * 2 + 85), 20)

    image.save("images_saves/{0}.png".format(username))
    return "images_saves/{0}.png".format(username)


def add_box_user_solve(problem: int, fill: bool, img):

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

    img_color = 220 if fill else 0
    filler = (img_color, img_color, img_color)

    outliner_color = 255
    outliner = (outliner_color, outliner_color, outliner_color)

    draw.rectangle(((h + border, w + border), (h + border + 10, w + border + 10)), fill=filler, outline=outliner, width=1)


def add_day_timestamp(image, data: list, timestamp: float, frame: int, total_frame: int, dimensions: tuple):

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle(((390, 370), (580, 390)), outline=(255, 255, 255), fill=(0, 0, 0), width=1)

    splits = 24
    cp = [(46, 127, 24), (200, 37, 56)][::-1] # color palette

    heat_map = [0 for _ in range(splits)]
    
    solves_at_this_point = list(filter(lambda element: element[1].timestamp() < timestamp, data))
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

    for element in data:
        if element[1].timestamp() > timestamp:
            break
        current = len(list(filter(lambda el: el[1].timestamp() < timestamp and element[1].timestamp() > el[1].timestamp() and element[1].timestamp() - el[1].timestamp() < day_duration, data)))
        if current > best:
            best = current

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle(((390, 310), (580, 330)), outline=(255, 255, 255), fill=(0, 0, 0), width=1)

    text_adder(image, str(best), (255, 255, 255), (480, 312), 12)
    text_adder(image, "Max solves in a 24H range", (255, 255, 255), (390, 290), 12)


def add_solve_count(image, solves_at_this_point: set):

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle(((390, 250), (580, 270)), outline=(255, 255, 255), fill=(0, 0, 0), width=1)

    text_adder(image, str(len(solves_at_this_point)), (255, 255, 255), (480, 252), 12)
    text_adder(image, "Solves", (255, 255, 255), (390, 230), 12)


def add_watermark(image):
    w, h = image.width, image.height
    text_adder(image, "Project Euler Discord Community", (255, 255, 255), (390 + 5, h - 35), 10)
    text_adder(image, "discord.gg/huGnueastb", (255, 255, 255), (390 + 5, h - 50), 15)



def image_for_timestamp_user_solve(data: list, timestamp: float, username: str, frame: int, total_frame: int, last_pb: int):

    dimensions = (600, 470)
    
    solves_at_this_point = list(filter(lambda element: element[1].timestamp() < timestamp, data))
    solves_at_this_point = list(map(lambda element: element[0], solves_at_this_point))
    solves_at_this_point = set(solves_at_this_point)
    
    image = Image.new('RGB', dimensions)

    for i in range(1, last_pb + 1):
        add_box_user_solve(i, i in solves_at_this_point, image)

    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle(((3*100 + 6*10, 20), (3*100 + 6*10 + 20, dimensions[1] - 20)))

    text_adder(image, "Time", (255, 255, 255), (390, 20), 15)
    draw.rectangle(((360+1, 20+1), (380-1, 20 + (dimensions[1] - 40) * frame / total_frame - 1)), (170, 170, 170))

    current_date = datetime.datetime.fromtimestamp(timestamp)
    text_adder(image, datetime.datetime.strftime(current_date, "%Y-%m-%d"), (255, 255, 255), (390, 40), 13)

    add_day_timestamp(image, data, timestamp, frame, total_frame, dimensions)
    add_watermark(image)
    add_max_solve(image, data, timestamp, frame, total_frame)
    add_solve_count(image, solves_at_this_point)

    text_adder(image, username, (255, 255, 255), (390, 70), 25)

    image_path = f"graphs/{username}/frame{frame}.png"
    image.save(image_path)

    return image_path


def concatenate_image_gif(username: str):

    images = glob.glob(f"graphs/{username}/*.png")
    images = sorted(images, key=lambda x: int(x.split("frame")[1].split(".")[0]))
    
    save_path = f"graphs/{username}/{username}.gif"

    gif = []
    for image in images:
        img = Image.open(image)
        gif.append(img.convert("P",palette=Image.ADAPTIVE))
    gif[0].save(save_path, save_all=True,optimize=False, append_images=gif[1:], loop=0)


if __name__ == '__main__':
    pass