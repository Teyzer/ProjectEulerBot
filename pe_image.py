from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import requests


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


if __name__ == '__main__':
    pass