# Project Euler Discord Bot

This project contains a package of functions used to communicate with the [Project Euler website](https://projecteuler.net) and the discord API to provide numerous functions for the members of the [Project Euler Discord](https://discord.gg/28bQcA7pQQ).

The desired outcome is to make project euler members life easier, with commands such as `&easiest` that will return a list of the 10 most solved problem by the community that the member didn't solve.

Also, one cool feature of the bot is its capacity to constantly seek for new problems solved by the members of the discord. Each minute, it sends a request to the Project Euler website, and with previously saved data in a database, compare everything to see if any member has solved a new problem. With this, the bot announce will announce every problem solved, awards, levels-up...

## Features

This is the list of commands you can use in the Discord of the community.

- `&profile` : shows a nice image summing up your Project Euler Profile
- `&link` : Link your Discord profile with your Project Euler one.
- `&unlink` : Unlink your Discord profile
- `&kudos` : Create a list of all the kudos you got the first time used, and then check if you got any new ones every new time the command is used.
- `&help` : Shows an honestly not-worked at all list of commands
- `&update` : Update the database that lists the friends of the bot on Project Euler
- `&easiest` : Shows a list of the 10 easiest problem for the member

Note that the command `&link` requires you to add the Project Euler Bot as a friend on the website itself, here is its friend key: `1910895_2C6CP6OuYKOwNlTdL8A5fXZ0p5Y41CZc`

# Technology

The main technology used by the scripts is the Project Euler API, which is always of the form `https://projecteuler.net/minimal=...`. Sadly, some data cannot be obtained this way, like the awards of each number (the number of awards can be obtained, but not the exact list showing which ones), kudos, and a lot more. When the minimal API does not cover the data required, I mostly use web scrapping with packages such as `requests` (which is obviously also used for the minimal API), and `beautifulsoup4`. For the database part, I use `pymysl`.

Each file has a special role, which is well explained by their name. `dbqueries.py` contains the database stuff, `pe_api.py` contains the web scrapping and minimal API contact, and so on. Note that `pe` in the name of the files stands for "Project Euler".
