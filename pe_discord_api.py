import asyncio
import time

import datetime
import pytz

from math import *
import json

import dbqueries
import pe_api
import pe_image
import interactions_discord as inters

import discord
from discord import option

TEST_SERVER = 943488228084813864
PROJECT_EULER_SERVER = 903915097804652595
GUILD_IDS = [PROJECT_EULER_SERVER]

# Initial condition
STARTING_TIME = datetime.datetime.now(pytz.utc)

# In order to keep track of the last time the solves of members were checked
LAST_CHECK_SUCCESS = False
LAST_CHECK_TIME = datetime.datetime.now(pytz.utc)
REPEATS_SINCE_START = 0
REPEATS_SUCCESSFUL_SINCE_START = 0

# Basic Discord stuff
intents = discord.Intents.all()
bot = discord.Bot(guild_ids=GUILD_IDS, intents=intents)

# Time between each check of solves, in seconds
AWAIT_TIME = 60

# Previously, the prefix that was used to make commands
PREFIX = "&"

# The IDs of the channels in which solves and achievements are announced
CHANNELS_TO_ANNOUNCE = [944372979809255483, 1002176082713256028]
SPECIAL_CHANNELS_TO_ANNOUNCE = [944372979809255483, 1004530709760847993]

# Constants for text
GREEN_CIRCLE = "🟢"
ORANGE_CIRCLE = "🟠"
RED_CIRCLE = "🔴"


