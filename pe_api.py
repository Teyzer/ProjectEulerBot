import requests
import dbqueries
from bs4 import BeautifulSoup
import phone_api

CREDENTIALS_LOCATION = "session_cookies.txt"
BASE_URL = "https://projecteuler.net/minimal={0}"
NOT_MINIMAL_BASE_URL = "https://projecteuler.net/{0}"


def req_to_project_euler(url, login=True):

    # Read the credentials of the account on projecteuler.net
    with open(CREDENTIALS_LOCATION, "r") as file:
        lines = file.readlines()
    
    # Do some formatting
    lines[0] = lines[0].replace("\n", "")
    lines[1] = lines[1].replace("\n", "")
    
    # Then store the important credentials
    phpSessId, keepAlive = lines
    cookies = {'PHPSESSID': phpSessId, 'keep_alive': keepAlive}

    # Try to do a request, because there may be some trouble (e.g.: the website is down)
    try:

        # Do the request to the website, with the right cookies that emulate the account
        r = requests.get(url, cookies=cookies)

        if r.status_code != 200:
            
            print(r.status_code)
            print(r.text)

            # Phone API is sending a notifications to Teyzer's phone
            phone_api.bot_crashed(r.status_code)
            return None

        else:
            return r.text

    except Exception as err:
        
        phone_api.bot_crashed("Runtime Error")
        print(err)
        return None


# Called every 5 minutes
# Checks every problem, awards, of every member, and announce if there is any change
def keep_session_alive():

    # Doing the right request, to https://projecteuler.net/minimal=friends, to the minimal API
    url = BASE_URL.format("friends")
    data = req_to_project_euler(url, True)

    # If data is None, it means that the request was unsuccessful
    if data is None:
        return None

    all_solved = []

    # Go take a look for yourself of https://projecteuler.net/minimal=friends, you may understand better how is data formatted
    members = list(map(lambda x: x.split("##"), data.split("\n")))
    db_members = dbqueries.single_req("SELECT * FROM members;")
    names = list(map(lambda x: db_members[x]["username"], db_members))

    # Connection to the actual database
    connection = dbqueries.open_con()

    # Count the number of people for which nothing has changed (not really useful, mainly for tests)
    people_passed_nothing_changed = 0

    for member in members:

        # For the last line of the retrieved data, which is only a blank line
        if len(member) == 1:
            continue

        # Format member: [Account, Nickname, Country, Solves Count, Level, Binary String of solves]
        # A cell of format members is "" if the members has not set the optional parameter
        format_member = list(map(lambda x: x if x != "" else "Undefined", member))

        # By default, a member of level 0 does not even have their level displayed on the API
        format_member[4] = (format_member[4] if format_member[4] != "Undefined" else '0')
        format_member[6] = format_member[6].replace("\r", "")

        # If the members that we just retrieved is part of the database
        if format_member[0] in names:

            # Then the database member is defined, and we can retrieve it
            db_member = db_members[names.index(format_member[0])]

            # This check means: if the solves in the database is not what we just retrieved, then this means there was a solve (or more)
            if str(db_member['solved']) != format_member[4]:

                # Just for debugging
                print("Change on member", format_member[0], "on problems solved")

                previously_solved = db_member["solve_list"]
                currently_solved = format_member[6]

                # In case what was in the database does not have the same length of the current binary string (ie if there was a new problem)
                previously_solved = previously_solved + "0" * (len(currently_solved) - len(previously_solved))

                solved = []

                l = len(currently_solved)
                for i in range(1, l + 1):
                    # If the current character is not the same as the previous. We take as true that it's always from 0 to 1 (i.e. there is no "unsolved")
                    if previously_solved[i - 1] != currently_solved[i - 1]:
                        
                        # Need to know the position of ths solver
                        problem_data = problem_def(i)
                        solver_position = problem_data[3]

                        # Insert the solve in the database
                        temp_query = "INSERT INTO solves (member, problem, solve_date, position) VALUES ('{0}', {1}, NOW(), {2})"
                        temp_query = temp_query.format(format_member[0], i, solver_position)
                        dbqueries.query(temp_query, connection)

                        # Add it in the solves array
                        solved.append(i)

                # Add everything in a nice array, the subarray here is of the form [Account, Solves Count, Discord ID, Level]
                all_solved.append([format_member[0], solved, db_member['discord_id'], format_member[4]])

                # Again for debug
                print("{0} solved the problem {1}".format(format_member[0], ",".join(list(map(str, solved)))))

                # We send the new data to the database
                temp_query = "UPDATE members SET solved={0}, solve_list='{1}' WHERE username = '{2}';"
                temp_query = temp_query.format(format_member[4], format_member[6], format_member[0])
                dbqueries.query(temp_query, connection)

            else:
                # Only for debugging
                people_passed_nothing_changed += 1
        
        # Else, the member was not in the databse, meaning we have to get his profile
        else:

            # Need the awards, that are not retrieved by default with minimal=friends    
            awards = get_awards(format_member[0])

            # Then add all of this in the database
            temp_query = "INSERT INTO members (username, nickname, country, language, solved, solve_list, discord_id, awards, awards_list) VALUES ('{0}', '{1}', '{2}', '{3}', {4}, '{5}', '', {6}, '{7}')"
            temp_query = temp_query.format(format_member[0], format_member[1], format_member[2], format_member[3], format_member[4], format_member[6], awards[0], awards[1])
            dbqueries.query(temp_query, connection)
            
            # Again some debugging
            print("Added", format_member[0])

    print("End of check, passed {0} people".format(people_passed_nothing_changed))

    dbqueries.close_con(connection)
    return all_solved


