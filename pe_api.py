import requests
from bs4 import BeautifulSoup

import datetime
import pytz

import dbqueries

import phone_api

from rich.console import Console
from rich import inspect



TOTAL_REQUESTS = 0
SESSION_REQUESTS = 0

console = Console()

CREDENTIALS_LOCATION = "session_cookies.txt"
BASE_URL = "https://projecteuler.net/minimal={0}"
NOT_MINIMAL_BASE_URL = "https://projecteuler.net/{0}"


class ProjectEulerRequest:
    
    def __init__(self, target_url: str, need_login: bool = True):
        
        global TOTAL_REQUESTS, SESSION_REQUESTS
        
        TOTAL_REQUESTS += 1
        SESSION_REQUESTS += 1
        
        with open(CREDENTIALS_LOCATION, "r") as file:
            lines = file.readlines()
        
        # Do some formatting
        for i in range(2):
            lines[i] = lines[i].replace("\n", "")
        
        # Then store the important credentials
        phpSessId, keepAlive = lines
        cookies = {'PHPSESSID': phpSessId, 'keep_alive': keepAlive}
        
        try:
            # Do the request to the website, with the right cookies that emulate the account
            r = requests.get(target_url, cookies=cookies)
            self.status = int(r.status_code)
            
            if r.status_code != 200:
                # Phone API is sending a notifications to Teyzer's phone
                phone_api.bot_crashed(r.status_code)
                self.response = None
            else:
                self.response = r.text

        except Exception as err:
            phone_api.bot_crashed("Runtime Error")
            self.status = None
            self.response = "Failed"
        

class PE_Problem:
    
    def __init__(self, problem_id: int, name: str = None, unix_publication: int = None, solves: int = None, 
                 solves_in_discord: int = None, difficulty_rating: int = None):
        self.name = name
        self.problem_id = problem_id
        self.unix_publication = unix_publication
        self.solves = solves
        self.solves_in_discord = solves_in_discord
        self.difficulty_rating = difficulty_rating
        
    def __str__(self) -> str:
        return str([self.problem_id, self.name, self.unix_publication, self.solves, self.solves_in_discord, self.difficulty_rating])
    
    def __repr__(self) -> str:
        return self.__str__()

    @staticmethod
    def complete_list():
        
        res_list = []
        
        API_data = ProjectEulerRequest("https://projecteuler.net/minimal=problems", False)
        
        rows = API_data.response.split("\n")
        timestamps = [int(x.split("##")[2]) for x in rows[1:-1]]
        
        UX_data = ProjectEulerRequest("https://projecteuler.net/progress", True)
        soup = BeautifulSoup(UX_data.response, 'html.parser')
        div = soup.find_all("span", class_='tooltiptext_narrow')
        
        for element in div:
            
            properties = list(map(
                lambda x: x.text, 
                element.find_all("div")
            ))
            
            if len(properties) == 0:
                continue
            
            problem_id = int(properties[0].split()[1])
            solvers = int(properties[1].split()[2])
            
            if len(properties) == 3:    
                difficulty = None
                title = properties[2].replace("\"", "")
            elif len(properties) == 4:
                difficulty = int(properties[2].split(": ")[1].split("%")[0])
                title = properties[3].replace("\"", "")
            
            pb = PE_Problem(problem_id, name=title, unix_publication=timestamps[problem_id - 1], solves=solvers, difficulty_rating=difficulty)
            res_list.append(pb)
                
        return res_list
        
        
