import asyncio
import time

import datetime
import pytz

from math import *
import json

from requests import TooManyRedirects

import pe_database
import pe_api
import pe_image
import pe_plot
import pe_events
import pe_session
import phone_api
import itertools

import requests

import interactions_discord as inters
import discord
from discord import option

import glob
import os
import random
import re
import traceback

from rich.console import Console
from rich import inspect

import sympy
from typing import Dict, List, Tuple, Any, Optional


console = Console(record = True)

TEST_SERVER = 943488228084813864
PROJECT_EULER_SERVER = 903915097804652595
GUILD_IDS = [PROJECT_EULER_SERVER]

BOT_APPLICATION_ID = 930813331512635413

ADMINISTRATOR_ROLE = 905683104461619261
MODERATOR_ROLE = 1103325920028266607

# Initial condition
STARTING_TIME = datetime.datetime.now(pytz.utc)

# In order to keep track of the last time the solves of members were checked
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
TESTING_CHANNEL_TO_ANNOUNCE = 1179793930993283144
BRAINSTORMING_CHANNEL = 1268346986810183680
SMALL_ANNOUNCEMENTS_CHANNEL = 1268526845318529034
THREADS_CHANNEL = 904251551474942002

SOLVE_ROLES = [904255861503975465, 905987654083026955, 975720598741331988, 905987783892561931, 975722082996473877, 905987999949529098, 975722386559225878, 975722571473498142, 1051483511749619722, 1351315236879073301]
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

PROBLEM_LINK = "[Jump to problem {0}](<https://projecteuler.net/problem={0}>)"


def pe_discord_api_setup(channels: dict):

    global CHANNELS_TO_ANNOUNCE, SPECIAL_CHANNELS_TO_ANNOUNCE, SMALL_ANNOUNCEMENTS_CHANNEL, THREADS_CHANNEL

    CHANNELS_TO_ANNOUNCE = channels["solve_channel"]
    SPECIAL_CHANNELS_TO_ANNOUNCE = channels["award_channel"]
    SMALL_ANNOUNCEMENTS_CHANNEL = channels["small_channel"]
    THREADS_CHANNEL = channels["thread_channel"]



