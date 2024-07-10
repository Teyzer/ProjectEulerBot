import asyncio
import time

import datetime
import pytz

from math import *
import json

import dbqueries
import pe_api
import pe_image
import pe_plot
import pe_events
import re
import itertools

import requests

import interactions_discord as inters
import discord
from discord import option

import glob
import os
import random

from rich.console import Console
from rich import inspect


console = Console(record=True)

TEST_SERVER = 943488228084813864
PROJECT_EULER_SERVER = 903915097804652595
GUILD_IDS = [PROJECT_EULER_SERVER]

BOT_APPLICATION_ID = 930813331512635413

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
THREADS_CHANNEL = 904251551474942002

SOLVE_ROLES = [904255861503975465, 905987654083026955, 975720598741331988, 905987783892561931, 975722082996473877, 905987999949529098, 975722386559225878, 975722571473498142, 1051483511749619722]
PERFECTIONIST_ROLE = 1135697719319609384

# Constants for text
GREEN_CIRCLE = "🟢"
ORANGE_CIRCLE = "🟠"
RED_CIRCLE = "🔴"

FIRST_PLACE_EMOJI = "🥇"
SECOND_PLACE_EMOJI = "🥈"
THIRD_PLACE_EMOJI = "🥉"

AWARDING_SENTENCES = [
    "{0} is the first solver for problem #{1}: '{2}'! Congratulations! " + FIRST_PLACE_EMOJI,
    "{0} is the second solver for problem #{1}: '{2}'! Congratulations! " + SECOND_PLACE_EMOJI,
    "{0} is the third solver for problem #{1}: '{2}'! Congratulations! " + THIRD_PLACE_EMOJI,
    "{0} solved the problem #{1}: '{2}' which has been solved by {3} people, well done!"
]

THREAD_DEFAULT_NAME_FORMAT = "Problem #{0} discussion"

# Where solve = [Account, Array of solves, Discord ID, Level] as returned by pe_api.keep_session_alive(),
# returns a nicely formatted string for the user, including a discord @ if it exists.
def formatName(solve):
    if solve[2] != "":
        return "`{0}` (<@{1}>)".format(solve[0], solve[2])
    else:
        return "`{0}`".format(solve[0])

    