class Member:
    
    
    def __init__(self, _username: str = None, _nickname: str = None, _country: str = None, _language: str = None,
                 _solve_count: int = None, _level: int = None, _solve_array: list = None, _discord_id: str = None, 
                 _kudo_count: int = None, _kudo_array: list = None, _database_solve_count: int = None, _database_solve_array: int = None, 
                 _award_count: int = None, _award_array: list = None, _database_award_count: int = None, 
                 _database_award_array: list = None, _database_kudo_count: int = None, _database_kudo_array: int = None):
        
        self._username = _username
        self._nickname = _nickname
        self._country = _country
        self._language = _language
        self._level = _level
        
        self._discord_id = None if _discord_id is None else str(_discord_id)
        
        self._pe_solve_count = _solve_count
        self._pe_solve_array = _solve_array
        self._pe_award_count = _award_count
        self._pe_award_array = _award_array
        self._pe_kudo_count = _kudo_count
        self._pe_kudo_array = _kudo_array
        
        self._database_solve_count = _database_solve_count
        self._database_solve_array = _database_solve_array
        self._database_award_count = _database_award_count
        self._database_award_array = _database_award_array
        self._database_kudo_count = _database_kudo_count
        self._database_kudo_array = _database_kudo_array
        
    
    def __str__(self):
        return f"{self._username}/{self._discord_id}/{self._pe_solve_count}/{self._database_solve_count}"
        

    def __repr__(self):
        return self.__str__()

        
    def update_from_friend_list(self, friend_page: ProjectEulerRequest = None):
        
        if friend_page is None:
            friend_page = ProjectEulerRequest(BASE_URL.format("friends"))
        
        if friend_page.status != 200:
            raise Exception("Request failed")
        
        format_func = lambda x: x.replace("C###", "Csharp##").replace("F###", "Fsharp##").split("##")
        text_response = list(map(format_func, friend_page.response.split("\n")))
        
        target_member = None
        for element in text_response:
            if element[0] == self.username():
                target_member = element
                break

        if target_member is None:
            raise Exception("Member not found in friend list")
        
        undef_func = lambda x, int_type: \
            (0 if int_type else "Undefined") if x == "" else (int(x) if int_type else x)
        
        self._nickname = undef_func(target_member[1], False)
        self._country = undef_func(target_member[2], False)
        self._language = undef_func(target_member[3], False)
        self._pe_solve_count = undef_func(target_member[4], True)
        self._level = undef_func(target_member[5], True)
        self._pe_solve_array = [
            c == "1" for c in 
            filter(lambda x: x in "01", target_member[6])
        ]

    
    def update_from_award_list(self):
        
        request_url = NOT_MINIMAL_BASE_URL.format(f"progress={self.username()};show=awards")
        kudo_page = ProjectEulerRequest(request_url)
        
        if kudo_page.status != 200:
            raise Exception("Request failed")
        
        soup = BeautifulSoup(kudo_page.response, 'html.parser')

        div1 = soup.find(id="problem_solving_awards_section")
        div2 = soup.find(id="forum_based_awards_section")

        problem_awards = div1.find_all(class_="award_box")
        solves_problem = [1 if len(problem.find_all(class_="smaller green strong")) == 1 else 0 for problem in problem_awards]

        forum_awards = div2.find_all(class_="award_box")
        solves_forum = [1 if len(problem.find_all(class_="smaller green strong")) == 1 else 0 for problem in forum_awards]
        
        self._pe_award_count = sum(solves_problem) + sum(solves_forum)
        self._pe_award_array = list(map(
            lambda x: [str(c) == "1" for c in x],
            [solves_problem, solves_forum]
        ))
        
        
    def update_from_post_page(self):
        
        request_url = NOT_MINIMAL_BASE_URL.format(f"progress={self.username()};show=posts")
        post_page = ProjectEulerRequest(request_url)
        
        if post_page.status != 200:
            raise Exception("Request failed")

        soup = BeautifulSoup(post_page.response, 'html.parser')
        div = soup.find(id='posts_made_section')

        post_made, kudos_earned = div.find_all("h3")[0].text.split(" / ")
        post_made = int(post_made.split(" ")[2])
        kudos_earned = int(kudos_earned.split(" ")[2])

        posts = [
            list(map(
                lambda x: int(x.text), 
                post.find_all("span")
            )) for post in div.find_all(class_="post_made_box")
        ]
        
        self._pe_kudo_count = sum(list(map(lambda x: x[1], posts)))
        self._pe_kudo_array = posts

    
    
    def update_from_database(self, connection = None, data = None):
        
        key_id, value_id = self.identity()
        check_function = lambda x: 0 if x is None else \
            sum([1 if str(x[k][key_id]) == str(value_id) else 0 for k in x.keys()])
        
        while check_function(data) == 0:
            
            if data is not None:
                self.update_from_friend_list()
                self.push_basics_to_database()
            
            tquery = "SELECT * FROM members;"
            data = dbqueries.option_query(tquery, connection)
        
        for k in data.keys():
            
            element = data[k]
            if element[key_id] == value_id:
                
                self._username = element["username"]
                self._discord_id = str(element["discord_id"])
                self._nickname = element["nickname"]
                self._country = element["country"]
                self._language = element["language"]
                self._database_solve_count = int(element["solved"])
                self._database_solve_array = [c == "1" for c in element["solve_list"]]
                self._database_award_count = element["awards"]
                self._database_award_array = list(map(
                    lambda x: [str(c) == "1" for c in x],
                    element["awards_list"].split("|")
                ))
                break
                
    
    def update_from_database_kudo(self, connection = None, data = None):
        
        key_id, value_id = self.identity()
        check_function = lambda x: 0 if x is None else len(x.keys())
        
        while check_function(data) == 0:
            
            if data is not None:
                self.update_from_post_page()
                self.push_kudo_to_database()
        
            tquery = f"SELECT * FROM members \
                INNER JOIN pe_posts ON members.username = pe_posts.username \
                WHERE members.{key_id} = '{value_id}'"
            data = dbqueries.option_query(tquery, connection)
    
        for k in data.keys():
            
            element = data[k]
            if element[key_id] == value_id:
                
                self._database_kudo_count = int(element["kudos"])
                self._database_kudo_array = list(map(
                    lambda el: list(map(
                        int, el.split("n")
                    )), element["posts_list"].split("|")
                ))
                break
        
    
    def identity(self) -> tuple:
        if self._username is not None:
            return ["username", self.username()]
        elif self._discord_id is not None:
            return ["discord_id", self.discord_id()]
        else:
            raise Exception("Need either a username or a Discord ID")
    
    
    def username(self) -> str:
        if self._username is None:
            self.update_from_database()
        return self._username
    
    
    def nickname(self) -> str:
        if self._nickname is None:
            self.update_from_database()
        return self._nickname
    
    
    def username_ping(self) -> str:
        dis_id = self.discord_id()
        if dis_id != "":
            return f"`{self.username()}` (<@{dis_id}>)"
        return f"`{self.username()}`"  
    
    
    def country(self) -> str:
        if self._country is None:
            self.update_from_database()
        return self._country
    
    
    def language(self) -> str:
        if self._language is None:
            self.update_from_database()
        return self._language
    
    
    def solve_count(self) -> int:
        
        if self._pe_solve_count is not None:
            return self._pe_solve_count
        elif self._database_solve_count is not None:
            return self._database_solve_count
        
        self.update_from_database()
        return self._database_solve_count
    
    
    def pe_solve_count(self) -> int:
        
        if self._pe_solve_count is not None:
            return self._pe_solve_count
        
        self.update_from_friend_list()
        return self._pe_solve_count
        
        
    def database_solve_count(self) -> int:
        
        if self._database_solve_count is not None:
            return self._database_solve_count
        
        self.update_from_database()
        return self._database_solve_count
    
    
    def solve_array(self) -> list:
        
        if self._pe_solve_array is not None:
            return self._pe_solve_array
        elif self._database_solve_array is not None:
            return self._database_solve_array
        
        self.update_from_database()
        return self._database_solve_array
    
    
    def pe_solve_array(self) -> list:
        
        if self._pe_solve_array is not None:
            return self._pe_solve_array
        
        self.update_from_friend_list()
        return self._pe_solve_array

    
    def database_solve_array(self) -> list:
        
        if self._database_solve_array is not None:
            return self._database_solve_array
        
        self.update_from_database()
        return self._database_solve_array
    
    
    def award_count(self):
        
        if self._pe_award_count is not None:
            return self._pe_award_count
        elif self._database_award_count is not None:
            return self._database_award_count
        
        self.update_from_database()
        return self._database_award_count
    
    
    def pe_award_count(self):
        
        if self._pe_award_count is not None:
            return self._pe_award_count
        
        self.update_from_award_list()
        return self._pe_award_count
    
    
    def database_award_count(self):
        
        if self._database_award_count is not None:
            return self._database_award_count
        
        self.update_from_database()
        return self._database_award_count
        
        
    def award_array(self):
        
        if self._pe_award_array is not None:
            return self._pe_award_array
        elif self._database_award_array is not None:
            return self._database_award_array
        
        self.update_from_database()
        return self._database_award_array
    
    
    def pe_award_array(self):
        
        if self._pe_award_array is not None:
            return self._pe_award_array
        
        self.update_from_award_list()
        return self._pe_award_array
    
    
    def database_award_array(self):
        
        if self._database_award_array is not None:
            return self._database_award_array
        
        self.update_from_database()
        return self._database_award_array
    
    
    def kudo_count(self):
        
        if self._pe_kudo_count is not None:
            return self._pe_kudo_count
        elif self._database_kudo_count is not None:
            return self._database_kudo_count
        
        self.update_from_post_page()
        return self._database_kudo_count
        
        
    def pe_kudo_count(self):
        
        if self._pe_kudo_count is not None:
            return self._pe_kudo_count
        
        self.update_from_post_page()
        return self._pe_kudo_count
    
    
    def database_kudo_count(self):
        
        if self._database_kudo_count is not None:
            return self._database_kudo_count
        
        self.update_from_database_kudo()
        return self._database_kudo_count
    
    
    def kudo_array(self):
        
        if self._pe_kudo_array is not None:
            return self._pe_kudo_array
        elif self._database_kudo_array is not None:
            return self._database_kudo_array
        
        self.update_from_post_page()
        return self._database_kudo_array
        
        
    def pe_kudo_array(self):
        
        if self._pe_kudo_array is not None:
            return self._pe_kudo_array
        
        self.update_from_post_page()
        return self._pe_kudo_array
    
    
    def database_kudo_array(self):
        
        if self._database_kudo_array is not None:
            return self._database_kudo_array
        
        self.update_from_database_kudo()
        return self._database_kudo_array
        
    
    def level(self) -> int:
        if self._level is None:
            self.update_from_database()
        return self._level
            
        
    def discord_id(self) -> str:
        if self._discord_id is None:
            self.update_from_database()
        return self._discord_id
    

    def position_in_discord(self) -> int:
        
        current_rank = 1
        all_members = Member.members_database()
        valid_members = 0

        if not self.is_discord_linked():
            return -1

        m: Member
        for m in all_members:

            if not m.is_discord_linked():
                continue
            valid_members += 1

            if m.solve_count() > self.solve_count():
                current_rank += 1
        
        return [current_rank, valid_members]

        
            
    def is_discord_linked(self, connection = None, data = None) -> bool:
        
        dis_id = self.discord_id()
        
        if self._username is not None:
            return True
        
        if data is None:
            tquery = f"SELECT * FROM members WHERE discord_id='{dis_id}';"
            data = dbqueries.option_query(tquery, connection)
            
        return len(data.keys()) >= 1
    
    
    def is_account_in_database(self, connection = None) -> bool:
        
        key_id, value_id = self.identity()
        tquery = f"SELECT * FROM members WHERE {key_id}='{value_id}';"
        
        return len(dbqueries.option_query(tquery, connection).keys()) >= 1
        
    
    def have_solves_changed(self):
        return (not (self.pe_solve_count() == self.database_solve_count()))
    
    
    def have_awards_changed(self):
        return (not (self.pe_award_count() == self.database_award_count()))
    
    
    def have_kudos_changed(self):
        return (not (self.pe_kudo_count() == self.database_kudo_count()))
    
            
    def get_new_solves(self):
        
        if not self.have_solves_changed():
            return []
        
        project_euler_data = self.pe_solve_array()
        database_data = self.database_solve_array()
        
        max_len = len(project_euler_data)
        
        nsolves = []
        
        for i in range(max_len):
            
            if project_euler_data[i] == False:
                continue
            
            if project_euler_data[i] == True and (i >= len(database_data) or database_data[i] == False):
                nsolves.append(i + 1)
            
        return nsolves
    
    
    def get_new_kudos(self):
        
        if not self.have_kudos_changed():
            return []
        
        project_euler_data = self.pe_kudo_array()
        database_data = self.database_kudo_array()
        
        database_dict = {el[0]: el[1] for el in database_data}
        
        nkudos = []
        
        for post in project_euler_data:
            
            post_id = post[0]
            post_kudos = post[1]
            
            if post_id not in database_dict.keys():
                nkudos.append(post)
            elif post_kudos != database_dict[post_id]:
                nkudos.append([post_id, post_kudos - database_dict[post_id]])   
            
        return nkudos
    
        
    def get_new_awards(self):
        
        if not self.have_awards_changed():
            return []
        
        project_euler_data = self.pe_award_array()
        database_data = self.database_award_array()
        
        first_len = len(project_euler_data[0])
        second_len = len(project_euler_data[1])
        
        nawards = [[], []]
        
        for i in range(first_len):
            if project_euler_data[0][i] == True and database_data[0][i] == False:
                nawards[0].append(i)
            
        for i in range(second_len):
            if project_euler_data[1][i] == True and database_data[1][i] == False:
                nawards[1].append(i)
            
        return nawards
        
    
    def push_kudo_to_database(self) -> None:
        
        kudos = self.pe_kudo_array()
        
        formatted = "|".join(list(map(
            lambda el: "n".join(list(map(str, el))), kudos
        )))
    
        tquery = f"INSERT INTO pe_posts (username, posts_number, kudos, posts_list) \
            VALUES ('{self.username()}', 0, {self.kudo_count()}, '{formatted}');"
            
        dbqueries.single_req(tquery)

    
    def push_basics_to_database(self) -> None:
        
        solved = self.pe_solve_count()
        solve_list = "".join([
            "01"[boolean] for boolean in self.pe_solve_array()
        ])
        
        username = self.username()
        nickname = self.nickname()
        country = self.country()
        language = self.language()
        
        if not self.is_account_in_database():
            awards_array = self.pe_award_array()
            awards = self.pe_award_count()
            awards_list = "|".join([
                "".join(["01"[b] for b in awards_array[0]]),
                "".join(["01"[b] for b in awards_array[1]])
            ])
            
            tquery = f"INSERT INTO members (username, nickname, country, language, solved, \
                solve_list, discord_id, awards, awards_list) VALUES (\
                '{username}', '{nickname}', '{country}', '{language}', \
                {solved}, '{solve_list}', '', {awards}, '{awards_list}');"
                
        else:
            tquery = f"UPDATE members SET nickname='{nickname}', \
                country='{country}', language='{language}', solved={solved},\
                solve_list='{solve_list}' WHERE username='{username}';"
                
        dbqueries.single_req(tquery)
        
        
    def push_awards_to_database(self) -> None:
        
        username = self.username()
        
        awards_array = self.pe_award_array()
        awards = self.pe_award_count()
        awards_list = "|".join([
            "".join(["01"[b] for b in awards_array[0]]),
            "".join(["01"[b] for b in awards_array[1]])
        ])
        
        tquery = f"UPDATE members SET awards={awards}, \
            awards_list='{awards_list}' WHERE username='{username}';"
            
        dbqueries.single_req(tquery)
        
        
    @staticmethod
    def members_friends() -> list:
        
        project_euler_data = ProjectEulerRequest("https://projecteuler.net/minimal=friends", True)
        
        usernames = list(map(
            lambda x: x.split("##")[0],
            project_euler_data.response.split("\n")
        ))
        
        result_list = []
        
        for username in usernames:
            
            if username == "":
                continue
            
            current = Member(username)
            current.update_from_friend_list(project_euler_data)
            
            result_list.append(current)
            
        return result_list
    
    
    @staticmethod
    def members_database() -> list:
        
        database_data = dbqueries.single_req("SELECT * FROM members;")
        
        usernames = list(map(
            lambda k: database_data[k]["username"],
            database_data 
        ))
        
        result_list = []
        
        for username in usernames:
            
            if username == "":
                continue
            
            current = Member(username)
            current.update_from_database(data = database_data)
            
            result_list.append(current)
            
        return result_list
    
    @staticmethod
    def members() -> list:
        
        database_data = dbqueries.single_req("SELECT * FROM members;")
        project_euler_data = ProjectEulerRequest("https://www.projecteuler.net/minimal=friends")
        
        database_usernames = list(map(
            lambda k: database_data[k]["username"],
            database_data 
        ))
        
        project_euler_usernames = list(map(
            lambda x: x.split("##")[0],
            project_euler_data.response.split("\n")
        ))
        
        result_list = []
        
        for username in project_euler_usernames:
            
            if username == "":
                continue
        
            current = Member(username)
            current.update_from_friend_list(project_euler_data)
            
            if username in database_usernames:
                current.update_from_database(data = database_data)
                
            result_list.append(current)
            
        return result_list
    

    def solved_problems(self):        
        solves = []
        for index, solved in enumerate(self.solve_array()):
            if solved:
                solves.append(index + 1)
        return solves


    def unsolved_problems(self):        
        unsolves = []
        for index, solved in enumerate(self.solve_array()):
            if not solved:
                unsolves.append(index + 1)
        return unsolves

        