@bot.event
async def on_ready():

    # Global variables in order to modify them
    global LAST_CHECK_SUCCESS
    global LAST_CHECK_TIME
    global REPEATS_SINCE_START
    global REPEATS_SUCCESSFUL_SINCE_START

    # For debugging
    print('Login made as {0.user}'.format(bot))
    
    # The 'Is playing {}' presence
    await bot.change_presence(activity=discord.Game(name="{0} Restarting...".format(ORANGE_CIRCLE)))

    while True:

        # Async sleep
        await asyncio.sleep(AWAIT_TIME)

        # In the console
        print(REPEATS_SINCE_START, end="| ")
        
        # Getting the data recquired
        solves = pe_api.keep_session_alive()
        REPEATS_SINCE_START += 1

        # Solve is None means that the data was not retrieved correctly
        if solves is None:
            
            if LAST_CHECK_SUCCESS == True:
                LAST_CHECK_SUCCESS = False
                await bot.change_presence(activity=discord.Game(name="{0} /status for details".format(RED_CIRCLE)))
            continue

        else:

            if LAST_CHECK_SUCCESS == False:
                LAST_CHECK_SUCCESS = True
                await bot.change_presence(activity=discord.Game(name="{0} /link to use me".format(GREEN_CIRCLE)))
            # We save this moment as the last correct retrieve
            LAST_CHECK_TIME = datetime.datetime.now(pytz.utc)
            REPEATS_SUCCESSFUL_SINCE_START += 1

        # No solve, so nothing to do
        if len(solves) == 0:
            continue

        for solve in solves:
            for problem in solve[1]:

                # Need to know the position of the solver, this may be optimized in the future, because already retrieved in 'keep_session_alive()'
                data_on_problem = pe_api.problem_def(problem)

                for channel_id in CHANNELS_TO_ANNOUNCE:
                    channel = bot.get_channel(channel_id)
                    if solve[2] == "":
                        sending_message = "`{0}` solved the problem #{1}: '{2}' which has been solved by {3} people, well done! <https://projecteuler.net/problem={1}>"
                        sending_message = sending_message.format(solve[0], data_on_problem[0], data_on_problem[1], data_on_problem[3])
                    else:
                        sending_message = "`{0}` (<@{4}>) solved the problem #{1}: '{2}' which has been solved by {3} people, well done! <https://projecteuler.net/problem={1}>"
                        sending_message = sending_message.format(solve[0], data_on_problem[0], data_on_problem[1], data_on_problem[3], solve[2])
                    await channel.send(sending_message)

            # If the member got a new level
            # May need to be corrected, as a double solve in a minute may lead the bot to forget a level
            if int(solve[3]) % 25 == 0:
                for channel_id in SPECIAL_CHANNELS_TO_ANNOUNCE:
                    channel = bot.get_channel(channel_id)
                    if solve[2] == "":
                        sending_message = "`{0}` has just reached level {1}, congratulations!"
                        sending_message = sending_message.format(solve[0], int(solve[3]) // 25)
                    else:
                        sending_message = "`{0}` (<@{2}>) has just reached level {1}, congratulations!"
                        sending_message = sending_message.format(solve[0], int(solve[3]) // 25, solve[2])
                    await channel.send(sending_message)

        # Get the list of users to check for awards (this is the only time we check forum awards)
        solvers = list(set([solve[0] for solve in solves]))

        # Get the complete list of awards, and then format the array
        awards = pe_api.get_awards_specs()
        awards = awards[0] + awards[1]

        # Checking the awards of each solver
        for solver in solvers:

            # Retrieving data on them, it automatically compute the new awards
            awards_user = pe_api.update_awards(solver)
            
            # If there is at least one new award
            if len(awards_user[1]) != 0:

                # Announcing the new awards
                for award in [awards[k] for k in awards_user[1]]:
                    for channel_id in SPECIAL_CHANNELS_TO_ANNOUNCE:
                        channel = bot.get_channel(channel_id)
                        await channel.send("`{0}` got the award '{1}', congratulations!".format(solver, award))



""" 
COMMANDS 
"""

@bot.slash_command(name="update", description="Update the known friend list of the bot")
async def command_hello(ctx):
    await ctx.defer()
    if pe_api.keep_session_alive() is None:
        await ctx.respond("An error occured during the fetch, this may need human checkup. Use /status to get more details.")
    else:
        await ctx.respond("The data was updated!")


@bot.slash_command(name="status", description="Give the current status of the bot, concerning recently fetched data")
async def command_status(ctx):
    
    text_response = "The last fetch of data was `{0}`. The last successful fetch was made on `{1}`.\n"
    text_response += "Since the last restart of the bot (`{4}`), there was `{2}` successful request, over `{3}` in total."

    fetched_data_status = "successful" if LAST_CHECK_SUCCESS else "unsuccessful"
    fetched_data_time_status = LAST_CHECK_TIME.strftime("%Y-%m-%d at %H:%M:%S UTC")
    fetch_starting_time = STARTING_TIME.strftime("%Y-%m-%d at %H:%M:%S UTC")

    text_response = text_response.format(fetched_data_status, fetched_data_time_status, str(REPEATS_SINCE_START), str(REPEATS_SUCCESSFUL_SINCE_START), fetch_starting_time)

    await ctx.respond(text_response)


@bot.slash_command(name="profile", description="Render your project euler profile in a cool image")
@option("member", description="Mention the member you want the profile to be displayed", default=None)
async def command_profile(ctx, member: discord.User):

    await ctx.defer()

    if member is not None:
        profile_url = member.avatar.url
        discord_id = member.id
    else:
        profile_url = ctx.author.avatar.url
        discord_id = ctx.author.id

    print(profile_url, discord_id)

    connection = dbqueries.open_con()
    temp_query = "SELECT * FROM members WHERE discord_id = '{0}'".format(discord_id)
    data = dbqueries.query(temp_query, connection)

    if len(data.keys()) == 0:
        dbqueries.close_con(connection)
        return await ctx.respond("This user is not linked! Please link your account first")

    data = data[0]

    all_data = dbqueries.query("SELECT * FROM members ORDER BY solved DESC;", connection)
    total = len(all_data.keys())
    rank = total

    for k in all_data.keys():
        if str(all_data[k]["discord_id"]) == str(discord_id):
            rank = k+1

    return await ctx.respond(file = discord.File(pe_image.generate_profile_image(data["username"], data["solved"], len(data["solve_list"]), rank, total, sum(int(x) for x in data["solve_list"][-10:]), profile_url)))


@bot.slash_command(name="link", description="Link your project euler account and your discord account")
@option("username", description="Your Project Euler username account (not nickname)")
async def command_link(ctx, username: str):

    await ctx.defer()

    discord_user_id = ctx.author.id
    database_discord_user = dbqueries.single_req("SELECT * FROM members WHERE discord_id = '{0}'".format(discord_user_id))
    if len(database_discord_user.keys()) != 0:
        sentence = "Your discord account is already linked to the account `{0}`, type /unlink to unlink it".format(database_discord_user[0]["username"])
        return await ctx.respond(sentence)

    user = dbqueries.single_req("SELECT * FROM members WHERE username = '{0}'".format(username))
    if len(user.keys()) == 0:
        return await ctx.respond("This username is not in my friend list. Add the bot account on project euler first: 1910895_2C6CP6OuYKOwNlTdL8A5fXZ0p5Y41CZc\nIf you think this is a mistake, type /update")

    user = user[0]
    if str(user["discord_id"]) != "":
        return await ctx.respond("This account is already linked to <@{0}>".format(user["discord_id"]))

    temp_query = "UPDATE members SET discord_id = '{0}' WHERE username = '{1}'".format(discord_user_id, username)
    dbqueries.single_req(temp_query)

    return await ctx.respond("Your account was linked to `{0}`!".format(username))


@bot.slash_command(name="unlink", description="Unlink your Project Euler account with your discord account")
async def command_unlink(ctx):

    await ctx.defer()

    discord_user_id = ctx.author.id
    database_discord_user = dbqueries.single_req("SELECT * FROM members WHERE discord_id = '{0}'".format(discord_user_id))

    if len(database_discord_user.keys()) == 0:
        return await ctx.respond("Your discord account isn't linked to any profile")

    temp_query = "UPDATE members SET discord_id = '' WHERE discord_id = '{0}'".format(discord_user_id)
    dbqueries.single_req(temp_query)

    return await ctx.respond("Your discord account was unlinked to the project euler `{0}` account".format(database_discord_user[0]["username"]))


@bot.slash_command(name="kudos", description="Display the kudos progression of your posts on the forum")
@option("member", description="Mention the member you want the kudos to be displayed", default=None)
async def command_kudos(ctx, member: discord.User):

    discord_id = ctx.author.id
    if member is not None:
        discord_id = member.id

    connection = dbqueries.open_con()
    if not pe_api.is_discord_linked(discord_id, connection):
        dbqueries.close_con(connection)
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")

    username = dbqueries.query("SELECT username FROM members WHERE discord_id='{0}';".format(discord_id), connection)[0]["username"]
    dbqueries.close_con(connection)

    kudos, change, changes = pe_api.update_kudos(username)
    if change == 0:
        return await ctx.respond("No change for user `{0}`, still {1} kudos (this is normal if this is your first time using the command since there was no previous data)".format(username, kudos))
    else:
        k = "```" + "\n".join(list(map(lambda x: ": ".join(list(map(str, x))), changes))) + "```"
        return await ctx.respond("There was some change for user `{0}`! You gained {1} kudos on the following posts (for a total of {2} kudos):".format(username, change, kudos) + k)


@bot.slash_command(name="easiest", description="Find the easiest problems you haven't solved yet")
@option("member", description="The member you want you want to see the next possible solves", default=None)
@option("method", description="The method used", choices=["By number of solves", "By order of publication", "By ratio of solves per time unit"], default="By ratio of solves per time unit")
@option("display_nb", description="The number of problems you want to be displayed", min_value=1, max_value=25, default=10)
async def command_easiest(ctx, member: discord.User, method: str, display_nb: int):
    
    discord_id = ctx.author.id
    if member is not None:
        discord_id = member.id

    print(discord_id)

    connection = dbqueries.open_con()
    if not pe_api.is_discord_linked(discord_id, connection):
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")

    username = dbqueries.query("SELECT username FROM members WHERE discord_id='{0}';".format(discord_id), connection)[0]["username"]
    dbqueries.close_con(connection)

    list_problems = pe_api.unsolved_problems(username)

    if method == "By number of solves":
        problems = sorted(list_problems, key=lambda x: int(x[3]), reverse=True)
    elif method == "By order of publication":
        problems = sorted(list_problems, key=lambda x: int(x[0]))
    elif method == "By ratio of solves per time unit":
        problems = sorted(list_problems, key=lambda x: int(x[3])/(int(time.time()) + 31536000 - int(x[2])), reverse=True)

    problems = problems[:display_nb]

    lst = "```" + "\n".join(list(map(lambda x: "Problem #{0}: '{1}' solved by {2} members".format(x[0], x[1], x[3]), problems))) + "```"
    return await ctx.respond("Here are the {1} easiest problems available to `{0}`:".format(username, display_nb) + lst)


@bot.slash_command(name="roles-languages", description="Select the languages roles you want to be displayed on your profile")
async def command_roles_languages(ctx):

    view = inters.DropdownView(bot, ctx.author)

    # Sending a message containing our View
    await ctx.respond("Choose your main languages (by alphabetic order):", view=view, ephemeral=True)


@bot.event
async def on_message(message):

    if message.author == bot.user:
        return

    if message.content.startswith(PREFIX):
        await message.channel.send("The & command is not supported anymore please use the slash commands with /")