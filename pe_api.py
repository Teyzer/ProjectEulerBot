import datetime

import requests
import dbqueries
from bs4 import BeautifulSoup
import phone_api

CREDENTIALS_LOCATION = "session_cookies.txt"
BASE_URL = "https://projecteuler.net/minimal={0}"
NOT_MINIMAL_BASE_URL = "https://projecteuler.net/{0}"


def req_to_project_euler(url, login=True):

    with open(CREDENTIALS_LOCATION, "r") as file:
        lines = file.readlines()
    lines[0] = lines[0].replace("\n", "")
    lines[1] = lines[1].replace("\n", "")
    phpSessId, keepAlive = lines
    cookies = {'PHPSESSID': phpSessId, 'keep_alive': keepAlive}

    try:
        r = requests.get(url, cookies=cookies)

        if r.status_code != 200:
            print(r.status_code)
            print(r.text)
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

    url = BASE_URL.format("friends")
    data = req_to_project_euler(url, True)

    if data is None:
        return None

    all_solved = []

    members = list(map(lambda x: x.split("##"), data.split("\n")))
    db_members = dbqueries.single_req("SELECT * FROM members;")
    names = list(map(lambda x: db_members[x]["username"], db_members))

    connection = dbqueries.open_con()

    people_passed_nothing_changed = 0

    for member in members:

        if len(member) == 1:
            continue

        format_member = list(map(lambda x: x if x != "" else "Undefined", member))
        format_member[4] = (format_member[4] if format_member[4] != "Undefined" else '0')
        format_member[6] = format_member[6].replace("\r", "")

        if format_member[0] in names:
            db_member = db_members[names.index(format_member[0])]
            if str(db_member['solved']) != format_member[4]:

                print("Change on member", format_member[0], "on problems solved")

                previously_solved = db_member["solve_list"]
                currently_solved = format_member[6]

                previously_solved = previously_solved + "0" * (len(currently_solved) - len(previously_solved))

                solved = []

                l = len(currently_solved)
                for i in range(1, l+1):
                    if previously_solved[i - 1] != currently_solved[i - 1]:
                        if is_contributor(db_member, i):
                            add_contribution(db_member, i)
                        solved.append(i)

                all_solved.append([format_member[0], solved, db_member['discord_id'], format_member[4]])

                print("{0} solved the problem {1}".format(format_member[0], ",".join(list(map(str, solved)))))

                temp_query = "UPDATE members SET solved={0}, solve_list='{1}' WHERE username = '{2}';"
                temp_query = temp_query.format(format_member[4], format_member[6], format_member[0])
                dbqueries.query(temp_query, connection)

            else:
                people_passed_nothing_changed += 1
        else:

            awards = get_awards(format_member[0])

            temp_query = "INSERT INTO members (username, nickname, country, language, solved, solve_list, discord_id, awards, awards_list) VALUES ('{0}', '{1}', '{2}', '{3}', {4}, '{5}', '', {6}, '{7}')"
            temp_query = temp_query.format(format_member[0], format_member[1], format_member[2], format_member[3], format_member[4], format_member[6], awards[0], awards[1])
            dbqueries.query(temp_query, connection)
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


# Returns True or False
def is_discord_linked(discord_id, connection=None):

    if connection is None:
        data = dbqueries.single_req("SELECT * FROM members WHERE discord_id='{0}';".format(discord_id))
    else:
        data = dbqueries.query("SELECT * FROM members WHERE discord_id='{0}';".format(discord_id), connection)
    return len(data.keys()) >= 1


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


# Our heuristic for checking if a user is a contributor to a problem is:
# Get the time the user solved a problem from their recent solves history,
# is this less than the most recent solver in the top 100 and are they
# absent from the top solvers list?
def is_contributor(username, problem):
    fastest_solvers = get_fastest_solvers(problem)
    in_solvers = username in (name for name, _ in fastest_solvers)
    if in_solvers: return False
    # Check if user has solved faster than last solver in top 100
    solved_at = get_user_recent_problems(username).get(problem, datetime.datetime.max)
    return solved_at < fastest_solvers[-1][1]


# Unfortunately, the history page for friends only shows recent problems solved
def get_user_recent_problems(username):
    """Return a dictionary of recent problems mapped to datetimes for a given user."""
    url = NOT_MINIMAL_BASE_URL.format(f"progress={username};show=history")
    data = req_to_project_euler(url, True)
    return get_user_recent_problems_from_data(data)


def get_user_recent_problems_from_data(data):
    soup = BeautifulSoup(data, "html.parser")
    problems = soup.find_all("tr")
    problem_dict = {}
    for problem in problems:
        n, _, date_info = problem.children
        fst_child = next(date_info.children)
        datetime_str = fst_child if isinstance(fst_child, str) \
            else next(fst_child.children)
        # 15 Jul 22 (07:34.59)
        dt = datetime.datetime.strptime(datetime_str, "%d %b %y (%H:%M.%S)")
        problem_dict[int(n.text.strip())] = dt
    return problem_dict


def get_fastest_solvers(problem):
    url = NOT_MINIMAL_BASE_URL.format(f"fastest={problem}")
    data = req_to_project_euler(url, True)
    return get_fastest_solvers_from_data(problem, data)


def get_fastest_solvers_from_data(problem, data):
    unix_ts = int(problem_def(problem)[2])
    dt = datetime.datetime.utcfromtimestamp(unix_ts)
    soup = BeautifulSoup(data, "html.parser")
    div = soup.find(id="statistics_fastest_solvers_page")

    _, *solves = div.find("table").find_all("tr")
    solver_info = []
    for solve in solves:
        columns = solve.find_all("td")
        position, username, loc, lang, time = (td.text for td in columns)
        if not isinstance(next(columns[1].children), str):  # it's an alias
            username = next(columns[1].children).attrs["title"]
        # seconds, minutes, hours, days, weeks, years
        times = [1, 60, 60*60, 60*60*24, 60*60*24*7, 60*60*24*7*52]
        total = 0
        for raw_time, multiplier in zip(reversed(time.split(", ")), times):
            time, *_ = raw_time.partition(" ")
            total += int(time)*multiplier
        solver_info.append((username, dt + datetime.timedelta(seconds=total)))
    return solver_info 


def add_contribution(username, problem, conn):
    stmt = (
        "INSERT INTO problem_contributions (username, problem)"
        "VALUES (%s, %s)"
        "ON DUPLICATE KEY UPDATE username=username"
    )
    dbqueries.query(stmt, conn, (username, problem))


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
