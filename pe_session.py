import traceback

from requests import TooManyRedirects
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC

from anticaptchaofficial.imagecaptcha import *

from PIL import Image
import json

import pe_api
import phone_api


MAX_TRIES = 3


def get_captcha(driver, element, path):
    
    location = element.location
    size = element.size
    driver.save_screenshot(path)

    image = Image.open(path)

    left = location['x']
    top = location['y']
    right = location['x'] + size['width']
    bottom = location['y'] + size['height']

    image = image.crop((left, top, right, bottom))
    image.save(path)

def solve(image_name: str, human: bool = False):
    
    if human:
        return input("Human CAPTCHA: ")
    
    solver = imagecaptcha()
    solver.set_key("AAAA")
    captcha_text = solver.solve_and_return_solution(image_name)

    phone_api.bot_info("Consumed a CAPTCHA token")
    
    return str(captcha_text)


def try_fetching_cookies(human: bool = False):

    url = "https://projecteuler.net/sign_in"
    filename = "web_utils/current-captcha.png"

    # GET THE CAPTCHA

    service = Service(executable_path='/usr/local/bin/geckodriver')

    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")

    driver = webdriver.Firefox(service=service, options=options)
    driver.set_window_size(1080, 720)

    driver.get(url)

    WebDriverWait(driver, 2)

    captcha = driver.find_element(By.ID,"captcha_image")
    get_captcha(driver, captcha, filename)

    captcha_result = solve(filename, human)

    # FILL THE FORM

    driver.find_element("xpath", 
        "//input[@id='username' and @name='username']"
    ).send_keys("EulerCommunity")

    driver.find_element("xpath", 
        "//input[@id='password' and @name='password']"
    ).send_keys("IncredibleBoy")

    driver.find_element("xpath", 
        "//input[@id='captcha' and @name='captcha']"
    ).send_keys(captcha_result)

    driver.find_element("xpath", 
        "//input[@id='remember_me' and @name='remember_me']"
    ).click()

    driver.find_element("xpath", 
        "//input[@name='sign_in' and @type='submit']"
    ).click()   

    cookies = driver.get_cookies()

    driver.quit()
    return cookies


def refresh_tokens():

    human = False

    current_tries = 0
    found_keepalive = False

    values = {"PHPSESSID": None, "keep_alive": None} # [PHPSESSID, keep_alive]

    while not found_keepalive and current_tries < MAX_TRIES:

        cookies = try_fetching_cookies(human)
        current_tries += 1

        print(current_tries)

        for cookie in cookies:

            if cookie["name"] == "PHPSESSID":
                values["PHPSESSID"] = cookie["value"]

            if cookie["name"] == "keep_alive":
                found_keepalive = True
                values["keep_alive"] = cookie["value"]
    
    if values["keep_alive"] is not None:
        phone_api.bot_info("Token refreshed automatically")
    else:
        phone_api.bot_crashed("Failed to refresh token")

    with open("keys.json", "r") as f:
        data = json.load(f)

    data["session_keys"] = values

    with open("keys.json", "w") as f:
        json.dump(data, f, indent=4)

    return values




def is_connected() -> bool:

    try:
        pe_request = pe_api.ProjectEulerRequest("https://projecteuler.net/archives", True)
    except TooManyRedirects as exc:
        pe_api.console.log(exc, traceback.format_exc())
        return False

    if pe_request.status != 200:
        return False

    return "Logged in as" in pe_request.response


def is_website_active() -> bool:
    pe_request = pe_api.ProjectEulerRequest("https://projecteuler.net/", False)
    return pe_request.status == 200



if __name__ == "__main__":

    print(is_connected())
    refresh_tokens()