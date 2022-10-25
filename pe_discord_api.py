import asyncio
import time

from math import *
import json

import dbqueries
import pe_api
import pe_image
import interactions_discord as inters

<<<<<<< Updated upstream
#temp_intents = discord.Intents(messages=True, guilds=True, members=True)
temp_intents = discord.Intents().all()
#temp_partials = discord.Partials(message=True, channel=True)
=======
import discord
from discord import option

TEST_SERVER = 943488228084813864
PROJECT_EULER_SERVER = 903915097804652595
GUILD_IDS = [PROJECT_EULER_SERVER]


intents = discord.Intents.all()
bot = discord.Bot(guild_ids=GUILD_IDS, intents=intents)
>>>>>>> Stashed changes

client = discord.Client(intents=temp_intents)

AWAIT_TIME = 60

PREFIX = "&"
CHANNELS_TO_ANNOUNCE = [944372979809255483, 1002176082713256028]
SPECIAL_CHANNELS_TO_ANNOUNCE = [944372979809255483, 1004530709760847993]

<<<<<<< Updated upstream
PROJECT_EULER_ROLES = [904255861503975465, 905987654083026955, 975720598741331988, 905987783892561931, 975722082996473877, 905987999949529098, 975722386559225878, 975722571473498142]
=======
>>>>>>> Stashed changes


@client.event
async def on_ready():

<<<<<<< Updated upstream
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game(name="github.com/Teyzer/ProjectEulerBot"))
=======
    print('We have logged in as {0.user}'.format(bot))
    await bot.change_presence(activity=discord.Game(name="/help for help"))