# Return array of the form ['n', 'Problem title', Unix Timestamp of publish, 'nb of solves', '0']
# Careful as all values in the array are string, not ints
def problem_def(n):
    data = req_to_project_euler(BASE_URL.format("problems"))
    lines = data.split("\n")
    pb = lines[n].replace("\r", "")
    specs = pb.split("##")
    return specs


# Return last problem available, including the ones in the recent tab
def last_problem():
    data = req_to_project_euler(BASE_URL.format("problems"))
    return len(data.split("\n")) - 2


# return an array of the form [nb_posts, nb_kudos, 2nd_array]
# with 2nd_array of the form [[index_post1, kudos_post1], [index_post2, kudos_post2], ...]
def get_kudos(username):

    url = NOT_MINIMAL_BASE_URL.format("progress={0};show=posts".format(username))
    data = req_to_project_euler(url)
    soup = BeautifulSoup(data, 'html.parser')
    div = soup.find(id='posts_made_section')

    post_made, kudos_earned = div.find_all("h3")[0].text.split(" / ")
    post_made = int(post_made.split(" ")[2])
    kudos_earned = int(kudos_earned.split(" ")[2])

    posts = [list(map(lambda x: int(x.text), post.find_all("span"))) for post in div.find_all(class_="post_made_box")]
    return [post_made, kudos_earned, posts]


# Return an array of the form [total_kudos, total_change, change_list]
# with change_list of the form [[post1, change1], [post2, change2], ...]
def update_kudos(username):

    posts_made, kudos_earned, posts_list = get_kudos(username)

    connection = dbqueries.open_con()
    temp_query = "SELECT * FROM pe_posts WHERE username = '{0}';".format(username)
    data = dbqueries.query(temp_query, connection)

    posts_txt = "|".join(["n".join(map(str, p)) for p in posts_list])

    changes = []
    total_change = 0

    if len(data.keys()) == 0:
        temp_query = "INSERT INTO pe_posts (username, posts_number, kudos, posts_list) VALUES ('{0}', {1}, {2}, '{3}');".format(username, posts_made, kudos_earned, posts_txt)
        dbqueries.query(temp_query, connection)
    else:
        previous = data[0]
        previous_posts = list(map(lambda x: list(map(int, x.split("n"))), previous["posts_list"].split("|")))
        if previous["kudos"] != kudos_earned:
            total_change = kudos_earned - previous["kudos"]
            for post in posts_list:
                for previous_post in previous_posts:
                    if post[0] == previous_post[0]:
                        if post[1] != previous_post[1]:
                            changes.append([post[0], post[1] - previous_post[1]])
                        break
        if previous["posts_number"] != posts_made or previous["kudos"] != kudos_earned:
            temp_query = "UPDATE pe_posts SET posts_number='{0}', kudos='{1}', posts_list='{2}' WHERE username='{3}'".format(posts_made, kudos_earned, posts_txt, username)
            dbqueries.query(temp_query, connection)

    dbqueries.close_con(connection)
    return [kudos_earned, total_change, changes]


# Returns True or False, given a discord id
def is_discord_linked(discord_id, connection=None):

    if connection is None:
        data = dbqueries.single_req("SELECT * FROM members WHERE discord_id='{0}';".format(discord_id))
    else:
        data = dbqueries.query("SELECT * FROM members WHERE discord_id='{0}';".format(discord_id), connection)
    return len(data.keys()) == 1


# Returns a double array of the form [problem_1, problem_2, problem_3, ...]
# with problem_i of the form ['problem_nb', 'problem_title', 'unix timestamp of publish', 'solved by', '0']
# careful again, only strings in the arrays
def unsolved_problems(username):

    url = BASE_URL.format("friends")
    data = req_to_project_euler(url, True)
    if data is None:
        pass

    members = list(map(lambda x: x.split("##"), data.split("\n")))

    usernames = list(map(lambda x: x[0], members))
    if username not in usernames:
        return None

    member_solves = members[usernames.index(username)][6]

    data = req_to_project_euler(BASE_URL.format("problems"))
    problems = list(map(lambda x: x.replace("\r", ""), data.split("\n")))

    unsolved = []

    for index, solved in enumerate(list(member_solves)):
        if solved == "0":
            unsolved.append(problems[index + 1].split("##"))

    unsolved = sorted(unsolved, key=lambda x: int(x[3]), reverse=True)
    return unsolved


