import requests
from bs4 import BeautifulSoup

import datetime
import pytz
import json
import time

import pe_database

import phone_api

from rich.console import Console
from rich import inspect

from typing import List, Dict, Optional, Any, Tuple, Union


TOTAL_REQUESTS = 0
TOTAL_SUCCESS_REQUESTS = 0
SESSION_REQUESTS = 0
LAST_REQUEST_SUCCESSFUL = False
LAST_REQUEST_TIME = datetime.datetime.now(pytz.utc)


CREDENTIALS_LOCATION = "session_cookies.txt"
BASE_URL = "https://projecteuler.net/minimal={0}"
NOT_MINIMAL_BASE_URL = "https://projecteuler.net/{0}"

COOKIES = {}

console = Console()


def pe_api_setup(cookies, account) -> None:

    global COOKIES
    COOKIES = cookies

    account_name = account["username"]

    console.log(f"[-] Added credential for account {account_name}")
    

def now_unix() -> int:
    return int(time.time())
    
    
def is_recent_unix(unix_timestamp: int):
    return now_unix() - unix_timestamp < 60



class ProjectEulerRequest:


    @staticmethod
    def request_failed() -> None:
        """
        When called, increase a global variable, counting how many requests failed.
        """
        global LAST_REQUEST_SUCCESSFUL
        LAST_REQUEST_SUCCESSFUL = False


    @staticmethod
    def request_succeeded() -> None:
        """
        When called, increase a global variable, counting how many requests succeeded.
        """
        global LAST_REQUEST_SUCCESSFUL, LAST_REQUEST_TIME, TOTAL_SUCCESS_REQUESTS
        
        LAST_REQUEST_SUCCESSFUL = True
        LAST_REQUEST_TIME = datetime.datetime.now(pytz.utc)
        TOTAL_SUCCESS_REQUESTS += 1

    
    def __init__(self, target_url: str, need_login: bool = True) -> None:

        global TOTAL_REQUESTS, SESSION_REQUESTS
        
        TOTAL_REQUESTS += 1
        SESSION_REQUESTS += 1

        if need_login:
            cookies = COOKIES
        else:
            cookies = {}

        try:
            # Do the request to the website, with the right cookies that emulate the account
            r = requests.get(target_url, cookies=cookies)
            self.status = int(r.status_code)
            
            if r.status_code != 200:
                # Phone API is sending a notifications to teyzer's phone
                phone_api.bot_crashed(r.status_code)
                ProjectEulerRequest.request_failed()
                self.response: str | Exception | None = None
                console.log(r.text)
            else:
                ProjectEulerRequest.request_succeeded()
                self.response: str | Exception | None = r.text
            
            self.err = None

        except Exception as err:

            # Previously, err was raised again at the end of this, but returning no data seems better
            phone_api.bot_crashed(str(err))
            ProjectEulerRequest.request_failed()
            self.status = None
            self.response: str | Exception | None = None
            self.err = err
            




        