async def major_update() -> bool:

    global REPEATS_SINCE_START
    global REPEATS_SUCCESSFUL_SINCE_START

    REPEATS_SINCE_START += 1

    # SANITY CHECKS
    website_active = pe_session.is_website_active()
    session_alive = pe_session.is_connected()

    if not website_active or not session_alive:
        pe_session.refresh_tokens()
        website_active = pe_session.is_website_active()
        session_alive = pe_session.is_connected()

    if not website_active:
        console.log("Skipped major_update because website does not respond.")
        await async_set_bot_status(3, "Website died")
        return False

    if not session_alive:
        console.log("Skipped major_update because there is no active session.")
        await async_set_bot_status(3, "Session died")
        return False

    # This is turned down for now as it doesn't work
    """
    if not website_down and not session_alive:
        pe_session.refresh_tokens()
    """

    # In the console
    console.log(f"Starting repeat #{REPEATS_SINCE_START}", end="| ")

    if REPEATS_SINCE_START % (3600 // AWAIT_TIME) == 1:
        console.log("Trying to update global stats... ", end="")
        global_update_output = pe_api.update_global_stats()
        console.log(global_update_output, end= " | ")

    # Getting the data required
    try:
        profiles = pe_api.update_process()
    
    except Exception as exc:
        console.log(exc, traceback.format_exc())
        await async_set_bot_status(3, "Unknown error")
        return False

    await async_set_bot_status([1, 2][not pe_api.LAST_REQUEST_SUCCESSFUL])

    if profiles is None:
        return False
    
    # Not important, you can skip this explanation
    # Only goal is to keep each profile in the database with a solve list that is the length of the number of problems
    if pe_api.last_problem() != pe_api.last_problem_database():
        console.log("[(-) New problem detected, adding one zero to everyone]")
        m: pe_api.Member
        for m in pe_api.Member.members():
            m.push_basics_to_database()
        console.log("[(+) Updated all members in the database]")
    
    # event = pe_events.eventSoPE()
    # event = pe_events.eventMonthly1()
    messages_to_announce = pe_events.update_events_without_profiles()
    await announce_messages(messages_to_announce)

    if len(profiles) == 0:
        return True
    
    problems: List[pe_api.Problem] = pe_api.Problem.complete_list()
    awards_specs = pe_api.get_awards_specs()
    
    for profile in profiles:
        
        member: pe_api.Member = profile["member"]
        solves: List[pe_api.Solve] = profile["solves"]
        awards = profile["awards"]
        
        if member.private():
            continue

        for solve in solves:
            
            problem: pe_api.Problem = solve.problem()
            pe_api.push_solve_to_database(member, solve.problem())

            for channel_id in CHANNELS_TO_ANNOUNCE:
                
                channel = bot.get_channel(channel_id)
                
                #decide what message to send depending on how many solvers there are
                if int(problem.solves()) <= 3:
                    sending_message = AWARDING_SENTENCES[problem.solves() - 1].format(member.username_ping(), problem.problem_id(), problem.name())
                else:
                    sending_message = AWARDING_SENTENCES[3].format(member.username_ping(), problem.problem_id(), problem.name(), problem.solves())
                    
                # add related emojis
                # optional_stars = " 🌠" if not event.is_problem_solved(problem.problem_id) else ""
                optional_bee = " ⚡" if problem.problem_id() == len(problems) else ""
                optional_emojis = optional_bee
                
                sending_message = sending_message + optional_emojis + " " + PROBLEM_LINK.format(problem.problem_id())
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

        for part in [0, 1, 2]:
            for award in awards[part]:
                for channel_id in SPECIAL_CHANNELS_TO_ANNOUNCE:
                    channel = bot.get_channel(channel_id)
                    award_name = awards_specs[part][award]
                    await channel.send(f"{member.username_ping()} got the award '{award_name}', congratulations!", 
                                        allowed_mentions = discord.AllowedMentions(users = False))
            
            
    messages = pe_events.update_events(profiles)
    await announce_messages(messages)

    return True


    

@bot.event
async def on_ready():

    # Global variables in order to modify them
    global REPEATS_SINCE_START
    global REPEATS_SUCCESSFUL_SINCE_START

    # The 'Is playing {}' presence
    await bot.change_presence(activity=discord.Game(name="{0} Restarting...".format(ORANGE_CIRCLE)))
    
    # For debugging
    console.log(f'Login made as {bot.user}')
    await tester()

    need_to_stop = False
    while not need_to_stop:
        
        # Async sleep
        await asyncio.sleep(AWAIT_TIME)
        
        # Main loop
        await major_update()



""" 
COMMANDS 
"""

@bot.slash_command(name="update", description="Update the known friend list of the bot")
async def command_hello(ctx):
    
    await ctx.defer()

    data = await major_update()

    if data in [False, None]:
        await ctx.respond("An error occurred during the fetch, this may need human checkup. Use /status to get more details.")
    else:
        await ctx.respond("The data was updated!")


@bot.slash_command(name="status", description="Give the current status of the bot, concerning recently fetched data")
async def command_status(ctx):
    
    text_response = "The last fetch of data was `{0}`. The last successful fetch was made on `{1}`.\n"
    text_response += "Since the last restart of the bot (`{4}`), there was `{2}` successful requests, over `{3}` in total.\n"
    text_response += "(And `{5}` queries to the database).\n"
    text_response += "Website status from my computer: `{6}`. Session of the bot status: `{7}`"

    fetched_data_status = "successful" if pe_api.LAST_REQUEST_SUCCESSFUL else "unsuccessful"
    fetched_data_time_status = pe_api.LAST_REQUEST_TIME.strftime("%Y-%m-%d at %H:%M:%S UTC")
    fetch_starting_time = STARTING_TIME.strftime("%Y-%m-%d at %H:%M:%S UTC")
    website_status = "online" if  pe_session.is_website_active() else "down"
    session_status = "active" if pe_session.is_connected() else "killed"

    text_response = text_response.format(
        fetched_data_status, 
        fetched_data_time_status, 
        str(pe_api.TOTAL_SUCCESS_REQUESTS),
        str(pe_api.TOTAL_REQUESTS), 
        fetch_starting_time,
        pe_database.DB_TOTAL_REQUESTS,
        website_status,
        session_status
    )

    await ctx.respond(text_response)


@bot.slash_command(name="profile", description="Render your project euler profile in a cool image")
@option("member", description="Mention the member you want the profile to be displayed", default=None)
async def command_profile(ctx, member: discord.User):

    await ctx.defer()

    if member is None:
        member = ctx.author

    discord_id = member.id
    profile_url = "https://cdn.discordapp.com/embed/avatars/{0}.png".format(int(member.discriminator) % 5)

    if member.avatar is not None:
        profile_url = member.avatar.url

    m = pe_api.Member(_discord_id = str(discord_id))

    if not m.is_discord_linked():
        return await ctx.respond("This user is not linked! Please link your account first")
    
    if m.private() and m.discord_id() != str(ctx.author.id):
        return await ctx.respond("This user has a private profile.")
    
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

    await major_update()

    discord_user_id = ctx.author.id
    database_discord_user = pe_database.query_single(f"SELECT * FROM members WHERE discord_id = '{discord_user_id}';")
    if len(database_discord_user) > 0:
        sentence = f"Your discord account is already linked to the account `{database_discord_user[0]['username']}`, type /unlink to unlink it"
        return await ctx.respond(sentence)

    users = pe_database.query_single(f"SELECT * FROM members WHERE username = '{username}';")
    if len(users) == 0:
        return await ctx.respond("This username is not in my friend list. Add the bot account on project euler first: 1910895_2C6CP6OuYKOwNlTdL8A5fXZ0p5Y41CZc\nThen ensure your account is not unlisted.\nIf you think this is a mistake, send a DM to <@439143335932854272>.")

    user = users[0]
    if str(user["discord_id"]) != "":
        return await ctx.respond(f"This account is already linked to <@{user['discord_id']}>")

    temp_query = f"UPDATE members SET discord_id = '{discord_user_id}' WHERE username = '{username}'"
    pe_database.query_single(temp_query)

    m = pe_api.Member(_username = username)
    await update_member_roles(m)

    return await ctx.respond(f"Your account was linked to `{username}`!")


@bot.slash_command(name="unlink", description="Unlink your Project Euler account with your discord account")
async def command_unlink(ctx):

    await ctx.defer()

    discord_user_id = ctx.author.id
    database_discord_user = pe_database.query_single(f"SELECT * FROM members WHERE discord_id = '{discord_user_id}';")
    # database_discord_user = dbqueries.single_req("SELECT * FROM members WHERE discord_id = '{0}'".format(discord_user_id))

    if len(database_discord_user) == 0:
        return await ctx.respond("Your discord account isn't linked to any profile")

    temp_query = f"UPDATE members SET discord_id = '' WHERE discord_id = '{discord_user_id}';"
    # dbqueries.single_req(temp_query)
    pe_database.query_single(temp_query)

    return await ctx.respond("Your discord account was unlinked to the project euler `{0}` account".format(database_discord_user[0]["username"]))


@bot.slash_command(name="kudos", description="Display the kudos progression of your posts on the forum")
@option("member", description="Mention the member you want the kudos to be displayed", default=None)
async def command_kudos(ctx, member: discord.User):

    await ctx.defer()

    pe_member = pe_api.Member(_discord_id = (ctx.author.id if member is None else member.id))

    if not pe_member.is_discord_linked():
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")
    
    if pe_member.private() and pe_member.discord_id() != str(ctx.author.id):
        return await ctx.respond("This user has a private profile.")

    if not pe_member.has_kudos_in_database():
        pe_member.push_kudo_to_database()
        return await ctx.respond("Your current posts have been saved in the database. Next time you use this command,"
                                 "the bot will display how manny kudos you earned.")

    new_kudos = pe_member.get_new_kudos()
    pe_member.push_kudo_to_database()
    
    kudo_count = pe_member.kudo_count()
    
    change = sum([el[1] for el in new_kudos])

    if change == 0:
        return await ctx.respond(f"No change for user `{pe_member.username_option()}`, still {kudo_count} kudos.")
    else:
        k = "```" + "\n".join(list(map(lambda x: ": ".join(list(map(str, x))), new_kudos))) + "```"
        return await ctx.respond("There was some change for user `{0}`! You gained {1} kudos on the following posts (for a total of {2} kudos):".format(pe_member.username_option(), change, kudo_count) + k)


@bot.slash_command(name="easiest", description="Find the easiest problems you haven't solved yet")
@option("member", description="The member you want you want to see the next possible solves", default=None)
@option("method", description="The method used", choices=["By number of solves", "By order of publication", "By ratio of solves per time unit"], default="By ratio of solves per time unit")
@option("display_nb", description="The number of problems you want to be displayed", min_value=1, max_value=25, default=10)
async def command_easiest(ctx, member: discord.User, method: str, display_nb: int):
    
    await ctx.defer()

    discord_id = ctx.author.id
    if member is not None:
        discord_id = member.id

    m = pe_api.Member(_discord_id = discord_id)

    if not m.is_discord_linked():
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")

    if m.private() and m.discord_id() != str(ctx.author.id):
        return await ctx.respond("This user has a private profile.")

    problem_specs = pe_api.Problem.complete_list()
    problem_list = [problem_specs[i - 1] for i in m.unsolved_problems()]

    def sort_method_key(problem: pe_api.Problem, method: str):
        if method == "By number of solves":
            return int(problem.solves())
        if method == "By order of publication":
            return int(problem.unix_publication())
        if method == "By ratio of solves per time unit":
            time_window = 10
            problem_id = problem.problem_id()
            last = len(problem_specs)
            if problem_id <= last - time_window:
                score = problem.solves() / sum([problem_specs[i - 1].solves() for i in range(problem_id, problem_id + time_window)])
            else:
                score = problem.solves() / sum([problem_specs[i - 1].solves() for i in range(problem_id - time_window, problem_id)])
            return score * problem.solves()
        

    problems = sorted(
        problem_list, 
        key=lambda problem: sort_method_key(problem, method), 
        reverse=True
    )

    problems = problems[:display_nb]

    lst = "```" + "\n".join(list(map(
        lambda pb: f"Problem #{pb.problem_id()}: '{pb.name()}' solved by {pb.solves()} members", 
        problems
    ))) + "```"

    return await ctx.respond(f"Here are the {display_nb} easiest problems available to `{m.username_option()}`:" + lst)


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
        
        try:
            data = pe_api.Problem.complete_list()
            problem_object: pe_api.Problem = data[problem_id - 1]
            problem_embed = discord.Embed(description=
                f"[Open problem #{problem_id}](https://projecteuler.net/problem={problem_id}) in web browser: '{problem_object.name()}' ({problem_object.difficulty()}%/{problem_object.solves()})"
            )
        except Exception as _:
            problem_embed = discord.Embed(description=
                f"[Open problem #{problem_id} in web browser](https://projecteuler.net/problem={problem_id})"
            )

        await message.channel.send(embed=problem_embed)

    if len(message.attachments) > 0:
        
        main_attach = message.attachments[0]
        if "history" in main_attach.filename and "csv" in main_attach.filename:
            
            filename = main_attach.filename
            username = filename.split("_history")[0]
            file_url = main_attach.url

            content = requests.get(file_url).text
            file_path = pe_plot.generate_individual_graph(content, username)

            if file_path is None:
                await message.channel.send("I could not generate the graph, it requires to know when was each problem published and the request to the server failed.")
            else:
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

    members = pe_api.Member.members()

    solvers = []

    m: pe_api.Member
    for m in members:

        if m.private():
            continue

        if m.has_solved(problem):
            solvers.append(m.username_option())

    # return await ctx.respond("Due to an issue concerning privacy, this command isn't available currently. This should only last for a few days at most, sorry!")

    # member_list = pe_api.get_all_members_who_solved(problem)

    if len(solvers) == 0:
        return await ctx.respond(f"Sadly, no member in my friend list solved problem #{problem}")
    
    try:
        boxed_members = "```" + ", ".join(solvers) + "```"
        return await ctx.respond(f"Here is the list of members who solved problem #{problem}" + boxed_members)
    except Exception as _:
        return await ctx.respond(f"The return message must be 2000 or fewer in length, sorry!")


@bot.slash_command(name="compare", description="Compare the solves of two members")
@option("first_member", description="The first member you want to compare the solves of")
@option("second_member", description="The second member you want to compare the solves of")
@option("max_display", description="The maximum displayed number of problems", default=30, min_value=1, max_value=100)
async def command_compare(ctx, first_member: discord.User, second_member: discord.User, max_display: int):

    await ctx.defer()

    # return await ctx.respond("Due to an issue concerning privacy, this command isn't available currently. This should only last for a few days at most, sorry!")
    if first_member is None or second_member is None:
        return await ctx.respond("Please specify two valid users!")

    first_pe_member = pe_api.Member(_discord_id = first_member.id)
    second_pe_member = pe_api.Member(_discord_id = second_member.id)

    if not first_pe_member.is_discord_linked() or not second_pe_member.is_discord_linked():
        return await ctx.respond("One of the two users has not linked their project euler account!")

    if first_pe_member.private() or second_pe_member.private():
        return await ctx.respond("One of the two users has a private profile.")

    first_username = first_pe_member.username_option()
    second_username = second_pe_member.username_option()

    common_solves = []
    common_not_solves = []
    only_first_solves = []
    only_second_solves = []

    last_problem_id = pe_api.last_problem()

    for index in range(1, last_problem_id + 1):

        if first_pe_member.has_solved(index) and second_pe_member.has_solved(index):
            common_solves.append(index)
        elif first_pe_member.has_solved(index) and not second_pe_member.has_solved(index):
            only_first_solves.append(index)
        elif not first_pe_member.has_solved(index) and second_pe_member.has_solved(index):
            only_second_solves.append(index)
        else:
            common_not_solves.append(index)

    mix_color = (255,87,51)
    color_one = (199,0,57)
    color_two = (255,195,15)

    solves_with_color = []
    for solve in common_solves:
        solves_with_color.append((solve, mix_color))
    for solve in only_first_solves:
        solves_with_color.append((solve, color_one))
    for solve in only_second_solves:
        solves_with_color.append((solve, color_two))
        
    grid_image = pe_image.project_euler_grid(solves_with_color)

    if len(only_first_solves) == 0:
        only_first_solves = ["None actually"]
    if len(only_second_solves) == 0:
        only_second_solves = ["None actually"]

    response_text = "The two members have {0} solves in common.\n".format(len(common_solves))
    
    response_text += "Problems solved by `{0}` and not by `{1}`: ".format(first_username, second_username)
    response_text += "```" + ", ".join(list(map(str, only_first_solves))[:max_display]) + (" ({0} more)".format(len(only_first_solves) - max_display) if len(only_first_solves) > max_display else "") + "```"

    response_text += "Problems solved by `{0}` and not by `{1}`: ".format(second_username, first_username)
    response_text += "```" + ", ".join(list(map(str, only_second_solves))[:max_display]) + (" ({0} more)".format(len(only_second_solves) - max_display) if len(only_second_solves) > max_display else "") + "```"

    await ctx.respond(response_text, file = discord.File(grid_image))
    os.remove(grid_image)


@bot.slash_command(name="thread", description="Create a private thread for a specific problem")
@option("problem", description="The problem you wish to open a thread for")
async def command_thread(ctx, problem: int):

    await ctx.defer()

    try:
        last_pb = pe_api.last_problem()
    except Exception as _:
        last_pb = pe_api.last_problem_database()
    
    # Just to ensure there's no unused thread
    if problem > last_pb:
        return await ctx.respond("This problem has not been published yet. Please try another one.")
    
    # Get the list of the threads objects on the server where the command was used
    available_threads = await get_available_threads(ctx.guild.id, ctx.channel.id)
    thread_name = THREAD_DEFAULT_NAME_FORMAT.format(problem)

    try:
        problem_object = pe_api.Problem(problem)
        problem_name = problem_object.name().replace('$', '*')
        optional_problem_name = f"'{problem_name}'"
    except Exception as _:
        optional_problem_name = "Failed to retrieve problem name"

    # If a thread already exists (check only with the name), then simply create a new link to it 
    if thread_name in list(map(lambda element: element.name, available_threads)):
        button_view = inters.problem_thread_view(problem_number=problem)
        response_text = f"A thread has already been opened for problem #{problem} ({optional_problem_name}). You can join it here:"
        return await ctx.respond(response_text, view=button_view)
    
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
    await thread_object.send(f"Start of the discussion for problem #{problem}, only opened to the solvers :)")
    
    # Retrieve the button object with the correct problem numbers
    button_view = inters.problem_thread_view(problem_number=problem)

    # Send the button
    await ctx.respond(f"Click the button below to join the appropriate thread! (Problem #{problem}: {optional_problem_name})", view=button_view)
    

@bot.slash_command(name="list-threads", description="Show a list of available threads")
async def command_list_threads(ctx):
    
    # Allow for more than 3 seconds of thought
    await ctx.defer()

    # Get the list of all available threads, and retrieve only their name
    threads = await get_available_threads(ctx.guild.id, ctx.channel.id)
    threads = [x.name for x in threads]

    # Keep only those that fit the name for the threads created by the bot
    threads = [x for x in threads if x.startswith('Problem #') and x.endswith(" discussion")]

    # Get the list of numbers. Go through a set to get rid of duplicates -
    # there seem to be multiple threads for some problems?
    threads = list({int(x.split()[1][1:]) for x in threads})
    threads.sort()

    # Merge consecutive threads into runs like "12-15".
    # Do not do this for negative bonus problems to avoid "-3--2".
    threads.append(threads[-1]+2)
    runs = []
    start = None
    for i in range(len(threads)-1):
        if start is None:
            start = threads[i]
        if threads[i+1] == threads[i]+1 and start > 0:
            continue
        end = threads[i]
        if start == end:
            runs.append(str(start))
        else:
            runs.append(f"{start}-{end}")
        start = None

    available_message = "Here are the problems with an open thread: ```" + ", ".join(runs) + "```"

    return await ctx.respond(available_message)


@bot.slash_command(name="randproblem", description="Give a random problem the user has not solved")
@option("member", description="The targeted member", default=None)
async def command_randproblem(ctx, member: discord.User):

    await ctx.defer()

    if member is None:
        member = ctx.author

    discord_id = member.id

    m = pe_api.Member(_discord_id = str(discord_id))
    if not m.is_discord_linked():
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")
    
    if m.private() and m.discord_id() != str(ctx.author.id):
        return await ctx.respond("This user has a private profile.")

    if m.solve_count() == len(m.solve_array()):
        return await ctx.respond(f"I *randomly* selected problem #1729 for user: `{m.username_option()}`: <https://teyzer.github.io/problem1729/>")

    problems = m.unsolved_problems()
    all_problems = pe_api.Problem.complete_list()
    choice: pe_api.Problem = all_problems[random.choice(problems) - 1]

    text_message = "I randomly selected problem #{0} for user `{1}`: \"{2}\". <https://projecteuler.net/problem={0}>"
    text_message = text_message.format(choice.problem_id(), m.username_option(), choice.name())

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
        
        solves_with_color = list(map(lambda x: (x, (220, 220, 220)), solves))
        
        grid_image = pe_image.project_euler_grid(solves_with_color)
        fls.append(grid_image)

        await ctx.respond("", file=discord.File(fls[1]))
    
        os.remove(grid_image)


@bot.slash_command(name="grid", description="Get the solve grid of an user")
@option("member", description="The targeted user", default = None)
async def commmand_grid(ctx, member: discord.User):

    await ctx.defer()

    m = pe_api.Member(_discord_id = (ctx.author.id if member is None else member.id))

    if not m.is_discord_linked():
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")

    if m.private() and m.discord_id() != str(ctx.author.id):
        return await ctx.respond("This user has a private profile.")

    solves = []
    for index, boolean in enumerate(m.solve_array()):
        if boolean:
            solves.append(index + 1)

    solves_with_color = list(map(lambda x: (x, (220, 220, 220)), solves))
    grid_image = pe_image.project_euler_grid(solves_with_color)
    
    await ctx.respond(f"Here is the grid for user `{m.username_option()}`", file=discord.File(grid_image))
    os.remove(grid_image)
    
    
@bot.slash_command(name="grid-animation", description="Get the solve grid of an user")
@option("member", description="The targeted user", default = None)
async def commmand_grid_animation(ctx, member: discord.User):
    
    await ctx.defer()

    m = pe_api.Member(_discord_id = (ctx.author.id if member is None else member.id))

    if not m.is_discord_linked():
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")

    if m.private() and m.discord_id() != str(ctx.author.id):
        return await ctx.respond("This user has a private profile.")
    
    username = m.username_option()
    content = m.solve_csv()
    
    file_path = pe_plot.generate_individual_graph(content, username)

    if file_path is None:
        await ctx.respond("I could not generate the graph, it requires to know when was each problem published and the request to the server failed.")
    else:
        await ctx.respond("", file=discord.File(file_path))

        path = f"graphs/{username}/"
        files = glob.glob(path + "*")
        for f in files:
            os.remove(f)


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

    await ctx.respond("I did not crash during the update, that's all I know", ephemeral=True)


@bot.slash_command(name="announce-back")
@option("problem", description="Which problem", min=1)
@option("member", description="Which member", default = None)
async def command_announce_back(ctx, problem: int, member: discord.User):

    await ctx.defer()

    perms = await sufficient_permissions(ctx.guild.get_member(ctx.author.id))

    if not perms:
        return await ctx.respond("You need to be a moderator or more to use this, sorry!", ephemeral=True)
    
    discord_id = ctx.author.id

    if member is not None:
        discord_id = member.id

    m = pe_api.Member(_discord_id = discord_id)
    m.make_problem_unsolved(problem)

    await ctx.respond("The solve will quickly be announced. Use /update if you want it to be right now.")


@bot.slash_command(name="force-new-session")
async def command_force_new_session(ctx):

    await ctx.defer()

    perms = await sufficient_permissions(ctx.guild.get_member(ctx.author.id))

    if not perms:
        return await ctx.respond("You need to be a moderator or more to use this, sorry!", ephemeral=True)
    
    values = pe_session.refresh_tokens()
    success = not(any([values[k] is None for k in values.keys()]))

    pe_api.COOKIES = values

    return await ctx.respond(f"Done. Returned keys are non-empty: {success}")


@bot.slash_command(name="leaderboard")
async def command_leaderboard(ctx):

    await ctx.defer()

    leaderboard_data = [(m.username_option(), m.solve_count()) for m in pe_api.Member.members()]
    return await inters.leaderboard_page(ctx, leaderboard_data, True, True, 10)


@bot.slash_command(name="botisdown")
@option("details", description="If you want to describe why you think so", default="")
async def bot_is_down(ctx, details: str):

    await ctx.defer()

    phone_api.bot_info(f"Warning by user: {details}")

    return await ctx.respond("Your alert has been sent successfully, sorry for the downtime again!")


@bot.slash_command(name="awards-requirements", description="Gives the problems you need to solve left to get a specific award")
@option("award", description="The award you want to get", choices=[
    "As Easy As Pi",
    "Unlucky Squares",
    "Prime Obsession",
    "Trinary Triumph",
    "Fibonacci Fever",
    "Triangle Trophy",
    "Lucky Luke"
])
@option("member", description="Which member", default = None)
async def command_awards_requirements(ctx, award: str, member: discord.User = None):

    await ctx.defer()

    if award is None:
        return await ctx.respond("Please specify an award!")
    
    discord_id = ctx.author.id
    if member is not None:
        discord_id = member.id

    m = pe_api.Member(_discord_id = discord_id)

    if m.private() and m.discord_id() != str(ctx.author.id):
        return await ctx.respond("This user has a private profile.")
    
    solve_list = m.solved_problems()
    last_pb = len(m.solve_array())

    valid_problems = []
    solves_needed = 0

    if award == "As Easy As Pi":
        valid_problems = sorted([3, 14, 15, 92, 65, 35, 89, 79, 32, 38, 45])
        solves_needed = len(valid_problems)
    
    if award == "Unlucky Squares":
        i = 1
        while i*i <= last_pb:
            valid_problems.append(i*i)
            i += 1
        solves_needed = 13
    
    if award == "Prime Obsession":
        valid_problems = list(sympy.primerange(0, len(solve_list)))
        solves_needed = 50

    if award == "Trinary Triumph":
        valid_problems = [1, 3, 9, 27, 81, 243, 729]
        solves_needed = len(valid_problems)

    if award == "Fibonacci Fever":
        valid_problems = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]
        solves_needed = len(valid_problems)

    if award == "Triangle Trophy":
        valid_problems = list([i * (i + 1) // 2 for i in range(1, 25+1)])
        solves_needed = len(valid_problems)
    
    if award == "Lucky Luke":
        # Code from https://oeis.org/A000959
        valid_problems = list(range(1, len(solve_list) + 1, 2))
        j = 1
        while j <= len(valid_problems) - 1 and valid_problems[j] <= len(valid_problems):
            del valid_problems[valid_problems[j]-1::valid_problems[j]]
            j += 1

    solve_list = set(solve_list)
    already_solved = [k for k in valid_problems if k in solve_list]
    not_solved = [k for k in valid_problems if not (k in solve_list)]

    left_to_solve = solves_needed - len(already_solved)
    if left_to_solve <= 0:
        return await ctx.respond("You already have the award!")
    
    text_list = "```" + ", ".join(list(map(str, not_solved))) + "```"
    return await ctx.respond(f"You need to solve {left_to_solve} problems among the following list to get the '{award}' award: {text_list}")
    
    

@bot.slash_command(name="problems-select", description="Gives a precise list of problems")
@option("options", description="Options")
@option("member", description="Which member", default = None)
async def command_awards_requirements(ctx, options: str, member: discord.User = None):

    limit_for_problems = 15

    if "HELP" in options.upper():

        help_text = "Usage: `/problems-select {options} [member]`\n"
        help_text += "`{options}` has the following format: `command1 | command2 | command3 | ...`\n\n"
        help_text += "Each command can be of one of the following formats:\n"
        help_text += "`%VALUE >= N` where %VALUE is one of `%DIFFICULTY`, `%ID`, `%SOLVES` and >= can be remplaced by ==, <=, <, >, with N a given integer. Filter problems based on id, difficulty, solves.\n"
        help_text += "`LIMIT N` - where N is a given integer, limit the list to N problems.\n"
        help_text += "`SORT %VALUE [DESC]` will sort the problems based on %VALUE, in reversed order if DESC is specified\n"
        help_text += "`SOLVED` or `NOT SOLVED`, will filter problems on whether you've solved them or not.\n\n"
        help_text += f"A limit of {limit_for_problems} problems is applied at the end for each request. Not case sensitive.\n"
        help_text += "An exemple would be: `%ID >= 400 | NOT SOLVED | SORT %DIFFICULTY DESC`: gives the list of problems after 400 that you did not solve, with the highest difficulty." 

        return await ctx.respond(help_text)


    current_list = pe_api.Problem.complete_list()

    discord_id = ctx.author.id
    if member is not None:
        discord_id = member.id

    m = pe_api.Member(_discord_id = discord_id)
    if m.private() and m.discord_id() != str(ctx.author.id):
        return await ctx.respond("This user has a private profile.")
    
    arguments = options.upper().split("|")
    arguments = list(map(lambda x: x.replace(" ", ""), arguments)) + [f"LIMIT{limit_for_problems}"]

    def weak_eval(exp: str, problem: pe_api.Problem):
        if exp == "%DIFFICULTY":
            return problem.difficulty()
        if exp == "%ID":
            return problem.problem_id()
        if exp == "%SOLVES":
            return problem.solves()
        return None

    # To account for the LIMIT{PB_LIMIT} that adds one command correctly executed each time
    commands_correctly_treated = -1

    try:

        for command in arguments:

            if "%DIFFICULTY" in command:
                current_list = list(filter(lambda x: x.difficulty() is not None, current_list))
            
            if (">" in command) or ("<" in command) or ("=" in command):

                possible_operators = {
                    "==": lambda x, y: x == int(y),
                    ">=": lambda x, y: x >= int(y),
                    "<=": lambda x, y: x <= int(y),
                    ">": lambda x, y: x > int(y),
                    "<": lambda x, y: x < int(y)
                }

                for operator in ["==", ">=", "<=", "<", ">"]:
                    
                    if operator in command:  

                        [parameter, value] = list(command.split(operator))
                        
                        current_list = list(filter(
                            lambda pb: possible_operators[operator](weak_eval(parameter, pb), value)
                        , current_list))

                        commands_correctly_treated += 1
                        break

            if "SORT" in command:

                desc = "DESC" in command

                if "%DIFFICULTY" in command:
                    current_list = sorted(current_list, key=lambda pb: pb.difficulty(), reverse=desc)
                    commands_correctly_treated += 1
                if "%ID" in command:
                    current_list = sorted(current_list, key=lambda pb: pb.problem_id(), reverse=desc)
                    commands_correctly_treated += 1
                if "%SOLVES" in command:
                    current_list = sorted(current_list, key=lambda pb: pb.solves(), reverse=desc)
                    commands_correctly_treated += 1

            if "LIMIT" in command:
                limit = int(command.split("LIMIT")[1])
                current_list = current_list[:limit]
                commands_correctly_treated += 1
            
            if "SOLVED" in command:
                own_solves = set(m.solved_problems())
                current_list = [pb for pb in current_list if ((pb.problem_id() in own_solves) ^ ("NOT" in command))]
                commands_correctly_treated += 1

    except Exception as e:
        return await ctx.respond("An error occured. Specify `help` in the options to get informations on this command.")

    def formatter(problem: pe_api.Problem):
        return f"{problem.problem_id()}: {problem.name()} (%{problem.difficulty()}/{problem.solves()})" 

    text_list = "```" + "\n".join(list(map(formatter, current_list))) + "```"
    return await ctx.respond(f"Correctly executed {commands_correctly_treated} commands: {text_list}")


@bot.slash_command(name="privacy-settings")
@option("setting", description="What privacy you want to be associated with your account", choices=["Public", "Private"])
async def command_privacy_settings(ctx, setting: str):

    m = pe_api.Member(_discord_id = ctx.author.id)

    if not m.is_discord_linked():
        return await ctx.respond("Please first link to an account to use this command.")

    if setting == "Public" and m.private():
        m.push_privacy_to_database(False)

    if setting == "Private" and not m.private():
        m.push_privacy_to_database(True)

    return await ctx.respond(f"Your profile has successfully been switched to `{setting}`")


@bot.slash_command(name="set-favorite-problem")
@option("Problem ID", description="The problem you want to set as favorite")
@option("Reason", description="Why do you love that problem")
async def command_set_favorite_problem(ctx, problem_id: int, reason: str):

    await ctx.defer()

    regex_to_match = r'^[\w\s.,?!\']*$'
    if not re.match(regex_to_match, reason):
        return await ctx.respond(f"The reason you specified contains forbidden characters. (The regex is {regex_to_match})")

    pe_member = pe_api.Member(_discord_id = ctx.author.id)
    pe_member.push_favorite_to_database(problem_id, reason)

    return await ctx.respond(f"Your favorite problem has been set to `{problem_id}`!")


@bot.slash_command(name="remove-favorite-problem")
async def command_remove_favorite_problem(ctx):

    await ctx.defer()

    pe_member = pe_api.Member(_discord_id = ctx.author.id)
    pe_member.push_favorite_to_database(None, None)

    return await ctx.respond("Your favorite problem has been removed!")


@bot.slash_command(name="get-favorite-problems")
@option("member", description="Which member", default = None)
async def command_get_favorite_problems(ctx, member: discord.User = None):

    await ctx.defer()

    if member is not None:

        pe_member = pe_api.Member(_discord_id = member.id)
        if not pe_member.is_discord_linked():
            return await ctx.respond("This user does not have a project euler account linked!")

        favorite_problem = pe_member.favorite_problem()
        reason_favorite = pe_member.reason_favorite_problem()

        if favorite_problem is None:
            return await ctx.respond("This user has no favorite problem!")

        return await ctx.respond(f"The favorite problem of `{member.name}` is `{favorite_problem}` because: `{reason_favorite}`")

    else:

        members = pe_api.Member.members()
        favorites: Dict[int, List[Tuple[pe_api.Member, str]]] = {}

        pe_member: pe_api.Member
        for pe_member in members:

            favorite_id = pe_member.favorite_problem()
            if favorite_id is not None:

                if favorite_id not in favorites:
                    favorites[favorite_id] = []

                favorites[favorite_id].append((pe_member, pe_member.reason_favorite_problem()))

        leaderboard_data: List[Tuple[int, str]] = []
        for favorite_id in favorites:

            number_of_favorites = len(favorites[favorite_id])
            members_with_this_favorite = ", ".join(list(map(lambda x: x[0].username_option(), favorites[favorite_id])))

            leaderboard_data.append((number_of_favorites, str(favorite_id) + " - " + members_with_this_favorite))

        return await inters.leaderboard_page(ctx, leaderboard_data, True, True, 10)



@bot.slash_command(name="guess-difficulty")
@option("Problem ID", description="Which problem")
@option("Neighbors", description="Number of neighbors to use to run the KNN-algorithm", min=1, default=None)
async def command_guess_difficulty(ctx, problem_id: int, neighbors: int = 5):

    await ctx.defer()

    if problem_id < 0:
        return await ctx.respond("Problem ID is out of range, I cannot evaluate the difficulty of bonus problems.")

    if problem_id == 0 or problem_id > len(pe_api.Problem.complete_list()):
        return await ctx.respond("Problem ID is out of range.")

    problem_obj = pe_api.Problem(problem_id)
    difficulty, nearests = problem_obj.guess_difficulty_detailed(neighbors_count=neighbors)

    answer_text = f"I expect problem #{problem_id} to have difficulty {difficulty}% based on its {neighbors} nearest neighbors:"
    
    answer_text += "```"
    for problem in nearests:
        answer_text += f"{problem.problem_id()}: {problem.difficulty()}% ({problem.name()})\n"
    answer_text += "```"

    return await ctx.respond(answer_text)


@bot.slash_command(name="guess-difficulty-all")
@option("Neighbors", description="Number of neighbors to use to run the KNN-algorithm", min=1, default=None)
async def command_guess_difficulty_all(ctx, neighbors: int = 5):

    await ctx.defer()

    try:
        last_problem = pe_api.last_problem()
    except Exception as _:
        last_problem = pe_api.last_problem_database()
    
    answer_text = f"Here is the difficulty I expect for the last 10 problems:"
    answer_text += "```"

    for problem_id in range(last_problem - 9, last_problem + 1):
        problem_obj = pe_api.Problem(problem_id)
        answer_text += f"{problem_obj.problem_id()}: {problem_obj.guess_difficulty()}% ({problem_obj.name()})\n"

    answer_text += "```"
    return await ctx.respond(answer_text)


@bot.slash_command(name="challenge")
@option("Member", description="Which member")
@option("Problem ID", description="Which problem")
@option("Duration in hours", description="Which problem")
async def challenge_command(ctx, user: discord.User, problem: int, hours: int):
    
    await ctx.defer()
    
    discord_id = user.id
    to_member: pe_api.Member = pe_api.Member(_discord_id=discord_id)
    
    if not to_member.is_discord_linked():
        return await ctx.respond("This user does not have a Project Euler account linked.")
    
    from_member = pe_api.Member(_discord_id=ctx.author.id)
    if not from_member.is_discord_linked():
        return await ctx.respond("You need to link your Project Euler account first.")
    
    challenge: pe_api.Challenge = pe_api.Challenge(from_member, to_member, pe_api.now_unix(), hours, pe_api.Problem(problem))
    challenge.register_in_database()
    
    own_id = challenge.challenge_id
    
    response = f"The challenge has been registered, with ID {own_id}, the challenged member may accept it with /challenge-accept."
    response += f" They will get {hours} hours to solve the problem from the momment they accept it."
    
    return await ctx.respond(response)
    
    
@bot.slash_command(name="challenge-accept")
@option("Challenge ID", description="Which challenge you want to accept")
async def command_challenge_accept(ctx, challenge_id: int):
    
    await ctx.defer()
    
    challenge = pe_api.Challenge.get_by_id(challenge_id)    
    if challenge is None:
        return await ctx.respond("I could not find a challenge with that ID.")
    
    if not challenge.to_member.is_discord_linked():
        return await ctx.respond("I could not verify you are the person the challenge has been sent to, please verify your account is linked.")
    
    if challenge.to_member.discord_id() != str(ctx.author.id):
       return await ctx.respond("You're not the person challenged for that ID.") 
    
    challenge.accept()
    return await ctx.respond(f"You have accepted the challenge. You have {challenge.hours_duration} hours to complete it!")



"""
COMMANDS FOR EVENTS ONLY
"""

@bot.slash_command(name="event-current-problem", description="Gives you the current problem, and the remaining time you have to solve it.")
async def command_event_current_problem(ctx):

    event = pe_events.eventMonthly1()

    current_problem = event.current_problem(diff_range=0)
    seconds_left = event.last_announcement(diff_range=0) + pe_events.eventMonthly1.get_refresh_rate_easy() - int(time.time())
    hours_left = round(seconds_left / 3600, 1)

    response_text = f"The current `easy` problem to solve is [**{current_problem}**](<https://projecteuler.net/problem={current_problem}>), you have {seconds_left} seconds ({hours_left} hours) left to solve it.\n"
    
    current_problem = event.current_problem(diff_range=1)
    seconds_left = event.last_announcement(diff_range=1) + pe_events.eventMonthly1.get_refresh_rate_medium() - int(time.time())
    hours_left = round(seconds_left / 3600, 1)
    
    response_text += f"The current `medium` problem to solve is [**{current_problem}**](<https://projecteuler.net/problem={current_problem}>), you have {seconds_left} seconds ({hours_left} hours) left to solve it.\n"

    current_problem = event.current_problem(diff_range=2)
    seconds_left = event.last_announcement(diff_range=2) + pe_events.eventMonthly1.get_refresh_rate_hard() - int(time.time())
    hours_left = round(seconds_left / 3600, 1)
    
    response_text += f"The current `hard` problem to solve is [**{current_problem}**](<https://projecteuler.net/problem={current_problem}>), you have {seconds_left} seconds ({hours_left} hours) left to solve it."

    return await ctx.respond(response_text)


@bot.slash_command(name="event-current-leaderboard", description="Gives you the current leaderboard.")
async def command_event_current_leaderboard(ctx):

    await ctx.defer()

    # leaderboard_data = pe_events.eventMonthly1.leaderboard()
    leaderboard_data = pe_events.eventSmoothen.leaderboard()

    return await inters.leaderboard_page(ctx, leaderboard_data, True, True, 10)


@bot.slash_command(name="force-event-new-problem")
@option("diff_range", choices=[0, 1, 2])
async def command_force_event_new_problem(ctx, diff_range: int):

    await ctx.defer()

    perms = await sufficient_permissions(ctx.guild.get_member(ctx.author.id))

    if not perms:
        return await ctx.respond("You need to be a moderator or more to use this, sorry!", ephemeral=True)
    
    event = pe_events.eventMonthly1()

    messages_to_send = []
    for message in event.switch_to_new_problem(diff_range):
        messages_to_send.append((message, "TEST_CHANNEL"))

    await announce_messages(messages_to_send)
    return await ctx.respond("Should be done.")



""" 
FUNCTIONS MADE TO HELP, STRICTLY CONCERNING DISCORD 
"""


async def update_member_roles(m: pe_api.Member):

    if m.discord_id() == "":
        return

    guild = bot.get_guild(PROJECT_EULER_SERVER)
    member = guild.get_member(int(m.discord_id()))
    
    # If the member could not be retrieved, if they left the discord server for exemple
    if member is None:
        return

    roles = member.roles
    
    solve_index = (m.solve_count() // 100) if m.solve_count() < 1000 else 9
    
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

    async for thread_object in channel.archived_threads(private=True, limit=None):
        threads.append(thread_object)

    # console.log(threads)
    return threads


async def async_set_bot_status(choice: int, crash_message: Optional[str] = None) -> None:
    """
    Use choice=
        0: Start
        1: Normal state
        2: Not working
        3: Not working, own message
    """

    if choice == 0:
        await bot.change_presence(activity=discord.Game(name=f"{ORANGE_CIRCLE} Starting"))
    elif choice == 1:
        await bot.change_presence(activity=discord.Game(name=f"{GREEN_CIRCLE} /link to use me"))
    elif choice == 2:
        await bot.change_presence(activity=discord.Game(name=f"{RED_CIRCLE} /status for details"))
    elif choice == 3:
        await bot.change_presence(activity=discord.Game(name=f"{RED_CIRCLE} {crash_message}"))


async def sufficient_permissions(member):

    guild = member.guild

    admin_role = guild.get_role(ADMINISTRATOR_ROLE)
    mod_role = guild.get_role(MODERATOR_ROLE)

    return admin_role in member.roles or mod_role in member.roles


async def announce_messages(messages: list):
    
    possible_channels = {
        "TEST_CHANNEL": SMALL_ANNOUNCEMENTS_CHANNEL
    }

    for message, channel_description in messages:
        channel = bot.get_channel(possible_channels[channel_description])
        await channel.send(message, allowed_mentions = discord.AllowedMentions(users=False))




async def tester():
    pass


if __name__ == "__main__":
    pass
    
