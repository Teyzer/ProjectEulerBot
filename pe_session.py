import traceback

from requests import TooManyRedirects
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC

import faulthandler

from anticaptchaofficial.imagecaptcha import *

from PIL import Image
import json

import pe_api
import phone_api

from rich.console import Console
from pe_global_objects import log
import os


console = Console()

MAX_TRIES = 3
CAPTCHA_KEY = None
PROFILE_NAME = None
PE_PASSWORD = None

PHPSESS_NAME = "__Host-PHPSESSID"


def session_setup(captcha: str, profile: str, pe_password: str) -> None:

    global CAPTCHA_KEY, PROFILE_NAME, PE_PASSWORD
    CAPTCHA_KEY = captcha
    PROFILE_NAME = profile
    PE_PASSWORD = pe_password



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
    solver.set_key(CAPTCHA_KEY)
    solver.set_numeric(1)
    solver.set_minLength(5)
    solver.set_maxLength(5)
    captcha_text = solver.solve_and_return_solution(image_name)

    phone_api.bot_info("Consumed a CAPTCHA token")
    
    return str(captcha_text)


def try_fetching_cookies(human: bool = False):

    url = "https://projecteuler.net/sign_in"
    filename = "web_utils/current-captcha.png"
    pre_form_filename = "web_utils/form.png"
    post_form_filename = "web_utils/postform.png"

    bot_password = PE_PASSWORD or os.environ.get("BOT_KEY")
    if not bot_password:
        log.error("Missing Project Euler password, cannot fetch cookies.")
        return []

    if 'web_utils' not in os.listdir('.'):
        os.mkdir('web_utils')

    service = Service(executable_path='/usr/local/bin/geckodriver')
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")

    driver = None
    try:
        driver = webdriver.Firefox(service=service, options=options)
        
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        driver.set_window_size(1080, 720)

        driver.get(url)
        
        captcha = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "captcha_image"))
        )
        get_captcha(driver, captcha, filename)

        captcha_result = solve(filename, human)
        log.info(f"[-] Tried to guess {captcha_result} as Captcha")

        driver.find_element("xpath", 
            "//input[@id='username' and @name='username']"
        ).send_keys("EulerCommunity")

        driver.find_element("xpath", 
            "//input[@id='password' and @name='password']"
        ).send_keys(bot_password)

        driver.find_element("xpath", 
            "//input[@id='captcha' and @name='captcha']"
        ).send_keys(captcha_result)

        driver.find_element("xpath", 
            "//input[@id='remember_me' and @name='remember_me']"
        ).click()

        driver.save_screenshot(pre_form_filename)

        driver.find_element("xpath", 
            "//input[@name='sign_in' and @type='submit']"
        ).click()   

        driver.save_screenshot(post_form_filename)

        cookies = driver.get_cookies()
        return cookies

    except Exception as e:
        # logging.error(f"[!] Error during browser automation: {e}")
        # traceback.print_exc()
        log.exception(e)
        return []
    
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                log.exception(e)
                # console.log(f"[!] Error closing driver: {e}")


def refresh_tokens():

    faulthandler.enable()

    human = False

    current_tries = 0
    found_keepalive = False

    values = {PHPSESS_NAME: None, "keep_alive": None} # [PHPSESSID, keep_alive]

    while not found_keepalive and current_tries < MAX_TRIES:

        cookies = try_fetching_cookies(human)
        current_tries += 1

        log.info(f"Making try #{current_tries} to refresh cookies")

        for cookie in cookies:

            log.info(f'{cookie["name"]}, {cookie["value"]}')
            if cookie["name"] == PHPSESS_NAME:
                values[PHPSESS_NAME] = cookie["value"]

            if cookie["name"] == "keep_alive":
                found_keepalive = True
                values["keep_alive"] = cookie["value"]
    
    if values["keep_alive"] is not None:
        phone_api.bot_info("Token refreshed automatically")
        log.info(f"Token refreshed automatically {values[PHPSESS_NAME]}")
    else:
        phone_api.bot_crashed("Failed to refresh token")
        log.error("Failed to refresh token")

    with open(PROFILE_NAME, "r") as f:
        data = json.load(f)

    data["session_keys"] = values

    with open(PROFILE_NAME, "w") as f:
        json.dump(data, f, indent=4)

    pe_api.COOKIES = values
    return values




def is_connected() -> bool:

    try:
        pe_request = pe_api.ProjectEulerRequest("https://projecteuler.net/archives", True)
    except TooManyRedirects as exc:
        pe_api.console.log(exc, traceback.format_exc())
        log.exception(exc)
        return False
    except pe_api.EulerRequestFail:
        return False

    if pe_request.status != 200:
        return False

    return "Logged in as" in pe_request.response


def is_website_active() -> bool:
    try:
        pe_request = pe_api.ProjectEulerRequest("https://projecteuler.net/", False)
    except pe_api.EulerRequestFail as _:
        return False
    return pe_request.status == 200



if __name__ == "__main__":

    profile_name = "profiles/authentic.json"
    with open(profile_name, "r") as f:
        data = json.load(f)
        session_setup(data["captcha_key"], profile_name, data["pe_account"]["password"])
        
    print(is_connected())
    print(refresh_tokens())