def update_process() -> None:
    
    members = Member.members()
    skipped_member_count = 0
    
    new_changes = []
    
    m: Member
    for m in members:
        
        if m.have_solves_changed():    
            
            nsolves = m.get_new_solves()
            console.log(f"New solve(s) for {m.username()}: {nsolves}")
            m.push_basics_to_database()
            
            nawards = None
            if m.have_awards_changed():
                nawards = m.get_new_awards()
                console.log(f"New award(s) for {m.username()}: {nawards}")
                m.push_awards_to_database()
            
            new_changes.append({"member": m, "solves": nsolves, "awards": nawards})
            
        else:
            skipped_member_count += 1
            
    console.log(f"Skipped {skipped_member_count} members")
    return new_changes

            


# Do a request to the projecteuler website with the corresponding cookies
def req_to_project_euler(url, login = True):

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


# def keep_session_alive():



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

    # Format data to get into the database
    format_func = lambda x: x.replace("C###", "Csharp##").replace("F###", "Fsharp##").split("##") 

    # Go take a look for yourself of https://projecteuler.net/minimal=friends, you may understand better how is data formatted
    members = list(map(format_func, data.split("\n")))
    db_members = dbqueries.single_req("SELECT * FROM members;")
    names = list(map(lambda x: db_members[x]["username"], db_members))

    # Connection to the actual database
    connection = dbqueries.open_con()

    # Count the number of people for which nothing has changed (not really useful, mainly for tests)
    people_passed_nothing_changed = 0

    # Assert that there is no error in the retrieve
    if len(names) < 10:
        return None
    #print(data)
    for member in members:

        # For the last line of the retrieved data, which is only a blank line
        if len(member) == 1:
            continue

        # Format member: [Account, Nickname, Country, Solves Count, Level, Binary String of solves]
        # A cell of format members is "" if the members has not set the optional parameter
        format_member = list(map(lambda x: x if x != "" else "Undefined", member))
        # print(format_member)
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