class Problem:
    
    
    _all_problems: List[Dict[str, Union[int, 'Problem']]] = []
    
    
    def __init__(self, problem_id: int, **kwargs):
        
        self._name: Optional[str] = None
        self._problem_id: Optional[int] = problem_id
        self._unix_publication: Optional[int] = None
        self._solves: Optional[int] = None
        self._solves_in_discord: Optional[int] = None
        self._difficulty_rating: Optional[int] = None
        
        for k, val in kwargs.items():
            self.__dict__[k] = val
        
            
    def __str__(self) -> str:
        return str(self.__dict__)
    
    
    def __repr__(self) -> str:
        return self.__str__()


    @staticmethod
    def fetch_problems() -> None:
        
        """
        Updates the global array `PROBLEMS`, which contains every problem
        """
        
        res_list = []
        
        api_data = ProjectEulerRequest("https://projecteuler.net/minimal=problems", False)
        
        rows = api_data.response.split("\n")
        timestamps = [int(x.split("##")[2]) for x in rows[1:-1]]
        
        ux_data = ProjectEulerRequest("https://projecteuler.net/progress", True)
        soup = BeautifulSoup(ux_data.response, 'html.parser')
        div = soup.find_all("span", class_='tooltiptext_narrow')
        
        if len(div) == 0:
            raise Exception("data could not be fetched from the website, could not update problem fields")
        
        for element in div:
            
            properties = list(map(
                lambda x: x.text, 
                element.find_all("div")
            ))
            
            if len(properties) == 0:
                continue
            
            problem_id = int(properties[0].split()[1])
            try: # TODO: Make a better version of this, this is pure quick fix here
                solvers = int(properties[1].split()[2])
            except Exception as _:
                solvers = 0


            if len(properties) == 3:    
                difficulty = None
                title = properties[2].replace("\"", "")
            elif len(properties) == 4:
                difficulty = int(properties[2].split(": ")[1].split("%")[0])
                title = properties[3].replace("\"", "")
            else:
                raise Exception("Properties did not have 3 or 4 fields, resulted in title not being defined")
            
            problem = Problem(problem_id, _problem_id=problem_id, _name=title, _unix_publication=timestamps[problem_id - 1], _solves=solvers, _difficulty_rating=difficulty)
            res_list.append(problem)
        
        current_time = now_unix()
        Problem._all_problems = [{"problem": problem, "fetched_at": current_time} for problem in res_list]


    @staticmethod
    def last_update(problem_id: int) -> Optional[int]:
        
        if len(Problem._all_problems) < problem_id:
            return None
        
        return Problem._all_problems[problem_id - 1]["fetched_at"]
    
    
    @staticmethod 
    def oldest_last_update() -> Optional[int]:
        
        if len(Problem._all_problems) == 0:
            return None
        
        min_timestamp = now_unix()

        for element in Problem._all_problems:
            fetched_at = element["fetched_at"]
            min_timestamp = min(min_timestamp, fetched_at)
            
        return min_timestamp
        
        
    @staticmethod
    def should_be_updated() -> bool:
        
        latest = Problem.oldest_last_update()
        if latest is None:
            return True
        
        return not is_recent_unix(latest)        
    

    @staticmethod
    def complete_list() -> List['Problem']:

        """
        Returns a list containing all problems. L[i - 1] is thus problem i. Each
        element is a Problem instance.
        """
        
        if Problem.should_be_updated():
            Problem.fetch_problems()
            
        return [element["problem"] for element in Problem._all_problems]
        
    
    def problem_id(self) -> int:
        
        """
        Returns the problem_id of a problem
        """
        
        if self._problem_id is None:
            raise ValueError("The problem object needs a _problem_id parameter to know which problem it is")
        
        return self._problem_id
    

    def update_from_project_euler(self) -> None:
        
        """
        Will update the problem, and gather the information you can about it on Project Euler. 
        This function is called automatically when trying to get fields that have not yet been defined
        """
        
        if self._problem_id is None:
            raise ValueError("_problem_id field is None")
        
        latest = Problem.last_update(self._problem_id)
        if latest is None or not is_recent_unix(latest):
            Problem.fetch_problems()
            
        for field in ["_name", "_unix_publication", "_solves", "_difficulty_rating"]:    
            self.__dict__[field] = Problem._all_problems[self._problem_id - 1]["problem"].__dict__[field]


    def name(self) -> str:
        
        """
        Return the name (title) of the problem
        """
        
        if self._name is None and self._problem_id is None:
            raise ValueError("_name and _problem_id fields are both undefined")
        
        if self._name is None:
            self.update_from_project_euler()
            
        return self._name
    
    
    def unix_publication(self) -> int:
        
        """
        Returns the unix publication date of the problem 
        """
        
        if self._unix_publication is None and self._problem_id is None:
            raise ValueError("_unix_publication and _problem_id fields are both undefined")
        
        if self._unix_publication is None:
            self.update_from_project_euler()
            
        return self._unix_publication
    
    
    def solves(self) -> int:
        
        """
        return the number of solves of a problem
        """
        
        if self._solves is None and self._problem_id is None:
            raise ValueError("_solves and _problem_id fields are both undefined")
        
        if self._solves is None:
            self.update_from_project_euler()
            
        return self._solves
    
    
    def difficulty_is_defined(self) -> bool:
        
        if self._difficulty_rating is not None:
            return True
        
        self.update_from_project_euler()
        return self._difficulty_rating is not None
    
    
    def difficulty(self) -> Optional[int]:
        
        """
        Returns the difficulty a problem
        """
        
        if self._difficulty_rating and self._problem_id is None:
            raise ValueError("_difficulty_rating and _problem_id are both undefined")
        
        if self._difficulty_rating is None:
            self.update_from_project_euler()
            
        return self._difficulty_rating
            

    def guess_difficulty_detailed(self, neighbors_count: int = 5) -> Tuple[int, List['Problem']]:
        
        """
        returns the difficulty guessed by the bot with a k-neighbor algorithm, along 
        with its k nearest neighbors
        """
        
        data_filename = "saved_data/fastest_solves.json"
        with open(data_filename, "r") as f:
            data = json.load(f)

        prob_key = str(self.problem_id())

        # TODO: make this a function incorporated inside the Problem object
        problem_data = get_fastest_solvers(self.problem_id())
        solve_count = len(problem_data.keys())
        
        new_dictionary = {}

        for prob_id in data.keys():

            if prob_id == prob_key:
                continue

            if len(data[prob_id].keys()) < 100:
                continue

            new_dictionary[prob_id] = {}
            for position in data[prob_id].keys():
                
                if int(position) <= solve_count:
                    new_dictionary[prob_id][position] = data[prob_id][position]

        def own_distance(arr1, arr2):

            total = 0

            for k in arr1.keys():
                ratio = arr1[k]["solve_time"] / arr2[k]["solve_time"] + arr2[k]["solve_time"] / arr1[k]["solve_time"]
                total += ratio
            
            return total

        nearests = sorted(new_dictionary.keys(), key=lambda k: own_distance(problem_data, new_dictionary[k]), reverse=False)
        all_problems = Problem.complete_list()

        to_keep: List[Problem] = list(map(lambda key: all_problems[int(key) - 1], nearests[:neighbors_count]))
        to_keep_difficulties: List[int] = list(map(lambda problem: problem.difficulty(), to_keep))

        difficulty = sorted(to_keep_difficulties)[neighbors_count // 2]
        
        return difficulty, to_keep


    def guess_difficulty(self) -> int:
        """
        returns the difficulty guessed by the bot with a k-neighbor algorithm
        """
        return self.guess_difficulty_detailed()[0]
        
            
    def title(self) -> int:
        """
        Alias for self.name() 
        """
        return self.name()
        
        
    def solvers_in_discord(self) -> List['Member']:
        
        members: List['Member'] = Member.members()
        
        valid_solvers = []
        
        member: 'Member'
        for member in members:
            
            if member.has_solved(self.problem_id()):
                valid_solvers.append(member)
                
        return valid_solvers
    
    

class Solve:
    
    
    def __init__(self, **kwargs):
        
        self._problem: Optional[Problem] = None
        self._problem_id: Optional[int] = None
        self._member: Optional[Member] = None
        self._unixtime: Optional[int] = None
        self._unix_is_accurate: bool = False
        
        for k, val in kwargs.items():
            self.__dict__[k] = val
            
            
    def problem(self) -> Problem:
        
        if self._problem is None and self._problem_id is None:
            raise Exception("this solve object does not have a problem object or problem id attached")
        
        if self._problem is None:
            self._problem = Problem(self._problem_id)
            
        return self._problem
    
    
    def problem_id(self) -> int:

        if self._problem_id is not None:
            return self._problem_id
        
        if self._problem is None and self._problem_id is None:
            raise Exception("this solve object does not have a problem object or problem id attached")
        
        return self.problem().problem_id()
            
        
    def member(self) -> 'Member':
        
        if self._member is None:
            raise ValueError("_member field has not been specified")
        
        return self._member
    
    
    def unixtime(self) -> int:
        
        if self._unixtime is None:
            raise ValueError("_unixtime field has not been specified")
        
        return self._unixtime



class Award:
    
    
    def __init__(self, **kwargs):
        pass



class Member:
    
    
    def __init__(self, **kwargs) -> None:

        self._username: Optional[str] = None # = _username
        self._nickname: Optional[str] = None # = _nickname
        self._country: Optional[str] = None # = _country
        self._language: Optional[str] = None # = _language
        self._level: Optional[int] = None # = _level
        
        self._discord_id: Optional[str] = None # = None if _discord_id is None else str(_discord_id)
        
        self._pe_solve_count: Optional[int] = None # = _solve_count
        self._pe_solve_array: Optional[List[bool]] = None # = _solve_array
        self._pe_award_count: Optional[int] = None # = _award_count
        self._pe_award_array: Tuple[List[bool], List[bool], List[bool]] | None = None # = _award_array
        self._pe_kudo_count: Optional[int] = None # = _kudo_count
        self._pe_kudo_array: List[Tuple[int, int]] | None = None # = _kudo_array
        self._pe_bonus_array: Optional[List[bool]] = None
        
        self._database_solve_count: Optional[int] = None # = _database_solve_count
        self._database_solve_array: Optional[List[bool]] = None # = _database_solve_array
        self._database_award_count: Optional[int] = None # = _database_award_count
        self._database_award_array: Tuple[List[bool], List[bool], List[bool]] | None = None # = _database_award_array
        self._database_kudo_count: Optional[int] = None # = _database_kudo_count
        self._database_kudo_array: List[Tuple[int, int]] | None = None # = _database_kudo_array
        self._database_bonus_array: Optional[List[bool]] | None = None

        # Elements that members can change by themselves on the discord
        self._private: Optional[bool] = None # = _private
        self._favorite_problem: Optional[int] = None
        self._reason_favorite_problem: Optional[str] = None

        for k, val in kwargs.items():

            if k == "_discord_id":
                self._discord_id = str(val)
                continue

            self.__dict__[k] = val
        
    
    def __str__(self) -> str:
        return f"{self._username}/{self._discord_id}/{self._pe_solve_count}/{self._database_solve_count}"
        

    def __repr__(self) -> str:
        return self.__str__()

        
    def update_from_friend_list(self, friend_page: Optional[ProjectEulerRequest] = None) -> None:

        """
        Update the Member object according to the bot's friend list.

        You can pass the data of the friends page if you already have the data
        and don't want to reload it.
        """

        if friend_page is None:
            friend_page = ProjectEulerRequest(BASE_URL.format("friends"))
        
        if friend_page.status != 200:
            ProjectEulerRequest.request_failed()
            raise Exception("Request failed")

        # This is because ## is used as separator in https://projecteuler.net/minimal=friends, and thus C# and F# are an issue
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

        to_solve_bool_array = lambda string_of_01: [
            c == "1" for c in
            filter(lambda x: x in "01", string_of_01)
        ]
        
        self._nickname = undef_func(target_member[1], False)
        self._country = undef_func(target_member[2], False)
        self._language = undef_func(target_member[3], False)
        self._pe_solve_count = undef_func(target_member[4], True)
        self._level = undef_func(target_member[5], True)
        self._pe_solve_array = to_solve_bool_array(target_member[6])
        self._pe_bonus_array = to_solve_bool_array(target_member[7])

    
    def update_from_award_list(self) -> None:

        """
        Update the awards of the member according to their awards page.
        """
        
        request_url = NOT_MINIMAL_BASE_URL.format(f"progress={self.username()};show=awards")
        kudo_page = ProjectEulerRequest(request_url)
        
        if kudo_page.status != 200:
            ProjectEulerRequest.request_failed()
            raise Exception("Request failed")
        
        soup = BeautifulSoup(kudo_page.response, 'html.parser')

        awards_section = soup.find(id="awards_section")
        if awards_section is None:
            raise Exception("awards section is None, this might be because the member is no longer in the friend list, or you're missing an account", self._username)
        
        awards_container = awards_section.find_all("div", recursive=False)

        div1 = awards_container[0]
        div2 = awards_container[1]
        div3 = awards_container[2]

        problem_awards = div1.find_all(class_="award_box")
        solves_problem = [1 if len(problem.find_all(class_="smaller green strong")) == 1 else 0 for problem in problem_awards]

        problem_publication = div2.find_all(class_="award_box")
        solves_publication = [1 if len(problem.find_all(class_="smaller green strong")) == 1 else 0 for problem in problem_publication]
        
        forum_awards = div3.find_all(class_="award_box")
        solves_forum = [1 if len(problem.find_all(class_="smaller green strong")) == 1 else 0 for problem in forum_awards]

        self._pe_award_count = sum(solves_problem) + sum(solves_publication) + sum(solves_forum)
        self._pe_award_array = tuple(map(
            lambda x: [str(c) == "1" for c in x],
            [solves_problem, solves_publication, solves_forum]
        ))
        
        
    def update_from_post_page(self) -> None:

        """
        Update the Member's posts according to their post page.
        """

        request_url = NOT_MINIMAL_BASE_URL.format(f"progress={self.username()};show=posts")
        post_page = ProjectEulerRequest(request_url)
        
        if post_page.status != 200:
            ProjectEulerRequest.request_failed()
            raise Exception("Request failed")

        soup = BeautifulSoup(post_page.response, 'html.parser')
        div = soup.find(id='posts_made_section')

        post_made, kudos_earned = div.find_all("h3")[0].text.split(" / ")
        post_made = int(post_made.split(" ")[2])
        kudos_earned = int(kudos_earned.split(" ")[2])

        def format_function(element: str) -> int:
            """
            Used to adapt to bonus problems
            """
            if element[0] == "B":
                element = "-" + element[1:]
            return int(element)

        posts = list(map(
            lambda post: tuple(map(
                lambda x: format_function(x.text),
                post.find_all("span")
            )), div.find_all(class_="post_made_box")
        ))
        
        self._pe_kudo_count = sum(list(map(lambda x: x[1], posts)))
        self._pe_kudo_array = posts


    def update_from_database(self, connection = None, data = None) -> None:

        """
        Downloads all the data from the database regarding this member, and updates all of its properties, so that they can be then used.
        """

        key_id, value_id = self.identity()
        
        def check_function(data_checked: Optional[List]) -> int:

            """
            This function is defined for what happens after.
            If the member we are looking for is within the data, we return 1 but
            in any other case we return 0
            """

            # If the data is None, obviously, we want to retry
            if data_checked is None:
                return 0
            
            # But if the member is within the database's data, we return 1
            for member in data_checked:
                if member[key_id] == str(value_id):
                    return 1
            
            return 0


        while check_function(data) == 0:
            
            if data is not None:
                self.update_from_friend_list()
                self.push_basics_to_database()
            
            temp_query = "SELECT * FROM members;"
            data = pe_database.query_option(temp_query, connection)


        for element in data:

            if element[key_id] == value_id:
                
                self._username = element["username"]
                self._discord_id = str(element["discord_id"])
                self._nickname = element["nickname"]
                self._country = element["country"]
                self._language = element["language"]
                self._database_solve_count = int(element["solved"])
                self._database_solve_array = [c == "1" for c in element["solve_list"]]
                self._database_bonus_array = [c == "1" for c in element["solve_list_bonus"]]
                self._database_award_count = element["awards"]
                self._database_award_array = tuple(map(
                    lambda x: [str(c) == "1" for c in x],
                    element["awards_list"].split("|")
                ))
                self._private = (element["private"] == 1)
                self._favorite_problem = element["favorite"]
                self._reason_favorite_problem = element["reason_favorite"]
                break
                
    
    def update_from_database_kudo(self, connection = None, data = None) -> None:
        
        key_id, value_id = self.identity()

        def check_function(data_checked: Optional[List]) -> int:

            """
            Returns 0 if the data does not seem correct, and anything
            but 0 if there is no apparent trouble
            """

            if data_checked is None:
                return 0
            return len(data_checked)

        
        while check_function(data) == 0:
            
            if data is not None:
                self.update_from_post_page()
                self.push_kudo_to_database()
        
            temp_query = f"SELECT * FROM members \
                INNER JOIN pe_posts ON members.username = pe_posts.username \
                WHERE members.{key_id} = '{value_id}'"
            data = pe_database.query_option(temp_query, connection)

    
        for element in data:

            if element[key_id] == value_id:
                
                self._database_kudo_count = int(element["kudos"])
                self._database_kudo_array = list(map(
                    lambda el: tuple(map(
                        int, el.split("n")
                    )), element["posts_list"].split("|")
                ))
                break
        
    
    def identity(self) -> Tuple[str, str]:
        """
        Returns a list of two elements, a key, and a value.
        It allows to check for the identity of the member with member[key] == value. (For a database's row)

        Note that this is needed because a member can have an identity coming from discord
        or from the project euler website, depending on where we have initiated the object.
        """
        if self._username is not None:
            return "username", self.username()
        elif self._discord_id is not None:
            return "discord_id", self.discord_id()
        else:
            raise Exception("Need either a username or a Discord ID")
        

    def private(self) -> bool:
        """
        Returns whether the user wants its username displayed somewhere or not.
        """
        if self._private is None:
            self.update_from_database()
        return self._private
    

    def push_privacy_to_database(self, new_privacy: bool, connection = None) -> None:
        """
        Updates a member's privacy in the database. `new_privacy` set as `true` indicates the member will be private.
        """
        new_value = "1" if (new_privacy == True) else "0"
        dis_id = self.discord_id()
        temp_query = f"UPDATE members SET private = {new_value} WHERE discord_id = '{dis_id}';"

        pe_database.query_option(temp_query, connection)
        self._private = new_privacy


    def favorite_problem(self) -> Optional[int]:
        """
        Returns the ID of the favorite problem of the member. Can be None.
        """
        if self._favorite_problem is None:
            self.update_from_database()

        # This can be None! If the user has never made any selection
        return self._favorite_problem


    def reason_favorite_problem(self) -> Optional[str]:
        """
        Returns the reason why the member has selected this problem as favorite. Can be None or an empty string.
        """
        if self._reason_favorite_problem is None:
            self.update_from_database()

        # This can be None or an empty string.
        return self._reason_favorite_problem


    def push_favorite_to_database(self, favorite_problem: Optional[int], reason_favorite_problem: Optional[str]) -> None:

        if favorite_problem is None:
            favorite_problem = 'NULL'
        else:
            favorite_problem = f'"{favorite_problem}"'

        if reason_favorite_problem is None:
            reason_favorite_problem = 'NULL'
        else:
            reason_favorite_problem = f'"{reason_favorite_problem}"'

        discord_id = self.discord_id()
        temp_query = f'UPDATE members SET favorite = {favorite_problem}, reason_favorite = {reason_favorite_problem} WHERE discord_id = "{discord_id}";'

        pe_database.query_single(temp_query)


    def username(self) -> str:
        """
        Returns the Project Euler username of the member.
        """
        if self._username is None:
            self.update_from_database()
        return self._username
    

    def username_option(self) -> str:
        """
        Returns the Project Euler username or "Private Account" if the account is private
        """
        if self.private():
            return "Private Account"
        return self.username()
    

    def nickname(self) -> str:
        """
        Returns the nickname of the account on Project Euler. This can be an empty string.
        """
        if self._nickname is None:
            self.update_from_database()
        return self._nickname
    

    def username_ping(self) -> str:

        """
        Returns the username formatted for discord code blocks, along with the discord ping if available
        """

        dis_id = self.discord_id()

        if self.private():
            return f"`Private Profile`"

        if dis_id != "":
            return f"`{self.username()}` (<@{dis_id}>)"
        
        return f"`{self.username()}`"  
    

    def country(self) -> str:
        """
        Returns the country of the Project Euler account
        """
        if self._country is None:
            self.update_from_database()
        return self._country
    

    def language(self) -> str:
        """
        Returns the language of the Project Euler account.
        """
        if self._language is None:
            self.update_from_database()
        return self._language
    
    
    def solve_csv_untouched(self) -> str:
        
        csv_url = f"https://projecteuler.net/history={self.username()}"
        req = ProjectEulerRequest(csv_url)
        
        csv_content = req.response
        
        return csv_content
        
    
    
    def solve_csv(self) -> str:
        """
        Returns a CSV string of the solves of the member. Formatted to account for the solves that are omitted.
        """
        csv_content = self.solve_csv_untouched()        
        
        lines = list(filter(lambda x: x.strip() != '', csv_content.split("\n")))
        problems_ids = set(map(lambda x: x.split(',')[2], lines))
        
        line_format = '0,01 Jan 70 (01:00),{problem_id},"random title"'
        
        for solve in self.solved_problems():
            if str(solve) not in problems_ids:
                lines.append(line_format.format(problem_id=solve))
        
        csv_content = "\n".join(lines)
        return csv_content
    

    def solve_count(self) -> int:

        """
        Returns the number of solves made by the member.
        """

        if self._pe_solve_count is not None:
            return self._pe_solve_count
        elif self._database_solve_count is not None:
            return self._database_solve_count
        
        self.update_from_database()
        return self._database_solve_count
    

    def pe_solve_count(self) -> int:

        """
        Returns the number of solves made by the member, as seen on Project Euler.
        """

        if self._pe_solve_count is not None:
            return self._pe_solve_count
        
        self.update_from_friend_list()
        if self._pe_solve_count is None:
            raise ValueError("_pe_solve_count should not be None after an update from friend list.")

        return self._pe_solve_count
        

    def database_solve_count(self) -> int:

        """
        Returns the number of solves made by the member in the database.
        This can be different from the number of solves on Project Euler during databases update.
        """

        if self._database_solve_count is not None:
            return self._database_solve_count
        
        self.update_from_database()
        if self._database_solve_count is None:
            raise ValueError("_database_solve_count should not be None after an update from database.")

        return self._database_solve_count
    

    def solve_array(self) -> List[bool]:

        """
        Returns an array of boolean: [b_1, ..., b_last_problem] where every True represents a problem solved
        """

        if self._pe_solve_array is not None:
            return self._pe_solve_array
        elif self._database_solve_array is not None:
            return self._database_solve_array
        
        self.update_from_database()
        if self._database_solve_array is None:
            raise ValueError("_database_solve_array should not be None after update from database.")

        return self._database_solve_array
    

    def pe_solve_array(self) -> List[bool]:

        """
        Returns an array of boolean: [b_1, ..., b_last_problem] where every True represents a problem solved,
        according to Project Euler's values.
        """

        if self._pe_solve_array is not None:
            return self._pe_solve_array
        
        self.update_from_friend_list()
        if self._pe_solve_array is None:
            raise ValueError("_pe_solve_array should not be None after update from friend list.")

        return self._pe_solve_array


    def database_solve_array(self) -> List[bool]:

        """
        Returns an array of boolean: [b_1, ..., b_last_problem] where every True represents a problem solved,
        according to the database's values.
        """
        
        if self._database_solve_array is not None:
            return self._database_solve_array
        
        self.update_from_database()
        if self._database_solve_array is None:
            raise ValueError("_database_solve_array should not be None after update from database.")

        return self._database_solve_array
    

    def has_solved(self, problem: int) -> bool:

        """
        With a problem id, returns whether the member has solved this problem or not.
        """

        if problem == 0:
            return False

        if problem < 0:

            problem = -problem
            if problem - 1 >= len(self.solve_bonus_array()):
                return False
            return self.solve_bonus_array()[problem - 1]

        if problem > 0:

            if problem - 1 >= len(self.solve_array()):
                return False
            return self.solve_array()[problem - 1]
    

    def award_count(self) -> int:

        """
        Returns the number of awards, classic ones and forum post ones
        """

        if self._pe_award_count is not None:
            return self._pe_award_count
        elif self._database_award_count is not None:
            return self._database_award_count
        
        self.update_from_database()
        return self._database_award_count
    

    def pe_award_count(self) -> int:

        """
        Returns the number of awards according to Project Euler.
        """

        if self._pe_award_count is not None:
            return self._pe_award_count
        
        self.update_from_award_list()
        if self._pe_award_count is None:
            raise ValueError("_pe_award_count should not be None after update from award list.")

        return self._pe_award_count
    

    def database_award_count(self) -> int:

        """
        Returns the number of awards according to the Database.
        """

        if self._database_award_count is not None:
            return self._database_award_count
        
        self.update_from_database()
        if self._database_award_count is None:
            raise ValueError("_database_award_count should not be None after update from database.")

        return self._database_award_count
        

    def award_array(self) -> Tuple[List[bool], List[bool], List[bool]]:

        """
        Returns an array with the awards, like
        ([True, False, ...], [True, False], [True, False, ...])
        Where each boolean represents if the award has been obtained
        
        First array is for main awards and second for forum awards
        Use pe_api.get_awards_specs to get the names of the awards
        """

        if self._pe_award_array is not None:
            return self._pe_award_array
        elif self._database_award_array is not None:
            return self._database_award_array
        
        self.update_from_database()
        return self._database_award_array
    
    
    def pe_award_array(self) -> Tuple[List[bool], List[bool], List[bool]]:
        
        if self._pe_award_array is not None:
            return self._pe_award_array
        
        self.update_from_award_list()
        if self._pe_award_array is None:
            raise ValueError("_pe_award_array should not be None after update from award list.")

        return self._pe_award_array
    
    
    def database_award_array(self) -> Tuple[List[bool], List[bool], List[bool]]:
        
        if self._database_award_array is not None:
            return self._database_award_array
        
        self.update_from_database()
        if self._database_award_array is None:
            raise ValueError("_database_award_array should not be None after update from award list.")

        return self._database_award_array
    
    
    def kudo_count(self) -> int:

        """
        Return the total kudo count
        """

        if self._pe_kudo_count is not None:
            return self._pe_kudo_count
        elif self._database_kudo_count is not None:
            return self._database_kudo_count
        
        self.update_from_post_page()
        return self._database_kudo_count
        
        
    def pe_kudo_count(self) -> int:

        """
        Returns the number of kudo that this user has.
        """
        
        if self._pe_kudo_count is not None:
            return self._pe_kudo_count
        
        self.update_from_post_page()
        if self._pe_kudo_count is None:
            raise ValueError("_pe_kudo_count should not be None after update from post page.")

        return self._pe_kudo_count
    
    
    def database_kudo_count(self) -> int:

        """
        Returns the number of kudo that this user has according to the database.
        """

        if self._database_kudo_count is not None:
            return self._database_kudo_count
        
        self.update_from_database_kudo()
        if self._database_kudo_count is None:
            raise ValueError("_database_kudo_count should not be None after update from kudo database.")

        return self._database_kudo_count
    
    
    def kudo_array(self) -> List[Tuple[int, int]]:

        """
        The list of kudos, in an array like [(107, 5), (108, 2)]
        If the user has 5 kudos for their post on 107 and 2 for 108
        """

        if self._pe_kudo_array is not None:
            return self._pe_kudo_array
        elif self._database_kudo_array is not None:
            return self._database_kudo_array
        
        self.update_from_database_kudo()
        return self._database_kudo_array
        

    def pe_kudo_array(self) -> List[Tuple[int, int]]:
        
        if self._pe_kudo_array is not None:
            return self._pe_kudo_array
        
        self.update_from_post_page()
        if self._pe_kudo_array is None:
            raise ValueError("_pe_kudo_array should not be None after update from post page.")

        return self._pe_kudo_array


    def has_kudos_in_database(self) -> bool:

        temp_query = f"SELECT * FROM pe_posts WHERE username = '{self.username()}';"
        query_result = pe_database.query_single(temp_query)

        return len(query_result) > 0
    

    def database_kudo_array(self) -> List[Tuple[int, int]]:
        
        if self._database_kudo_array is not None:
            return self._database_kudo_array
        
        self.update_from_database_kudo()
        if self._database_kudo_array is None:
            raise ValueError("_database_kudo_array should not be None after update from kudo database.")

        return self._database_kudo_array
        

    def level(self) -> int:
        """
        Returns the level of the member. This is only `number_of_solves // 25`.
        """
        if self._level is None:
            self.update_from_database()
        return self._level


    def solve_bonus_array(self) -> List[bool]:

        if self._pe_bonus_array is not None:
            return self._pe_bonus_array
        elif self._database_bonus_array is not None:
            return self._database_bonus_array

        self.update_from_friend_list()
        if self._pe_bonus_array is None:
            raise ValueError("_pe_bonus_array should not be None after update from friend list.")

        return self._pe_bonus_array


    def pe_solve_bonus_array(self) -> List[bool]:

        if self._pe_bonus_array is not None:
            return self._pe_bonus_array

        self.update_from_friend_list()
        if self._pe_bonus_array is None:
            raise ValueError("_pe_bonus_array should not be None after update from friend list.")

        return self._pe_bonus_array


    def database_solve_bonus_array(self) -> List[bool]:

        if self._database_bonus_array is not None:
            return self._database_bonus_array

        self.update_from_database()
        if self._database_bonus_array is None:
            raise ValueError("_database_bonus_array should not be None after update from database.")

        return self._database_bonus_array


    def discord_id(self) -> str:
        """
        Returns the discord ID of the member. It might be an empty string if not self.is_discord_linked()
        """
        if self._discord_id is None:
            self.update_from_database()
        return self._discord_id
    

    def position_in_discord(self) -> tuple[int, int]:

        """
        Returns the position in the discord (ranking by solve count)
        and the number of member in the discord
        """

        current_rank = 1
        all_members = Member.members_database()
        valid_members = 0

        if not self.is_discord_linked():
            return -1, -1

        member: Member
        for member in all_members:

            if not member.is_discord_linked():
                continue
            valid_members += 1

            if member.solve_count() > self.solve_count():
                current_rank += 1
        
        return current_rank, valid_members

        
    def is_discord_linked(self, connection = None, data = None) -> bool:

        """
        Returns true if the account is linked to a project euler account, 
        that is, if there is an entry in the database with the corresponding discord_id
        """
        
        dis_id = self.discord_id()
        if dis_id == "":
            return False
        
        if self._username is not None:
            return True
        
        if data is None:
            temp_query = f"SELECT * FROM members WHERE discord_id='{dis_id}';"
            data = pe_database.query_option(temp_query, connection)

        return len(data) >= 1 and dis_id != ""


    def is_account_in_database(self, connection = None) -> bool:

        """
        Returns whether a given member is in the database.
        """

        key_id, value_id = self.identity()
        temp_query = f"SELECT * FROM members WHERE {key_id}='{value_id}';"
        
        return len(pe_database.query_option(temp_query, connection)) >= 1
        

    def have_solves_changed(self) -> bool:
        """
        Are the solves of this member not the same on the website and in the database.
        """
        return not (self.pe_solve_count() == self.database_solve_count())
    

    def have_awards_changed(self) -> bool:
        """
        Are the awards of this member not the same on the website and in the database.
        """
        return not (self.pe_award_count() == self.database_award_count())
    

    def have_kudos_changed(self) -> bool:
        """
        Are the kudos of this member not the same on the website and in the database.
        """
        return not (self.pe_kudo_count() == self.database_kudo_count())
    

    def get_new_solves(self) -> List[Solve]:

        """
        Returns a list of the problems that have just been solved by a member.
        """

        if not self.have_solves_changed():
            return []
        
        project_euler_data = self.pe_solve_array()
        database_data = self.database_solve_array()
        
        max_len = len(project_euler_data)
        
        new_solves = []
        
        for i in range(max_len):
            
            if not project_euler_data[i]:
                continue
            
            if project_euler_data[i] == True and (i >= len(database_data) or database_data[i] == False):
                new_solves.append(
                    Solve(
                        _problem=Problem(i+1),
                        _problem_id=i+1,
                        _member=self,
                        _unixtime=now_unix(),
                        _unix_is_accurate=False
                    )
                )
            
        return new_solves
    

    def get_new_kudos(self) -> List[Tuple[int, int]]:

        """
        Returns a list of tuples. Each element has the format: (post_id, new_number_of_kudos)
        """

        if not self.have_kudos_changed():
            return []
        
        project_euler_data = self.pe_kudo_array()
        database_data = self.database_kudo_array()
        
        database_dict = {el[0]: el[1] for el in database_data}
        
        new_kudos = []
        
        for post in project_euler_data:
            
            post_id = post[0]
            post_kudos = post[1]
            
            if post_id not in database_dict.keys():
                new_kudos.append(post)
            elif post_kudos != database_dict[post_id]:
                new_kudos.append((post_id, post_kudos - database_dict[post_id]))
            
        return new_kudos
    

    def get_new_awards(self) -> Tuple[List[int], List[int], List[int]]:

        """
        Get a 3-tuple (one element for each category of awards) each element containing a list of the indexes
        of newly acquired awards.
        """

        if not self.have_awards_changed():
            return [], [], []
        
        project_euler_data = self.pe_award_array()
        database_data = self.database_award_array()
        
        first_len = len(project_euler_data[0])
        second_len = len(project_euler_data[1])
        third_len = len(project_euler_data[2])
        
        new_awards = ([], [], [])
        
        if len(project_euler_data) != 3:
            raise Exception("project euler data is not long enough", project_euler_data, self._username)
        
        if len(database_data) != 3:
            raise Exception("database data is not long enough", database_data, self._username)
        
        for i in range(first_len):
            if project_euler_data[0][i] == True and database_data[0][i] == False:
                new_awards[0].append(i)
            
        for i in range(second_len):
            if project_euler_data[1][i] == True and database_data[1][i] == False:
                new_awards[1].append(i)

        for i in range(third_len):
            if project_euler_data[2][i] == True and database_data[2][i] == False:
                new_awards[2].append(i)
            
        return new_awards
        

    def push_kudo_to_database(self) -> None:

        """
        Updates the kudo database according to the kudos on Project Euler's kudo page.
        """

        kudos = self.pe_kudo_array()
        
        formatted = "|".join(list(map(
            lambda el: "n".join(list(map(str, el))), kudos
        )))

        is_in_database_query = f"SELECT * FROM pe_posts WHERE username = '{self.username()}';"
        is_in_database_response = pe_database.query_single(is_in_database_query)
        is_in_database = len(is_in_database_response) > 0

        if is_in_database:
            temp_query = f"UPDATE pe_posts SET kudos = {self.kudo_count()}, posts_list = '{formatted}' \
                WHERE username = '{self.username()}';"
        else:
            temp_query = f"INSERT INTO pe_posts (username, posts_number, kudos, posts_list) \
                VALUES ('{self.username()}', 0, {self.kudo_count()}, '{formatted}');"

        pe_database.query_single(temp_query)


    def push_basics_to_database(self) -> None:

        """
        Updates the database with basic information that were collected about the member.
        """

        solved = self.pe_solve_count()
        solve_list = "".join([
            "01"[boolean] for boolean in self.pe_solve_array()
        ])
        solve_bonus_list = "".join([
            "01"[boolean] for boolean in self.pe_solve_bonus_array()
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
                "".join(["01"[b] for b in awards_array[1]]),
                "".join(["01"[b] for b in awards_array[2]])
            ])
            
            temp_query = f"INSERT INTO members (username, nickname, country, language, solved, \
                solve_list, discord_id, awards, awards_list, private, solve_list_bonus) VALUES (\
                '{username}', '{nickname}', '{country}', '{language}', \
                {solved}, '{solve_list}', '', {awards}, '{awards_list}', 0, '{solve_bonus_list}');"
                
        else:
            temp_query = f"UPDATE members SET nickname='{nickname}', \
                country='{country}', language='{language}', solved={solved},\
                solve_list='{solve_list}', solve_list_bonus='{solve_bonus_list}' \
                WHERE username='{username}';"
                
        pe_database.query_single(temp_query)
        

    def push_awards_to_database(self) -> None:

        """
        Updates the database with information about the awards of the member.
        """

        username = self.username()
        
        awards_array = self.pe_award_array()
        awards = self.pe_award_count()
        awards_list = "|".join([
            "".join(["01"[b] for b in awards_array[0]]),
            "".join(["01"[b] for b in awards_array[1]]),
            "".join(["01"[b] for b in awards_array[2]])
        ])
        
        temp_query = f"UPDATE members SET awards={awards}, \
            awards_list='{awards_list}' WHERE username='{username}';"

        pe_database.query_single(temp_query)
        

    @staticmethod
    def members_friends() -> List['Member']:

        """
        Returns a list of all the members in the friend list of the bot on project euler
        """

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
    def members_database() -> List['Member']:

        """
        Returns a list of all the members in the friend list of the bot in the database
        """

        database_data = pe_database.query_single("SELECT * FROM members;")

        usernames = list(map(
            lambda member: member["username"],
            database_data
        ))
        
        result_list = []
        
        for username in usernames:
            
            if username == "":
                continue
            
            current = Member(_username=username)
            current.update_from_database(data = database_data)
            
            result_list.append(current)
            
        return result_list
    

    @staticmethod
    def members() -> List['Member']:
        
        """ 
        Returns a list of all the members that the bot has ever heard of. A list of `pe_api.Member` objects 
        """

        database_data = pe_database.query_single("SELECT * FROM members;")
        project_euler_data = ProjectEulerRequest("https://www.projecteuler.net/minimal=friends")

        database_usernames = list(map(
            lambda member: member["username"],
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
        
            current = Member(_username=username)
            current.update_from_friend_list(project_euler_data)
            
            if username in database_usernames:
                current.update_from_database(data = database_data)
                
            result_list.append(current)
            
        return result_list
    

    def solved_problems(self) -> List[int]:
        """
        Returns a list like [102, 105] if the member has solved only 102 and 105
        """       
        solves = []
        for index, solved in enumerate(self.solve_array()):
            if solved:
                solves.append(index + 1)
        return solves


    def unsolved_problems(self) -> List[int]:
        """
        Returns a list like [763] if the member only has 763 left to
        """
        not_solves = []
        for index, solved in enumerate(self.solve_array()):
            if not solved:
                not_solves.append(index + 1)
        return not_solves
    

    def make_problem_unsolved(self, problem: int) -> None:

        """
        Takes a member and removes one its solves. Particularly useful for testing and debugging.
        """

        cur_solves = "".join(["01"[b] for b in self.database_solve_array()])
        cur_solves = cur_solves[:(problem - 1)] + "0" + cur_solves[(problem - 1) + 1:]

        temp_query = f"UPDATE members SET solve_list = '{cur_solves}', solved = {self.solve_count() - 1} \
            WHERE username = '{self.username()}';"

        pe_database.query_single(temp_query)
        


class Challenge:
    
    
    def __init__(self, from_member: Member, to_member: Member, unix_start: int, hours_duration: int, problem: Problem):
        
        self.from_member: Member = from_member
        self.to_member: Member = to_member
        self.unix_start: int = unix_start
        self.hours_duration: int = hours_duration
        self.problem: Problem = problem
        
        self.accepted: bool = False
        self.unix_accept_time: Optional[int] = None
        self.challenge_id: Optional[int] = None
        
        
        
    @staticmethod
    def all_challenges(search_query: Optional[str]) -> List['Challenge']:
        
        data = pe_database.query_single("SELECT * FROM challenges;" if search_query is None else search_query)
        
        output_data = []
        for row in data:
            
            from_member = Member(_username=row["from_member"])
            to_member = Member(_username=row["to_member"])
            unix_start = row["unix_start"]
            hours_duration = row["hours_duration"]
            problem = Problem(row["problem"])
            
            challenge = Challenge(from_member, to_member, unix_start, hours_duration, problem)
            challenge.challenge_id = row["id"]
            challenge.accepted = row["accepted"] == 1
            challenge.unix_accept_time = None if row["unix_accept_time"] == -1 else row["unix_accept_time"]
            
            output_data.append(challenge)
            
        return output_data
            

    def register_in_database(self) -> None:
        
        from_name = self.from_member.username()
        to_name = self.to_member.username()
        problem_id = self.problem.problem_id()
        
        accepted = 1 if self.accepted else 0
        unix_accept_time = -1 if self.unix_accept_time is None else self.unix_accept_time
        
        query = f"INSERT INTO challenges (from_member, to_member, unix_start, hours_duration, problem, accepted, unix_accept_time) \
            VALUES ('{from_name}', '{to_name}', {self.unix_start}, {self.hours_duration}, {problem_id}, {accepted}, {unix_accept_time});"
        
        pe_database.query_single(query)
        
        query_retrieve_row = f"SELECT id FROM challenges WHERE accepted={accepted} AND unix_start={self.unix_start} AND \
            from_member='{from_name}' AND to_member='{to_name}' ORDER BY id DESC;"
        rows_in_database = pe_database.query_single(query_retrieve_row)
        
        self.challenge_id = rows_in_database[0]["id"]
        
    
    def accept(self):
        
        """
        Will mark the challenge as accepted.
        """
    
        current_time = now_unix()
        query = f"UPDATE challenges SET accepted=1, unix_accept_time={current_time} WHERE id={self.challenge_id};"
        pe_database.query_single(query)
        
        self.unix_accept_time = current_time
        self.accepted = True    
        
    
    @staticmethod
    def get_by_id(challenge_id: int) -> Optional['Challenge']:
        
        all_challenges = Challenge.all_challenges(f"SELECT * FROM challenges WHERE id={challenge_id};")
        if len(all_challenges) == 0:
            return None
        
        challenge = all_challenges[0]
        return challenge
        
    
    @staticmethod
    def accept_by_id(challenge_id: int):
        
        challenge = Challenge.get_by_id(challenge_id)
        if challenge is None:
            raise Exception("Could not find the challenge")
        
        challenge.accept()

        
        
        
        
        


def update_process() -> Optional[List[Dict[str, Any]]]:
    
    members: List[Member] = Member.members()
    skipped_member_count = 0
    
    new_changes = []

    
    for member in members:
        
        if member.have_solves_changed():
            
            new_solves = member.get_new_solves()
            console.log(f"New solve(s) for {member.username()}: {[s.problem_id() for s in new_solves]}")
            member.push_basics_to_database()

            new_awards = None
            if member.have_awards_changed():
                new_awards = member.get_new_awards()
                console.log(f"New award(s) for {member.username()}: {new_awards}")
                member.push_awards_to_database()
            
            new_changes.append({"member": member, "solves": new_solves, "awards": new_awards})
            
        else:
            skipped_member_count += 1
            
    console.log(f"Skipped {skipped_member_count} members")
    console.log(new_changes)
    return new_changes


def push_solve_to_database(member: Member, solve: Problem):

    pb_def = problem_def(solve.problem_id())
    position = pb_def[3]

    temp_query = "INSERT INTO solves (member, problem, solve_date, position) VALUES ('{0}', {1}, datetime('now'), {2})"
    temp_query = temp_query.format(member.username(), solve.problem_id(), position)
    pe_database.query_single(temp_query)






# Return array of the form ['n', 'Problem title', Unix Timestamp of publish, 'nb of solves', '0']
# Careful as all values in the array are string, not ints
def problem_def(n):
    data = ProjectEulerRequest(BASE_URL.format("problems")).response
    lines = data.split("\n")
    pb = lines[n].replace("\r", "")
    specs = pb.split("##")
    return specs


# Return array of the form [problem_1, problem_2, ...., problem_last]
# With each problem being of the kind ['n', 'Problem title', Unix Timestamp of publish, 'nb of solves', '0']
# Careful as all values in the array are string, not ints
def problems_list():
    data = ProjectEulerRequest(BASE_URL.format("problems")).response.split("\n")
    data = list(map(lambda element: element.replace("\r", "").split("##"), data))
    return data


# Return last problem available, including the ones in the recent tab
def last_problem():
    data = ProjectEulerRequest(BASE_URL.format("problems")).response
    return len(data.split("\n")) - 2


def last_problem_database():
    data = pe_database.query_single("SELECT MAX(len) AS most_solve FROM (SELECT LENGTH(solve_list) AS len FROM members) AS T;")
    return data[0]["most_solve"]



# Returns False if discord_id is not in the database, else returns the project euler username
def project_euler_username(discord_id, connection=None) -> str:

    temp_query = f"SELECT * FROM members WHERE discord_id='{discord_id}';"
    data = pe_database.query_option(temp_query, connection=connection)

    if len(data) < 1:
        return ""

    return data[0]["username"]


# Essentially does the same thing as get_all_members_who_solved, but returns the entire profiles
# Returns a list with format [[username1: str, discord_id1: str], [username2: str, discord_id2: str], ....]
def get_all_discord_profiles_who_solved(problem: int):

    solvers = []

    try:
        members: List[Member] = Member.members()
    except Exception as _:
        members: List[Member] = Member.members_database()

    for member in members:

        if member.is_discord_linked() and member.has_solved(problem):
            solvers.append([member.username(), member.discord_id()])

    return solvers


# return a list of all the names of the awards
def get_awards_specs():
    url = NOT_MINIMAL_BASE_URL.format("progress;show=awards")
    data = ProjectEulerRequest(url).response
    soup = BeautifulSoup(data, 'html.parser')

    awards_container = soup.find(id="awards_section").find_all("div", recursive=False)

    div1 = awards_container[0]
    div2 = awards_container[1]
    div3 = awards_container[2]

    all_awards = []

    problem_awards = div1.find_all(class_="tooltip inner_box")
    all_awards.append([problem.find_all(class_="strong")[0].text for problem in problem_awards])

    problem_publication = div2.find_all(class_="award_box")
    all_awards.append([problem.find_all(class_="strong")[0].text for problem in problem_publication])

    forum_awards = div3.find_all(class_="award_box")
    all_awards.append([problem.find_all(class_="strong")[0].text for problem in forum_awards])

    return all_awards


# Get the solves of the last few days in the database
def get_solves_in_database():

    connection = pe_database.open_connection()

    temp_query = "SELECT * FROM solves;"
    
    data = pe_database.query(temp_query, connection)
    pe_database.close_connection(connection)

    return data


# Get the global solves in the database
def get_global_solves_in_database():

    connection = pe_database.open_connection()

    temp_query = "SELECT id, solves, date_stat FROM global_stats"

    data = pe_database.query(temp_query, connection)
    pe_database.close_connection(connection)

    return data 


# Get the current global stats on the website
def get_global_stats():

    # Basic script to get the html code on a page
    problem_url = NOT_MINIMAL_BASE_URL.format("problem_analysis")
    problem_data = ProjectEulerRequest(problem_url).response
    problem_soup = BeautifulSoup(problem_data, 'html.parser')

    # This tag represents the column we wants
    problems = problem_soup.find_all(class_="equal_column")
    problems = list(map(lambda x: x.text, problems)) # Get the text of elements, no html tags
    problems = list(filter(lambda x: x != "Solved Exactly", problems)) # Remove colum names

    # Problem count
    problem_count = sum([(i + 1) * int(problems[i]) for i in range(len(problems))])
    
    # Again, basic requests to get html code
    level_url = NOT_MINIMAL_BASE_URL.format("levels")
    level_data = ProjectEulerRequest(level_url).response
    level_soup = BeautifulSoup(level_data, 'html.parser')

    # Format all this data
    levels = level_soup.find_all(class_="small_notice")
    levels = list(map(lambda x: x.text.split()[0], levels)) # format <div>4054 members</div>
    
    # Get levels count
    level_count = sum([(i + 1) * int(levels[i]) for i in range(len(levels))])    

    # Basic script to get the awards stats
    award_url = NOT_MINIMAL_BASE_URL.format("awards")
    award_data = ProjectEulerRequest(award_url).response
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
    connection = pe_database.open_connection()

    # The query to retrieve saved statistics
    temp_query = "SELECT * FROM global_constants;"
    previous_data = pe_database.query(temp_query, connection=connection)

    # Ensure the retrieve was successful
    if len(previous_data) == 1:
        previous_data = previous_data[0]
    else:
        pe_database.close_connection(connection)
        return False

    # Assert the current day has not already been retrieved
    current_day = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
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
    temp_query = "INSERT INTO global_stats (solves, levels, awards, date_stat) VALUES ({0}, {1}, {2}, datetime('now'));"
    temp_query = temp_query.format(problem_diff, level_diff, award_diff)
    pe_database.query(temp_query, connection)

    # Update the last data
    temp_query = "UPDATE global_constants SET solves_count = {0}, levels_count = {1}, awards_count = {2}, saved_date = datetime('now');"
    temp_query = temp_query.format(problem_count, level_count, award_count)
    pe_database.query(temp_query, connection)

    # Alert my phone that everything has gone as planned
    phone_api.bot_success("Added stats for day " + current_day)
    pe_database.close_connection(connection)

    return True # Everything went fine


def get_fastest_solvers(problem: int):

    page_url = NOT_MINIMAL_BASE_URL.format(f"fastest={problem}")
    solvers_data = ProjectEulerRequest(page_url).response
    solvers_soup = BeautifulSoup(solvers_data, 'html.parser')

    if "No data available" in solvers_soup.text:
        return {}
    
    rows = solvers_soup.find_all(class_="grid")[0].find_all("tr")
    number_of_solvers = len(rows) - 1

    data = {}

    for rank, element in enumerate(rows, start = 0): # starts at 0 because we want to exclude row "0" being the "user, country, language, time"
        
        lines = element.find_all("td")

        if len(lines) != 5:
            continue

        """
        lines[0] = rank
        lines[1] = username
        lines[2] = country
        lines[3] = language
        lines[4] = time
        """

        username = lines[1].text

        try_nickname = lines[1].find_all("span")
        if len(try_nickname) != 0:
            username = lines[1].find("span").get("title")

        solve_time_string = lines[4].text

        correspondences = {
            "second": 1,
            "minute": 60,
            "hour": 3600,
            "day": 86400,
            "week": 604800,
            "year": 31536000
        }

        solve_time = 0
        for k in correspondences.keys():
            for part_str in solve_time_string.split(", "):
                
                if k in part_str:
                    solve_time += correspondences[k] * int(part_str.split()[0])

        data[str(rank)] = {"username": username, "solve_time": solve_time}

    return data


def update_fastest_solves(starting_problem: int = 277):

    last_pb = last_problem()

    data_filename = "saved_data/fastest_solves.json"

    with open(data_filename, "r") as f:
        whole_data = json.load(f)

    console.log("Refreshing data for solvers.")

    wait_time = 1

    for problem in range(starting_problem, last_pb + 1):
        
        data = get_fastest_solvers(problem)
        whole_data[problem] = data
        
        console.log(problem)
        time.sleep(wait_time)

    with open(data_filename, "w") as f:
        json.dump(whole_data, f, indent=4)




if __name__ == "__main__":
    pass
    
    