@bot.event
async def on_ready():

    # await u()

    # Global variables in order to modify them
    global LAST_CHECK_SUCCESS
    global LAST_CHECK_TIME
    global REPEATS_SINCE_START
    global REPEATS_SUCCESSFUL_SINCE_START


    # For debugging
    console.log(f'Login made as {bot.user}')
    
    # The 'Is playing {}' presence
    await bot.change_presence(activity=discord.Game(name="{0} Restarting...".format(ORANGE_CIRCLE)))

    while True:
        
        # Async sleep
        await asyncio.sleep(AWAIT_TIME)

        # In the console
        console.log(REPEATS_SINCE_START, end="| ")

        if REPEATS_SINCE_START % (3600 // AWAIT_TIME) == 0:
            console.log("Trying to update global stats... ", end="")
            global_update_output = pe_api.update_global_stats()
            console.log(global_update_output, end= " | ")
        
        # Getting the data recquired
        try:
            
            profiles = pe_api.update_process()
            
            if LAST_CHECK_SUCCESS == False:
                LAST_CHECK_SUCCESS = True
                await bot.change_presence(activity=discord.Game(name="{0} /link to use me".format(GREEN_CIRCLE)))
            
            # We save this moment as the last correct retrieve
            LAST_CHECK_TIME = datetime.datetime.now(pytz.utc)
            REPEATS_SUCCESSFUL_SINCE_START += 1
        
        except Exception:
            
            if LAST_CHECK_SUCCESS == True:
                LAST_CHECK_SUCCESS = False
                await bot.change_presence(activity = discord.Game(name="{0} /status for details".format(RED_CIRCLE)))
            continue
        
        REPEATS_SINCE_START += 1
        
        if len(profiles) == 0:
            continue
        
        event = pe_events.eventSoPE()
        
        problems: pe_api.PE_Problem = pe_api.PE_Problem.complete_list()
        awards_specs = pe_api.get_awards_specs()
        
        for profile in profiles:
            
            member: pe_api.Member = profile["member"]
            solves = profile["solves"]
            awards = profile["awards"]
            
            for problem_id in solves:
                
                problem: pe_api.PE_Problem = problems[problem_id - 1]
                pe_api.push_solve_to_database(member, problem)

                for channel_id in CHANNELS_TO_ANNOUNCE:
                    
                    channel = bot.get_channel(channel_id)
                    
                    #decide what message to send depending on how many solvers there are
                    if int(problem.solves) <= 3:
                        sending_message = AWARDING_SENTENCES[problem.solves - 1].format(member.username_ping(), problem.problem_id, problem.name)
                    else:
                        sending_message = AWARDING_SENTENCES[3].format(member.username_ping(), problem.problem_id, problem.name, problem.solves)
                        
                    # this is a temporary code to add stars
                    optional_stars = " 🌠" if not event.is_problem_solved(problem.problem_id) else ""
                    
                    sending_message = sending_message + optional_stars + " <https://projecteuler.net/problem={0}>".format(problem.problem_id)
                    await channel.send(sending_message, allowed_mentions = discord.AllowedMentions(users=False))
                
            if member.solve_count() % 25 == 0:
                
                if member.is_discord_linked():
                    await update_member_roles(member)
                
                for channel_id in SPECIAL_CHANNELS_TO_ANNOUNCE:
                    channel = bot.get_channel(channel_id)
                    sending_message = member.username_ping() + " has just reached level {0}, congratulations!"
                    sending_message = sending_message.format(member.solve_count() // 25)
                    await channel.send(sending_message, allowed_mentions = discord.AllowedMentions(users=False))

            if member.is_discord_linked() and member.solve_count() == len(member.solve_array()):
                await update_member_roles(member)

            if awards is None:
                continue

            for part in [0, 1]:
                for award in awards[part]:
                    for channel_id in SPECIAL_CHANNELS_TO_ANNOUNCE:
                        channel = bot.get_channel(channel_id)
                        award_name = awards_specs[part][award]
                        await channel.send(f"{member.username_ping()} got the award '{award_name}', congratulations!", 
                                           allowed_mentions = discord.AllowedMentions(users=False))
                
                
        pe_events.update_events(profiles)



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

    text_response = text_response.format(fetched_data_status, fetched_data_time_status, str(REPEATS_SUCCESSFUL_SINCE_START), str(REPEATS_SINCE_START), fetch_starting_time)

    await ctx.respond(text_response)


@bot.slash_command(name="profile", description="Render your project euler profile in a cool image")
@option("member", description="Mention the member you want the profile to be displayed", default=None)
async def command_profile(ctx, member: discord.User):

    await ctx.defer()

    if member is None:
        member = ctx.author

    discord_id = member.id
    profile_url = "https://cdn.discordapp.com/embed/avatars/{0}.png".format(int(member.discriminator) % 5)

    try:
        profile_url = member.avatar.url
    except:
        pass

    m = pe_api.Member(_discord_id = discord_id)

    if not m.is_discord_linked():
        return await ctx.respond("This user is not linked! Please link your account first")
    
    user_data = m.solve_array()
    rank_in_discord, people_in_discord = m.position_in_discord()

    file_path = pe_image.generate_profile_image(
        m.username(),
        m.solve_count(),
        len(m.solve_array()),
        rank_in_discord,
        people_in_discord,
        sum([1 if x else 0 for x in user_data[-10:]]),
        profile_url
    )

    return await ctx.respond(file = discord.File(file_path))


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

    m = pe_api.Member(_username = username)
    await update_member_roles(m)

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

    m = pe_api.Member(_discord_id = (ctx.author.id if member is None else member.id))

    if not m.is_discord_linked():
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")

    nkudos = m.get_new_kudos()
    m.push_kudo_to_database()
    
    kudo_count = m.kudo_count()
    
    change = sum([el[1] for el in nkudos])

    if change == 0:
        return await ctx.respond("No change for user `{0}`, still {1} kudos (Always displayed when first using the command)".format(m.username(), kudo_count))
    else:
        k = "```" + "\n".join(list(map(lambda x: ": ".join(list(map(str, x))), nkudos))) + "```"
        return await ctx.respond("There was some change for user `{0}`! You gained {1} kudos on the following posts (for a total of {2} kudos):".format(m.username(), change, kudo_count) + k)


@bot.slash_command(name="easiest", description="Find the easiest problems you haven't solved yet")
@option("member", description="The member you want you want to see the next possible solves", default=None)
@option("method", description="The method used", choices=["By number of solves", "By order of publication", "By ratio of solves per time unit"], default="By ratio of solves per time unit")
@option("display_nb", description="The number of problems you want to be displayed", min_value=1, max_value=25, default=10)
async def command_easiest(ctx, member: discord.User, method: str, display_nb: int):
    
    discord_id = ctx.author.id
    if member is not None:
        discord_id = member.id

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


@bot.slash_command(name="graph", description="Graph something!")
@option("data", choices=["solves"], default="solves")
@option("subset", choices=["local", "global"], default="local")
@option("days_count", min_value=0, max_value=1000, default=10)
async def command_graph(ctx, data: str, subset: str, days_count: int):
    
    await ctx.defer()

    if data == "solves":
        image_location = pe_plot.graph_solves(days_count, subset == "local")
    else:
        return await ctx.respond("The given parameters are not actually available")

    return await ctx.respond(file = discord.File(image_location))



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

    search = re.finditer("#(\d+)", message.content)
    message_problems = set([int(k.group(0)[1:]) for k in search if k.group(0)[1:].isnumeric()])
    for problem_id in itertools.islice(message_problems, 10):
        if problem_id <= 0 or problem_id > pe_api.last_problem():
            continue
            
        problem_embed = discord.Embed(description=f"[Open problem #{problem_id} in web browser](https://projecteuler.net/problem={problem_id})")

        await message.channel.send(embed=problem_embed)

    if len(message.attachments) > 0:
        
        main_attach = message.attachments[0]
        if "history" in main_attach.filename and "csv" in main_attach.filename:
            
            filename = main_attach.filename
            username = filename.split("_history")[0]
            file_url = main_attach.url

            content = requests.get(file_url).text
            file_path = pe_plot.generate_individual_graph(content, username)

            await message.channel.send("", file=discord.File(file_path))

            path = f"graphs/{username}/"
            files = glob.glob(path + "*")
            for f in files:
                os.remove(f)




@bot.slash_command(name="whosolved", description="Display a list of members who solved a particular problem")
@option("problem", description="The problem")
async def command_whosolved(ctx, problem: int):

    await ctx.defer()

    if problem is None:
        return await ctx.respond("Please specify a problem!")

    member_list = pe_api.get_all_members_who_solved(problem)

    if len(member_list) == 0:
        return await ctx.respond(f"Sadly, no member in my friend list solved problem #{problem}")
    
    boxed_members = "```" + ", ".join(member_list) + "```"
    return await ctx.respond(f"Here is the list of members who solved problem #{problem}" + boxed_members)


@bot.slash_command(name="compare", description="Compare the solves of two members")
@option("first_member", description="The first member you want to compare the solves of")
@option("second_member", description="The second member you want to compare the solves of")
@option("max_display", description="The maximum displayed number of problems", default=30, min_value=1, max_value=100)
async def command_compare(ctx, first_member: discord.User, second_member: discord.User, max_display: int):

    await ctx.defer()

    if first_member is None or second_member is None:
        return await ctx.respond("Please specify two valid users!")
    
    first_username = pe_api.project_euler_username(first_member.id)
    second_username = pe_api.project_euler_username(second_member.id)

    if not first_username or not second_username:
        return await ctx.respond("One of the two users (or both) has not linked their project euler account");

    first_solves = pe_api.problems_of_member(first_username)
    second_solves = pe_api.problems_of_member(second_username)

    common_solves = []
    common_not_solves = []
    only_first_solves = []
    only_second_solves = []

    last_pb = pe_api.last_problem()

    for index in range(1, last_pb + 1):
        if first_solves[index - 1] == "1" and second_solves[index - 1] == "1":
            common_solves.append(index)
        elif first_solves[index - 1] == "1" and second_solves[index - 1] == "0":
            only_first_solves.append(index)
        elif first_solves[index - 1] == "0" and second_solves[index - 1] == "1":
            only_second_solves.append(index)
        else:
            common_not_solves.append(index)

    if len(only_first_solves) == 0:
        only_first_solves = ["None actually"]
    if len(only_second_solves) == 0:
        only_second_solves = ["None actually"]

    response_text = "The two members have {0} solves in common.\n".format(len(common_solves))
    
    response_text += "Problems solved by `{0}` and not by `{1}`: ".format(first_username, second_username)
    response_text += "```" + ", ".join(list(map(str, only_first_solves))[:max_display]) + (" ({0} more)".format(len(only_first_solves) - max_display) if len(only_first_solves) > max_display else "") + "```"

    response_text += "Problems solved by `{0}` and not by `{1}`: ".format(second_username, first_username)
    response_text += "```" + ", ".join(list(map(str, only_second_solves))[:max_display]) + (" ({0} more)".format(len(only_second_solves) - max_display) if len(only_second_solves) > max_display else "") + "```"

    return await ctx.respond(response_text)


@bot.slash_command(name="thread", description="Create a private thread for a specific problem")
@option("problem", description="The problem you wish to open a thread for", min_value=1)
async def command_thread(ctx, problem: int):

    await ctx.defer()

    last_pb = pe_api.last_problem()
    
    # Just to ensure there's no unused thread
    if problem > last_pb:
        return await ctx.respond("This problem has not been published yet. Please try another one.")
    
    # Get the list of the threads objects on the server where the command was used
    available_threads = await get_available_threads(ctx.guild.id, ctx.channel.id)
    thread_name = THREAD_DEFAULT_NAME_FORMAT.format(problem)

    # If a thread already exists (check only with the name), then simply create a new link to it 
    if thread_name in list(map(lambda element: element.name, available_threads)):
        button_view = inters.problem_thread_view(problem_number=problem)
        return await ctx.respond("A thread has already been opened for this problem. You can join it here:", view=button_view)
    
    # Otherwise, find the appropriate channel
    adapted_channel = ctx.channel
    for chan in ctx.guild.channels:
        if chan.name == "problem-discussion":
            adapted_channel = chan
            break
    
    # Then create the thread in it
    thread_object = await adapted_channel.create_thread(name=thread_name, type=discord.ChannelType.private_thread, auto_archive_duration=60)
    
    # Make it impossible for non-moderator to invite people 
    await thread_object.edit(invitable=False)

    # Send the first message of the thread
    await thread_object.send("Start of the discussion for problem #{0}, only opened to the solvers :)".format(problem))
    
    # Retrieve the button object with the correct problem numbers
    button_view = inters.problem_thread_view(problem_number=problem)

    # Send the button
    await ctx.respond("Click the button below to join the appropriate thread!", view=button_view)
    

@bot.slash_command(name="list-threads", description="Show a list of available threads")
async def command_list_threads(ctx):
    
    # Allow for more than 3 seconds of thought
    await ctx.defer()

    available_threads = await get_available_threads(ctx.guild.id, ctx.channel.id)

    # Get the list of all available threads, and retrieve only their name
    available_threads = list(map(lambda element: element.name, available_threads))

    # Keep only those that fit the name for the threads created by the bot
    available_threads = list(filter(lambda element: "Problem #" in element and "discussion" in element, available_threads))
    
    # And split it in order to only get the numbers
    available_threads = list(map(lambda element: element.split()[1][1:], available_threads))

    # Put them in the right order
    available_threads = sorted(available_threads, key = lambda element: int(element))

    # Just in case threads expire
    if len(available_threads) == 0:
        available_threads.append("None actually")

    available_message = "Here are the problems with an open thread: ```" + ", ".join(available_threads) + "```"

    return await ctx.respond(available_message)


@bot.slash_command(name="randproblem", description="Give a random problem the user has not solved")
@option("member", description="The targetted member", default=None)
@option("minimum difficulty", description="minimum project euler difficulty rating", default=5, min=5, max=100)
@option("maximum difficulty", description="maximum project euler difficulty rating", default=100, min=5, max=100)
async def command_randproblem(ctx, member: discord.User, min_difficulty: int, max_difficulty: int):

    await ctx.defer()

    if member is None:
        member = ctx.author

    discord_id = member.id

    m = pe_api.Member(_discord_id = discord_id)
    if not m.is_discord_linked():
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")

    if min_difficulty > max_difficulty:
        return await ctx.respond("Minimum difficulty must be smaller than maximum difficulty")

    if m.solve_count() == len(m.solve_array()) or random.uniform(0,1) < 0.001:
        return await ctx.respond(f"I *randomly* selected problem #1729 for user: `{m.username()}`: <https://teyzer.github.io/problem1729/>")

    problems = pe_api.unsolved_problems(m.username())
    if min_difficulty == 5 and max_difficulty == 100:
        choice = random.choice(problems)
    else:
        difficulties = [*map(lambda problem: (problem.problem_id,problem.difficulty_rating),pe_api.PE_Problem.complete_list())]
        unsolved_difficulties = []
        unsolved_ids_map = {}
        for problem in problems:
            unsolved_ids_map[int(problem[0])] = problem

        for problem,difficulty in difficulties:
            if problem in unsolved_ids_map and min_difficulty <= difficulty <= max_difficulty:
                unsolved_difficulties.append(unsolved_ids_map[problem])

        if len(unsolved_difficulties) == 0:
            return await ctx.respond(f"{m.username()} has no unsolved problems in difficulty range [{min_difficulty},{max_difficulty}]")
        choice = random.choice(unsolved_difficulties)

    text_message = "I randomly selected problem #{0} for user `{1}`: \"{2}\". <https://projecteuler.net/problem={0}>"
    text_message = text_message.format(choice[0], m.username(), choice[1])

    return await ctx.respond(text_message)
    

@bot.slash_command(name="events", description="Get the status of an event")
@option("event", description="Which event", choices=["SoPE"])
@option("page", description="Which page of the leaderboard", min=1, max=10, default=1)
async def command_events(ctx, event: str, page: int):
    
    await ctx.defer()
    
    page_size = 15
    
    if event == "SoPE":
            
        ev = pe_events.eventSoPE()
        data = ev.scores()
        
        list_data = [[k, data[k]] for k in data.keys()]
        list_data = sorted(list_data, key=lambda element: element[1], reverse=True)
        list_data = list_data[page_size * (page - 1) : page_size * page]
        
        text_message = f"Here is the page n°{page} out of {(len(data.keys()) + 14) // page_size} for the event {event}:"
        text_message += "```c\n" + "\n".join([f"{page_size * (page - 1) + i + 1}: {list_data[i][0]} with {list_data[i][1]} points" for i in range(len(list_data))]) + "```"
        
        await ctx.respond(text_message)
    

@bot.slash_command(name="events-data", description="Get the data of an event")
@option("event", description="Which event", choices=["SoPE"])
async def command_events_data(ctx, event: str):
    
    await ctx.defer()

    fls = [f"events/{event}/data.json"]
    
    if event == "SoPE":
        
        ev = pe_events.eventSoPE()
        solves = list(map(int, ev.data["solves"].keys()))
        
        grid_image = pe_image.project_euler_grid(solves)
        fls.append(grid_image)

        await ctx.respond("", file=discord.File(fls[1]))
    
        os.remove(grid_image)


@bot.slash_command(name="grid", description="Get the solve grid of an user")
@option("member", description="The targetted user", default = None)
async def commmand_grid(ctx, member: discord.User):

    await ctx.defer()

    m = pe_api.Member(_discord_id = (ctx.author.id if member is None else member.id))

    if not m.is_discord_linked():
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")

    solves = []
    for id, b in enumerate(m.solve_array()):
        if b == True:
            solves.append(id + 1)

    grid_image = pe_image.project_euler_grid(solves)
    
    await ctx.respond(f"Here is the grid for user `{m.username()}`", file=discord.File(grid_image))
    os.remove(grid_image)
    

@bot.slash_command(name="has-been-claimed", description="Get the status")
@option("problem", description="Which problem", min=1)
async def command_has_been_claimed(ctx, problem: int):

    await ctx.defer()

    ev = pe_events.eventSoPE()

    if ev.is_problem_solved(problem):
        claimer = pe_api.Member(_username = ev.data["solves"][str(problem)]["username"])
        return await ctx.respond(f"Problem {problem} has already been claimed by {claimer.username_ping()} (SoPE event)", allowed_mentions = discord.AllowedMentions(users = False))
    else:
        return await ctx.respond(f"Problem {problem} has not been claimed yet (SoPE event)")


@bot.slash_command(name="easiest-sope", description="Get the easiests problems available in the SoPE")
@option("member", description="The member you want to use it on", default = None)
@option("display_nb", description="The number of problem you want dislayed", default=10, min=1, max=25)
async def command_easiest_sope(ctx, member: discord.User, display_nb: int):

    await ctx.defer()

    discord_id = ctx.author.id
    if member is not None:
        discord_id = member.id

    m = pe_api.Member(_discord_id = discord_id)

    if not m.is_discord_linked():
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")

    problem_specs = pe_api.PE_Problem.complete_list()
    problem_list = [problem_specs[i - 1] for i in m.unsolved_problems()]

    problems = sorted(
        problem_list, 
        key=lambda pb: int(pb.solves) / (int(time.time()) + 31536000 - int(pb.unix_publication) ), 
        reverse=True
    )

    ev = pe_events.eventSoPE()
    problems = list(filter(
        lambda pb: not ev.is_problem_solved(pb.problem_id),
        problem_list
    ))

    problems = problems[:display_nb]

    lst = "```" + "\n".join(list(map(
        lambda pb: f"Problem #{pb.problem_id}: '{pb.name}' solved by {pb.solves} members", 
        problems
    ))) + "```"

    return await ctx.respond(f"Here are the {display_nb} easiest problems available to `{m.username()}` for SoPE:" + lst)


@bot.slash_command(name="update-roles")
@option("member", description="The member that you want to be updated", default = None)
async def command_update_roles(ctx, member: discord.User):

    # This allows to give more than 3 seconds to execute the command
    await ctx.defer()

    discord_id = ctx.author.id
    if member is not None:
        discord_id = member.id

    m = pe_api.Member(_discord_id = discord_id)
    await update_member_roles(m)

    return await ctx.respond("I did not crash during the update, that's all I know", ephemeral=True)




""" 
FUNCTIONS MADE TO HELP, STRICTLY CONCERNING DISCORD 
"""


async def update_member_roles(m: pe_api.Member):

    guild = bot.get_guild(PROJECT_EULER_SERVER)
    member = guild.get_member(int(m.discord_id()))

    roles = member.roles
    
    solve_index = (m.solve_count() // 100) if m.solve_count() < 900 else 8
    
    # Getting the object roles rather than simply their id
    appropriate_role = guild.get_role(SOLVE_ROLES[solve_index])
    perfectionist_role = guild.get_role(PERFECTIONIST_ROLE)

    # We check if the member already has the role corresponding to its solve range
    found_appropriate = False
    found_perfectionnist = False

    # And we cache roles to remove later
    to_remove = []
    to_add = []

    for role in roles:

        if role.id in SOLVE_ROLES:
            if role.id == appropriate_role.id:
                found_appropriate = True
            else:
                to_remove.append(role)

        if role.id == perfectionist_role.id:
            found_perfectionnist = True


    # Perfectionnist role
    if not found_perfectionnist and m.solve_count() == len(m.solve_array()):
        to_add.append(perfectionist_role)
    if not found_appropriate:
        to_add.append(appropriate_role)

    await member.add_roles(*to_add)
    await member.remove_roles(*to_remove)


async def get_available_threads(guild_id: int, channel_id: int) -> list:
    
    if int(guild_id) == PROJECT_EULER_SERVER:
        channel_id = THREADS_CHANNEL
    
    guild = bot.get_guild(int(guild_id))
    channel = guild.get_channel(int(channel_id))
    
    threads = guild.threads
    async for t in channel.archived_threads(private = True, limit = 100):
        threads.append(t)
        
    return threads
    

if __name__ == "__main__":
    pass