def push_solve_to_database(member: Member, solve: PE_Problem):

    pb_def = problem_def(solve.problem_id)
    position = pb_def[3]

    temp_query = "INSERT INTO solves (member, problem, solve_date, position) VALUES ('{0}', {1}, NOW(), {2})"
    temp_query = temp_query.format(member.username(), solve.problem_id, position)
    dbqueries.single_req(temp_query)






# Return array of the form ['n', 'Problem title', Unix Timestamp of publish, 'nb of solves', '0']
# Careful as all values in the array are string, not ints
def problem_def(n):
    data = req_to_project_euler(BASE_URL.format("problems"))
    lines = data.split("\n")
    pb = lines[n].replace("\r", "")
    specs = pb.split("##")
    return specs


# Return array of the form [problem_1, problem_2, ...., problem_last]
# With each problem being of the kind ['n', 'Problem title', Unix Timestamp of publish, 'nb of solves', '0']
# Careful as all values in the array are string, not ints
def problems_list():
    data = req_to_project_euler(BASE_URL.format("problems"), False).split("\n")
    data = list(map(lambda element: element.replace("\r", "").split("##"), data))
    return data


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

    # Get the profile of the user on project euler
    posts_made, kudos_earned, posts_list = get_kudos(username)
    # print(posts_made, kudos_earned, posts_list)

    # Get the profile of the user in the database
    connection = dbqueries.open_con()
    temp_query = "SELECT * FROM pe_posts WHERE username = '{0}';".format(username)
    data = dbqueries.query(temp_query, connection)

    # This is the way data is formatted in the database, if you had 1 kudo on post 162 and 2 kudos on post 163, it would be like 162n2|163n1
    posts_txt = "|".join(["n".join(map(str, p)) for p in posts_list])

    changes = []
    total_change = 0

    # If the user had never used /kudos before, so there is no profile in the database
    if len(data.keys()) == 0:
        temp_query = "INSERT INTO pe_posts (username, posts_number, kudos, posts_list) VALUES ('{0}', {1}, {2}, '{3}');".format(username, posts_made, kudos_earned, posts_txt)
        dbqueries.query(temp_query, connection)
    else:

        # Get the first line of the database
        previous = data[0]
        
        # Get the data in a nice array [[problemn1, kudos1], ...]
        previous_posts = list(map(lambda x: list(map(int, x.split("n"))), previous["posts_list"].split("|")))
        # print(previous_posts)

        # If the total number of kudos has changed
        if previous["kudos"] != kudos_earned:

            # The number of kudos obtained since the last update
            total_change = kudos_earned - previous["kudos"]
            
            for post in posts_list:

                # To know if we found the post in the known posts in the database
                found_post_in_already_posted = False
                
                # If the post was already there, then we compute the number of kudos gained there
                for previous_post in previous_posts:
                    
                    # If we got the right post that has the problem number corresponding to the actual one
                    if post[0] == previous_post[0]:
                        found_post_in_already_posted = True
                        if post[1] != previous_post[1]:
                            changes.append([post[0], post[1] - previous_post[1]])
                        break

                # If the post was created between the current command and the last /kudo
                if not found_post_in_already_posted:
                    changes.append([post[0], post[1]])
                    
        
        # If there was any change, we modify the profile in the database, wheter it is a new kudo or simply a new post, without kudos on it
        if previous["posts_number"] != posts_made or previous["kudos"] != kudos_earned:
            temp_query = "UPDATE pe_posts SET posts_number='{0}', kudos='{1}', posts_list='{2}' WHERE username='{3}'".format(posts_made, kudos_earned, posts_txt, username)
            dbqueries.query(temp_query, connection)

    dbqueries.close_con(connection)
    return [kudos_earned, total_change, changes]