>>>>>>> Stashed changes

    repeats = 0

    while True:

        await asyncio.sleep(AWAIT_TIME)

        print(repeats, end="| ")
        solves = pe_api.keep_session_alive()
        repeats += 1

        if solves is None:
            continue

        if len(solves) == 0:
            continue

        for solve in solves:
            for problem in solve[1]:
                data_on_problem = pe_api.problem_def(problem)
                for channel_id in CHANNELS_TO_ANNOUNCE:
                    channel = client.get_channel(channel_id)
                    if solve[2] == "":
                        sending_message = "`{0}` solved the problem #{1}: '{2}' which has been solved by {3} people, well done! <https://projecteuler.net/problem={1}>"
                        sending_message = sending_message.format(solve[0], data_on_problem[0], data_on_problem[1], data_on_problem[3])
                    else:
                        sending_message = "`{0}` (<@{4}>) solved the problem #{1}: '{2}' which has been solved by {3} people, well done! <https://projecteuler.net/problem={1}>"
                        sending_message = sending_message.format(solve[0], data_on_problem[0], data_on_problem[1], data_on_problem[3], solve[2])
                    await channel.send(sending_message)
            if int(solve[3]) % 25 == 0:
                for channel_id in SPECIAL_CHANNELS_TO_ANNOUNCE:
                    channel = client.get_channel(channel_id)
                    if solve[2] == "":
                        sending_message = "`{0}` has just reached level {1}, congratulations!"
                        sending_message = sending_message.format(solve[0], int(solve[3]) // 25)
                    else:
                        sending_message = "`{0}` (<@{2}>) has just reached level {1}, congratulations!"
                        sending_message = sending_message.format(solve[0], int(solve[3]) // 25, solve[2])
                    await channel.send(sending_message)

        solvers = list(set([solve[0] for solve in solves]))

        awards = pe_api.get_awards_specs()
        awards = awards[0] + awards[1]

        for solver in solvers:
            awards_user = pe_api.update_awards(solver)
            if len(awards_user[1]) != 0:
                for award in [awards[k] for k in awards_user[1]]:
                    for channel_id in SPECIAL_CHANNELS_TO_ANNOUNCE:
                        channel = client.get_channel(channel_id)
                        await channel.send("`{0}` got the award '{1}', congratulations!".format(solver, award))





@client.event
async def on_message(message):

    if message.author == client.user:
        return

    if not message.content.startswith(PREFIX):
        return

    commands = message.content[1:].split(" ")
    command = commands[0]

    arguments_len = len(commands) - 1
    print("Command '{0}' by '{1}'".format(command, message.author.name))

    if command == "link":

        if arguments_len < 1:
            return await message.channel.send("Please specify a Project Euler username to link with")

        discord_user_id = message.author.id
        database_discord_user = dbqueries.single_req("SELECT * FROM members WHERE discord_id = '{0}'".format(discord_user_id))
        if len(database_discord_user.keys()) != 0:
            sentence = "Your discord account is already linked to the account `{0}`, type &unlink to unlink it".format(database_discord_user[0]["username"])
            return await message.channel.send(sentence)

        user = dbqueries.single_req("SELECT * FROM members WHERE username = '{0}'".format(commands[1]))
        if len(user.keys()) == 0:
            return await message.channel.send("This username is not in my friend list. Add the bot account on project euler first: 1910895_2C6CP6OuYKOwNlTdL8A5fXZ0p5Y41CZc\nIf you think this is a mistake, type &update")

        user = user[0]
        if str(user["discord_id"]) != "":
            return await message.channel.send("This account is already linked to <@{0}>".format(user["discord_id"]))

        temp_query = "UPDATE members SET discord_id = '{0}' WHERE username = '{1}'".format(message.author.id, commands[1])
        dbqueries.single_req(temp_query)

        return await message.channel.send("Your account was linked to `{0}`!".format(commands[1]))

    if command == "unlink":

<<<<<<< Updated upstream
        discord_user_id = message.author.id
        database_discord_user = dbqueries.single_req("SELECT * FROM members WHERE discord_id = '{0}'".format(discord_user_id))

        if len(database_discord_user.keys()) == 0:
            return await message.channel.send("Your discord account isn't linked to any profile")
=======
    discord_user_id = ctx.author.id
    database_discord_user = dbqueries.single_req("SELECT * FROM members WHERE discord_id = '{0}'".format(discord_user_id))
    if len(database_discord_user.keys()) != 0:
        sentence = "Your discord account is already linked to the account `{0}`, type /unlink to unlink it".format(database_discord_user[0]["username"])
        return await ctx.respond(sentence)

    user = dbqueries.single_req("SELECT * FROM members WHERE username = '{0}'".format(username))
    if len(user.keys()) == 0:
        return await ctx.respond("This username is not in my friend list. Add the bot account on project euler first: 1910895_2C6CP6OuYKOwNlTdL8A5fXZ0p5Y41CZc\nIf you think this is a mistake, type /update")
>>>>>>> Stashed changes

        temp_query = "UPDATE members SET discord_id = '' WHERE discord_id = '{0}'".format(discord_user_id)
        dbqueries.single_req(temp_query)

        return await message.channel.send("Your discord account was unlinked to the project euler `{0}` account".format(database_discord_user[0]["username"]))

    if command == "profile":
        #await message.channel.send("We are re-developing this feature, it isn't available at the moment!")

        #print(json.dumps(message.mentions))
        if len(message.mentions) > 0:
            #print("none")
            profile_url = message.mentions[0].avatar.url
            discord_id = message.mentions[0].id
        else:
            #print(json.dumps(discord.Users().get(message.author.id)))
            profile_url = message.author.avatar.url
            discord_id = message.author.id


        connection = dbqueries.open_con()
        temp_query = "SELECT * FROM members WHERE discord_id = '{0}'".format(discord_id)
        data = dbqueries.query(temp_query, connection)

        if len(data.keys()) == 0:
            dbqueries.close_con(connection)
            return await message.channel.send("This user is not linked! Please link your account first")

        data = data[0]

        all_data = dbqueries.query("SELECT * FROM members ORDER BY solved DESC;", connection)
        total = len(all_data.keys())
        rank = total

        for k in all_data.keys():
            if str(all_data[k]["discord_id"]) == str(discord_id):
                rank = k+1

        return await message.channel.send(file = discord.File(pe_image.generate_profile_image(data["username"], data["solved"], len(data["solve_list"]), rank, total, sum(int(x) for x in data["solve_list"][-10:]), profile_url)))

    if command == "update":
        pe_api.keep_session_alive()
        return await message.channel.send("The data was updated successfully!")

    if command == "problem":
        return await message.channel.send("This feature is being rebuilt, it doesn't work currently, sorry \\:)")

<<<<<<< Updated upstream
    if command == "help":
        return await message.channel.send("Possible commands: link, unlink, profile, update, problem, help")
=======
    connection = dbqueries.open_con()
    if not pe_api.is_discord_linked(discord_id, connection):
        dbqueries.close_con(connection)
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")
>>>>>>> Stashed changes

    if command == "kudos":

        discord_id = message.author.id
        if len(message.mentions) != 0:
            discord_id = message.mentions[0].id

        connection = dbqueries.open_con()
        if not pe_api.is_discord_linked(discord_id, connection):
            dbqueries.close_con(connection)
            return await message.channel.send("This user does not have a project euler account linked! Please link with &link first")

<<<<<<< Updated upstream
        username = dbqueries.query("SELECT username FROM members WHERE discord_id='{0}';".format(discord_id), connection)[0]["username"]
        dbqueries.close_con(connection)
=======
@bot.slash_command(name="easiest", description="Find the easiest problems you haven't solved yet")
@option("member", description="The member you want you want to see the next possible solves", default=None)
@option("method", description="The method used", choices=["By number of solves", "By order of publication", "By ratio of solves per time unit"], default="By ratio of solves per time unit")
@option("display_nb", description="The number of problems you want to be displayed", min_value=1, max_value=25, default=10)
async def command_easiest(ctx, member: discord.User, method: str, display_nb: int):
    
    discord_id = ctx.author.id
    if member is not None:
        discord_id = member.id
>>>>>>> Stashed changes

        kudos, change, changes = pe_api.update_kudos(username)
        if change == 0:
            return await message.channel.send("No change for user `{0}`, still {1} kudos (this is normal if this is your first time using the command since there was no previous data)".format(username, kudos))
        else:
            k = "```" + "\n".join(list(map(lambda x: ": ".join(list(map(str, x))), changes))) + "```"
            return await message.channel.send("There was some change for user `{0}`! You gained {1} kudos on the following posts (for a total of {2} kudos):".format(username, change, kudos) + k)

<<<<<<< Updated upstream
    if command == "easiest":
=======
    connection = dbqueries.open_con()
    if not pe_api.is_discord_linked(discord_id, connection):
        return await ctx.respond("This user does not have a project euler account linked! Please link with /link first")
>>>>>>> Stashed changes

        discord_id = message.author.id
        if len(message.mentions) != 0:
            discord_id = message.mentions[0].id

        connection = dbqueries.open_con()
        if not pe_api.is_discord_linked(discord_id, connection):
            return await message.channel.send("This user does not have a project euler account linked! Please link with &link first")

        username = dbqueries.query("SELECT username FROM members WHERE discord_id='{0}';".format(discord_id), connection)[0]["username"]
        dbqueries.close_con(connection)

        method = "per_solve"
        allowed_methods = ["per_solve", "per_order", "per_ratio"]
        if len(commands) >= 2 and commands[1] in allowed_methods:
            method = commands[1]

        list_problems = pe_api.unsolved_problems(username)

        if method == "per_solve":
            problems = sorted(list_problems, key=lambda x: int(x[3]), reverse=True)
        elif method == "per_order":
            problems = sorted(list_problems, key=lambda x: int(x[0]))
        elif method == "per_ratio":
            problems = sorted(list_problems, key=lambda x: int(x[3])/(int(time.time()) + 31536000 - int(x[2])), reverse=True)

<<<<<<< Updated upstream
        max_problems = 25
        number_of_problems = 10
=======
@bot.slash_command(name="roles-languages", description="Select the languages roles you want to be displayed on your profile")
async def command_roles_languages(ctx):

    view = inters.DropdownView(bot, ctx.author)

    # Sending a message containing our View
    await ctx.respond("Choose your main languages (by alphabetic order):", view=view, ephemeral=True)

>>>>>>> Stashed changes

        if len(commands) >= 3:
            try:
                x = int(commands[2])
                number_of_problems = x if x <= max_problems else max_problems
            except Exception as e:
                pass

        problems = problems[:number_of_problems]

        lst = "```" + "\n".join(list(map(lambda x: "Problem #{0}: '{1}' solved by {2} members".format(x[0], x[1], x[3]), problems))) + "```"
        return await message.channel.send("Here are the {1} easiest problems available to `{0}`:".format(username, number_of_problems) + lst)