# returns a list of the form [profile1, profile2, profile3, ...]
# with profile1 of the form [username, nickname, country, language, solved, level, list of solve]
# and list of solve being of the form 1111100010000111 and so on
# Note that all values are strings
def get_all_profiles_on_project_euler():

    url = BASE_URL.format("friends")
    data = req_to_project_euler(url, True)
    if data is None:
        pass

    members = list(map(lambda x: x.split("##"), data.split("\n")))
    return members[:-1]


# returns a list of the form [username1, username2, username3, ...]
def get_all_usernames_on_project_euler():

    profiles = get_all_profiles_on_project_euler()
    return list(map(lambda x: x[0], profiles))


# returns a list of the form [username1, username2, username3, ...]
def get_all_members_who_solved(problem):

    solvers = []

    profiles = get_all_profiles_on_project_euler()
    for profile in profiles:
        #print(profile)
        if profile[6][problem - 1] == "1":
            solvers.append(profile[0])

    return solvers


# return a binary string like 111110001100... with every 1 marking a solve
def problems_of_member(username):

    url = BASE_URL.format("friends")
    data = req_to_project_euler(url, True)
    if data is None:
        pass

    members = list(map(lambda x: x.split("##"), data.split("\n")))

    usernames = list(map(lambda x: x[0], members))
    if username not in usernames:
        return None

    member_solves = members[usernames.index(username)][6]

    print(member_solves)


# returns an array like [32, '1111110111111111111001011101101011|11111']
# with first int being the number of awards, and then a binary list, splitted with | for problem and forum awards
def get_awards(username):

    url = NOT_MINIMAL_BASE_URL.format("progress={0};show=awards".format(username))
    data = req_to_project_euler(url)
    soup = BeautifulSoup(data, 'html.parser')

    div1 = soup.find(id="problem_solving_awards_section")
    div2 = soup.find(id="forum_based_awards_section")

    problem_awards = div1.find_all(class_="award_box")
    solves_problem = [1 if len(problem.find_all(class_="smaller green strong")) == 1 else 0 for problem in problem_awards]

    forum_awards = div2.find_all(class_="award_box")
    solves_forum = [1 if len(problem.find_all(class_="smaller green strong")) == 1 else 0 for problem in forum_awards]

    return [sum(solves_problem) + sum(solves_forum), "".join(list(map(str, solves_problem)))+"|"+"".join(list(map(str, solves_forum)))]


# returns a list of the form [awards, changes]
# with each changes of the form [index_award_1, index_award_2, ...]
def update_awards(username):

    connection = dbqueries.open_con()
    temp_query = "SELECT username, awards, awards_list FROM members WHERE username='{0}';".format(username)
    data = dbqueries.query(temp_query, connection)[0]

    current_data = get_awards(username)

    changes = []

    first_len = len(current_data[1].split("|")[0])
    second_len = len(current_data[1].split("|")[1])

    if data["awards_list"] != current_data[1]:
        for i in range(first_len):
            if current_data[1][i] == "1" and data["awards_list"][i] == "0":
                changes.append(i)
        for j in range(first_len + 1, first_len + 1 + second_len):
            if current_data[1][j] == "1" and data["awards_list"][j] == "0":
                changes.append(j-1)

    temp_query = "UPDATE members SET awards={0}, awards_list='{1}' WHERE username='{2}';".format(current_data[0], current_data[1], username)
    dbqueries.query(temp_query, connection)
    dbqueries.close_con(connection)

    return [current_data[0], changes]


# returns a list of all the usernames in the database
def all_members_in_database():
    data = dbqueries.single_req("SELECT username FROM members;")
    return list(map(lambda x: x["username"], [data[k] for k in data.keys()]))


# return a list of all the names of the awards
def get_awards_specs():
    url = NOT_MINIMAL_BASE_URL.format("progress;show=awards")
    data = req_to_project_euler(url)
    soup = BeautifulSoup(data, 'html.parser')

    all_awards = []

    d_problems = soup.find(id="problem_solving_awards_section").find_all(class_="tooltip inner_box")
    all_awards.append([problem.find_all(class_="strong")[0].text for problem in d_problems])

    d_problems = soup.find(id="forum_based_awards_section").find_all(class_="tooltip inner_box")
    all_awards.append([problem.find_all(class_="strong")[0].text for problem in d_problems])

    return all_awards