# Returns True or False, given a discord id
def is_discord_linked(discord_id, connection=None):

    data = dbqueries.option_query("SELECT * FROM members WHERE discord_id='{0}';".format(str(discord_id)), connection)
    return len(data.keys()) >= 1


# Returns False if discord_id is not in the database, else returns the project euler username
def project_euler_username(discord_id, connection=None):

    if connection is None:
        data = dbqueries.single_req("SELECT * FROM members WHERE discord_id='{0}';".format(str(discord_id)))
    else:
        data = dbqueries.query("SELECT * FROM members WHERE discord_id='{0}';".format(str(discord_id)), connection)

    if len(data.keys()) < 1:
        return False

    return data[0]["username"]


# Returns a 2d array of the form [problem_1, problem_2, problem_3, ...]
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
def get_all_members_who_solved(problem: int):

    solvers = []

    profiles = get_all_profiles_on_project_euler()

    for profile in profiles:

        # Make sure the problem can be retrieved from the user
        if (len(profile[6]) > problem - 1) and (profile[6][problem - 1] == "1"):
            solvers.append(profile[0])

    return solvers


# Essentially does the same thing as get_all_members_who_solved, but returns the entire profiles
# Returns a list with format [[username1: str, discord_id1: str], [username2: str, discord_id2: str], ....]
def get_all_discord_profiles_who_solved(problem: int):

    solvers = []

    profiles = get_all_profiles_in_database()

    for k in profiles.keys():
        profile = profiles[k]
        
        if len(profile["solve_list"]) >= problem and profile["solve_list"][problem - 1] == "1" and profile["discord_id"] != "":
            solvers.append([profile["username"], profile["discord_id"]])

    return solvers


