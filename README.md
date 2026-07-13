# Project Euler Discord Bot

This project contains a package of functions used to communicate with the [Project Euler website](https://projecteuler.net) and the discord API to provide numerous functions for the members of the [Project Euler Discord](https://discord.gg/huGnueastb).

The bot is used to display statistics, and to send messages to desired channels each time a member of the discord solves a problem. 

The bot has been used a total of `75,000` times so far.

## Features

Here is a non-exhaustive list of commands you can use if you join the discord:

- `/profile` : shows a nice image summing up your Project Euler Profile
- `/link` : Link your Discord profile with your Project Euler one.
- `/unlink` : Unlink your Discord profile
- `/kudos` : Create a list of all the kudos you got the first time used, and then check if you got any new ones every new time the command is used.
- `/help` : Shows an honestly not-worked at all list of commands
- `/update` : Update the database that lists the friends of the bot on Project Euler
- `/easiest` : Shows a list of the 10 easiest problem for the member

Note that the command `/link` requires you to add the Project Euler Bot as a friend on the website itself, here is its friend key: `1910895_2C6CP6OuYKOwNlTdL8A5fXZ0p5Y41CZc`

# How does it work.

## Technologies, and principles.

The bot works with the `pycord` package, which is a fork of the classic `discord` package. The bot keeps a complete copy of: the solves (not including timestamps), the awards, the kudos (if the member triggers the associated command). Everything is stored inside a `sqlite3` database (communication with `pe_databases.py`).

Everything is heavily object oriented, and the main objects are inside `pe_api.py`. Currently, the main ones are `Problem` and `Member`, and there are a few other ones. 

The entire project is becoming asynchronous, that is, almost every method that either communicates (or has a probability to communicate) with Project Euler or with Discord will be asynchronous. 

## The two important processes

The launchpoint is at `eulerbot.py`. Here, two things are launched: the communication with discord and a loop that triggers every 60 seconds. Almost every function is asynchronous in order not to block the communication with Discord.

The discord communication takes care of the slash commands, and the loop takes care of announcing the solves, the awards, and so on. 

# If you want to contribute

## Installation

First of all, I think it's important for you to be a member of the Discord, so be sure that you've joined, and feel free to ask me any question there (@pacome.f).

You can start by cloning the repo wherever you want. Then, create a python virtual environment, with `python3 -m venv .venv`, and install the required packages with `pip install -r requirements.txt`. 

Then, to launch the script, you will need several things (most of which I can lend, just send me a DM):
- A Project Euler account. All of the friends of that account will be the people we check the solves of.
- A Discord Bot. 
- A Database. You can use `databases/test.db`, but check the date to be sure the date is not too old. That's to make sure that the tables inside are of the same format as the repository expects.

When you have all of that, you need to create a file `profiles/test.json` of the following format:

```json
{
    "discord_key": "...",
    "database_file": "test.db",
    "captcha_key": "",
    "pe_account": {
        "username": "",
        "password": ""
    },
    "session_keys": {
        "__Host-PHPSESSID": "...",
        "keep_alive": "..."
    },
    "announcement_channels": {
        "solve_channel": [
            ...,
            ...
        ],
        "award_channel": [
            ...,
            ...
        ],
        "thread_channel": ...,
        "small_channel": ...
    }
}
```

Discord key is the key of the discord bot. Leave database file as `test.db`. Leave captcha key empty, it should not be needed and requires an otherwise too complicated setup.

You can also leave the username and password of the pe_account empty, it is only required (with the captcha key), to automatically connect. We will bypass that in just a moment.

Session keys are what interest us the most. You'll need to go in your browser, connect to projecteuler.net with the account you chose, then open DevTools (F12), and go to Storage, then Cookies, then copy the two associated values in the correct field. This is for Firefox, but it shouldn't be too different for Chrome or others.

Then, you'll need to fill in appropriate channels, I can give you those, or if you want to make it yourself, select one server in which your discord bot has permissions, and put in the ID of that channel. You can have multiple channels for solve and awards. 

## Run

Then you should be able to run the bot with `python3 eulerbot.py test.json`. The script automatically goes to search for the profile (`test.json` here) in the `profiles` folder. 