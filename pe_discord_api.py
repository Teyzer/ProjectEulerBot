import asyncio
import discord

import dbqueries
import pe_api
import pe_image

client = discord.Client(intents=discord.Intents.default())

AWAIT_TIME = 60

PREFIX = "&"
CHANNELS_TO_ANNOUNCE = [944372979809255483, 1002176082713256028]
SPECIAL_CHANNELS_TO_ANNOUNCE = [944372979809255483, 1004530709760847993]

PROJECT_EULER_ROLES = [904255861503975465, 905987654083026955, 975720598741331988, 905987783892561931, 975722082996473877, 905987999949529098, 975722386559225878, 975722571473498142]


@client.event
async def on_ready():

    print('We have logged in as {0.user}'.format(client))

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

        discord_user_id = message.author.id
        database_discord_user = dbqueries.single_req("SELECT * FROM members WHERE discord_id = '{0}'".format(discord_user_id))

        if len(database_discord_user.keys()) == 0:
            return await message.channel.send("Your discord account isn't linked to any profile")

        temp_query = "UPDATE members SET discord_id = '' WHERE discord_id = '{0}'".format(discord_user_id)
        dbqueries.single_req(temp_query)

        return await message.channel.send("Your discord account was unlinked to the project euler `{0}` account".format(database_discord_user[0]["username"]))

    if command == "profile":
        #await message.channel.send("We are re-developing this feature, it isn't available at the moment!")
        if len(message.mentions) > 0:
            profile_url = message.mentions[0].avatar_url
            discord_id = message.mentions[0].id
        else:
            profile_url = message.author.avatar_url
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

    if command == "help":
        return await message.channel.send("Possible commands: link, unlink, profile, update, problem, help")

    if command == "kudos":

        discord_id = message.author.id
        if len(message.mentions) != 0:
            discord_id = message.mentions[0].id

        connection = dbqueries.open_con()
        if not pe_api.is_discord_linked(discord_id, connection):
            dbqueries.close_con(connection)
            return await message.channel.send("This user does not have a project euler account linked! Please link with &link first")

        username = dbqueries.query("SELECT username FROM members WHERE discord_id='{0}';".format(discord_id), connection)[0]["username"]
        dbqueries.close_con(connection)

        kudos, change, changes = pe_api.update_kudos(username)
        if change == 0:
            return await message.channel.send("No change for user `{0}`, still {1} kudos (this is normal if this is your first time using the command since there was no previous data)".format(username, kudos))
        else:
            k = "```" + "\n".join(list(map(lambda x: ": ".join(list(map(str, x))), changes))) + "```"
            return await message.channel.send("There was some change for user `{0}`! You gained {1} kudos on the following posts (for a total of {2} kudos):".format(username, change, kudos) + k)

    if command == "easiest":

        discord_id = message.author.id
        if len(message.mentions) != 0:
            discord_id = message.mentions[0].id

        connection = dbqueries.open_con()
        if not pe_api.is_discord_linked(discord_id, connection):
            return await message.channel.send("This user does not have a project euler account linked! Please link with &link first")

        username = dbqueries.query("SELECT username FROM members WHERE discord_id='{0}';".format(discord_id), connection)[0]["username"]
        dbqueries.close_con(connection)

        problems = pe_api.unsolved_problems(username)[:10]

        lst = "```" + "\n".join(list(map(lambda x: "Problem #{0}: '{1}' solved by {2} members".format(x[0], x[1], x[3]), problems))) + "```"
        return await message.channel.send("Here are the 10 easiest problems available to `{0}`:".format(username) + lst)