# return a binary string like "111110001100..." with every 1 marking a solve
# use a project euler request, not a request to the database (should not change anything)
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

    return member_solves


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


# returns a list of all the profiles in the database 
def get_all_profiles_in_database():
    return dbqueries.single_req("SELECT * FROM members;")


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


# Get the solves of the last few days in the database
def get_solves_in_database(days_count = 0):

    connection = dbqueries.open_con()

    if days_count == 0:
        temp_query = "SELECT * FROM solves"
    else:
        temp_query = "SELECT * FROM solves WHERE DATE(solve_date) BETWEEN DATE(CURRENT_DATE() - INTERVAL {0} DAY) AND DATE(CURRENT_DATE());"
        temp_query = temp_query.format(days_count)
        
    data = dbqueries.query(temp_query, connection)
    dbqueries.close_con(connection)

    return data


# Get the global solves in the database
def get_global_solves_in_database(days_count = 0):

    connection = dbqueries.open_con()

    if days_count == 0:
        temp_query = "SELECT id, solves, DATE(date_stat) FROM global_stats"
    else:
        temp_query = "SELECT id, solves, DATE(date_stat) FROM global_stats WHERE DATE(date_stat) BETWEEN DATE(CURRENT_DATE() - INTERVAL {0} DAY) AND DATE(CURRENT_DATE());"
        temp_query = temp_query.format(days_count)

    data = dbqueries.query(temp_query, connection)
    dbqueries.close_con(connection)

    return data 


# Get the current global stats on the website
def get_global_stats():

    # Basic script to get the html code on a page
    problem_url = NOT_MINIMAL_BASE_URL.format("problem_analysis")
    problem_data = req_to_project_euler(problem_url)
    problem_soup = BeautifulSoup(problem_data, 'html.parser')

    # This tag represents the column we wants
    problems = problem_soup.find_all(class_="equal_column")
    problems = list(map(lambda x: x.text, problems)) # Get the text of elements, no html tags
    problems = list(filter(lambda x: x != "Solved Exactly", problems)) # Remove colum names

    # Problem count
    problem_count = sum([(i + 1) * int(problems[i]) for i in range(len(problems))])
    
    # Again, basic requests to get html code
    level_url = NOT_MINIMAL_BASE_URL.format("levels")
    level_data = req_to_project_euler(level_url)
    level_soup = BeautifulSoup(level_data, 'html.parser')

    # Format all this data
    levels = level_soup.find_all(class_="small_notice")
    levels = list(map(lambda x: x.text.split()[0], levels)) # format <div>4054 members</div>
    
    # Get levels count
    level_count = sum([(i + 1) * int(levels[i]) for i in range(len(levels))])    

    # Basic script to get the awards stats
    award_url = NOT_MINIMAL_BASE_URL.format("awards")
    award_data = req_to_project_euler(award_url)
    award_soup = BeautifulSoup(award_data, 'html.parser')

    # Formatting the data
    awards = award_soup.find_all(class_="small_notice")
    awards = list(map(lambda x: x.text.split()[0], awards))
    
    # Award count
    award_count = sum(list(map(int, awards)))

    return [problem_count, level_count, award_count]


# Update the database with global statistics
def update_global_stats():

    # Open connection to the database
    connection = dbqueries.open_con()

    # The query to retrieve saved statistics
    temp_query = "SELECT * FROM global_constants"
    previous_data = dbqueries.query(temp_query, connection)

    # Ensure the retrieve was successful
    if len(previous_data) == 1:
        previous_data = previous_data[0]
    else:
        dbqueries.close_con(connection)
        return False

    # Assert the current day has not already been retrieved
    current_day = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d")
    last_date = datetime.datetime.strptime(previous_data["saved_date"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")

    if current_day == last_date:
        return False

    # Get today's statistics
    problem_count, level_count, award_count = get_global_stats()

    # Compute the difference for each stat
    problem_diff = problem_count - previous_data["solves_count"]
    level_diff = level_count - previous_data["levels_count"]
    award_diff = award_count - previous_data["awards_count"]

    # If the cache is still the same, no need to update right now
    if problem_diff == 0 and level_diff == 0 and award_diff == 0:
        return False

    # And bring it back in the database
    temp_query = "INSERT INTO global_stats (solves, levels, awards, date_stat) VALUES ({0}, {1}, {2}, NOW())"
    temp_query = temp_query.format(problem_diff, level_diff, award_diff)
    dbqueries.query(temp_query, connection)

    # Update the last data
    temp_query = "UPDATE global_constants SET solves_count = {0}, levels_count = {1}, awards_count = {2}, saved_date = NOW()"
    temp_query = temp_query.format(problem_count, level_count, award_count)
    dbqueries.query(temp_query, connection)

    # Alert my phone that everything has went as planned
    phone_api.bot_success("Added stats for day " + current_day)

    return True # Everything went fine



if __name__ == "__main__":
    
    dbqueries.setup_database_keys()
    
    x = Member(_username = "Teyzer18")
    # print(x.unsolved_problems())

    print(PE_Problem.complete_list())

    # z = Member.members()
    # for m in z:
    #     m.push_basics_to_database()
    #     print(m.username())
    
    console.log(TOTAL_REQUESTS, dbqueries.DB_TOTAL_REQUESTS)
    
    
