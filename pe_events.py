import json
import time
import pe_api

import copy

import random


def get_event_data(event: str):
    
    with open(f"events/{event}/data.json", "r") as f:
        content = json.loads(f.read())
    return content


def push_event_data(event: str, data: dict):
    
    with open(f"events/{event}/data.json", "w") as f:
        f.write(json.dumps(data, indent=4))


class eventSoPE:
    
    def __init__(self) -> None:
        self.data = get_event_data("SoPE")

    def is_problem_solved(self, problem: int) -> bool:
        return str(problem) in self.data["solves"].keys()
    
    def get_solver(self, problem: int) -> tuple:
        if not self.is_problem_solved(problem):
            return None
        return self.data["solves"][str(problem)].values()
        
    def set_solver(self, problem: int, username: str, timestamp: int) -> None:
        self.data["solves"][str(problem)] = {"username": username, "timestamp": timestamp}
        push_event_data("SoPE", self.data)
        
    def set_solver_option(self, problem: int, username: str, timestamp: int) -> None:
        if not self.is_problem_solved(problem):
            self.set_solver(problem, username, timestamp)
            
    def starting_timestamp(self):
        return self.data["timestamp_start"]
            
    def scores(self):
        
        problems = pe_api.PE_Problem.complete_list()
        score_list = {}
        
        problem: pe_api.PE_Problem
        for problem in problems:
            
            problem_id = problem.problem_id
            if not self.is_problem_solved(problem_id):
                continue
                
            solver_name, timestamp = self.get_solver(problem_id)
            time_to_solve = timestamp - self.starting_timestamp()
            
            difficulty = problem.difficulty_rating if problem.difficulty_rating is not None else 70
            
            difficulty_score = max(5, (difficulty // 15) * 5)
            day_score = time_to_solve // 86400
            
            if solver_name not in score_list:
                score_list[solver_name] = 0
                
            score_list[solver_name] += day_score + difficulty_score
            
        return score_list
    

class eventMonthly1:

    @staticmethod
    def get_refresh_rate_easy():
        return 22 * 3600
    
    @staticmethod
    def get_refresh_rate_medium():
        return 46 * 3600
    
    @staticmethod
    def get_refresh_rate_hard():
        return 70 * 3600

    def __init__(self) -> None:
        self.event_name = "monthly1"
        self.data = get_event_data(self.event_name) 
        self.announce_channel_name = "private-bot"

    def past_problems(self) -> list:
        return list(map(int, self.data["solves"].keys()))
    
    def current_problem(self, diff_range: int) -> int:
        return int(self.data[["easy", "medium", "hard"][diff_range]]["current_problem"])

    def last_announcement(self, diff_range: bool) -> int:
        return int(self.data[["easy", "medium", "hard"][diff_range]]["last_timestamp"])

    def switch_to_new_problem(self, diff_range: int):

        """
        Returns an announcement message, that will go up the function calls tree, until it reaches
        pe_discord_api.py, to be announced in channels
        """

        max_problem = pe_api.last_problem()
        choice = -1
        already_used = self.past_problems()

        problems = pe_api.PE_Problem.complete_list()
        
        while True:

            choice = random.randint(1, max_problem)

            if choice == -1 or choice in already_used:
                continue

            current_problem: pe_api.PE_Problem = problems[choice - 1]
            if current_problem.difficulty_rating == None:
                continue

            if diff_range == 0 and not (current_problem.difficulty_rating <= 40):
                continue

            if diff_range == 1 and not (45 <= current_problem.difficulty_rating <= 75):
                continue

            if diff_range == 2 and not (current_problem.difficulty_rating >= 80):
                continue

            break
        
        difficulty_text = ["easy", "medium", "hard"][diff_range]
        difficulty_category_text = f" with difficulty `{difficulty_text}`"
        announce_message_text = f"Switching to a new problem for the current event {difficulty_category_text}\
: be the first to solve [**{choice}**](<https://projecteuler.net/problem={choice}>): '{current_problem.name}'!"

        self.data["solves"][str(choice)] = {
            "solver_username": "None",
            "timestamp_announced": str(int(time.time())),
            "timestamp_solved": "-1"
        }
        self.data[difficulty_text]["last_timestamp"] = str(int(time.time()))
        self.data[difficulty_text]["current_problem"] = str(choice)

        push_event_data(self.event_name, self.data)
        return [announce_message_text]
    
    def current_problem_solved_by(self, member: pe_api.Member, diff_range: int):
        
        current = self.current_problem(diff_range=diff_range)
        self.data["solves"][str(current)]["timestamp_solved"] = str(int(time.time()))
        self.data["solves"][str(current)]["solver_username"] = member.username()

        problem = pe_api.PE_Problem.complete_list()[current - 1]

        push_event_data(self.event_name, self.data)
        previous_message = self.switch_to_new_problem(diff_range)
        
        announced_message_text = f"User {member.username_ping()} just solved problem {current}! " + previous_message[0]
        
        return [announced_message_text]
    
    def scores(self):

        members = {}
        problems = pe_api.PE_Problem.complete_list()

        solves = self.data["solves"]

        for key in solves.keys():
            
            username = solves[key]["solver_username"]
            if username == "None":
                continue

            credited_points = 20 + (int(solves[key]["timestamp_solved"]) - int(solves[key]["timestamp_solved"])) // 3600
            
            if problems[int(key) - 1].difficulty_rating >= 80:
                credited_points *= 3
            elif problems[int(key) - 1].difficulty_rating >= 45:
                credited_points *= 2

            if username in members:
                members[username] += credited_points
            else:
                members[username] = credited_points

        return sorted(list(members.items()), key=lambda el: el[1], reverse=True)
    
    @staticmethod
    def update_event(profiles):

        event = eventMonthly1()
        messages_to_send = []

        profile: pe_api.Member
        for profile in profiles:        
            
            member: pe_api.Member = profile["member"]
            solves = profile["solves"]
            awards = profile["awards"]

            if event.current_problem(diff_range=0) in solves:
                for message in event.current_problem_solved_by(member, diff_range=0):
                    messages_to_send.append((message, "TEST_CHANNEL"))

            if event.current_problem(diff_range=1) in solves:
                for message in event.current_problem_solved_by(member, diff_range=1):
                    messages_to_send.append((message, "TEST_CHANNEL"))

            if event.current_problem(diff_range=2) in solves:
                for message in event.current_problem_solved_by(member, diff_range=2):
                    messages_to_send.append((message, "TEST_CHANNEL"))

        return messages_to_send


    @staticmethod
    def update_events_without_profiles():

        event = eventMonthly1()
        messages_to_send = []

        if int(time.time()) - event.last_announcement(diff_range=0) > eventMonthly1.get_refresh_rate_easy():
            for message in event.switch_to_new_problem(diff_range=0):
                messages_to_send.append((message, "TEST_CHANNEL"))

        if int(time.time()) - event.last_announcement(diff_range=1) > eventMonthly1.get_refresh_rate_medium():
            for message in event.switch_to_new_problem(diff_range=1):
                messages_to_send.append((message, "TEST_CHANNEL"))

        if int(time.time()) - event.last_announcement(diff_range=2) > eventMonthly1.get_refresh_rate_hard():
            for message in event.switch_to_new_problem(diff_range=2):
                messages_to_send.append((message, "TEST_CHANNEL"))

        return messages_to_send
    
    @staticmethod
    def leaderboard():
        event = eventMonthly1()
        scores = event.scores()
        leaderboard_data = [(element[0], element[1]) for element in scores]
        return leaderboard_data


class eventSmoothen:

    @staticmethod
    def get_smooth_score(solve_list: list) -> float:

        """
        takes a list of solves, an array of booleans
        """

        def perimeter(solve_list: list) -> int:
            
            total = 0

            for index, was_solved in enumerate(solve_list, start=1):

                if not was_solved:
                    continue

                total += 4
                if ((index - 1) % 100 + 1) > 10:
                    neighbor = index - 10 - 1
                    if neighbor < len(solve_list) and solve_list[neighbor]:
                        total -= 1

                if ((index - 1) % 10 + 1) < 10:
                    neighbor = index + 1 - 1
                    if neighbor < len(solve_list) and solve_list[neighbor]:
                        total -= 1

                if ((index - 1) % 100 + 1) < 90:
                    neighbor = index + 10 - 1
                    if neighbor < len(solve_list) and solve_list[neighbor]:
                        total -= 1
                        
                if ((index - 1) % 10 + 1) > 1:
                    neighbor = index - 1 - 1
                    if neighbor < len(solve_list) and solve_list[neighbor]:
                        total -= 1

            return total


        def area(solve_list: list) -> int:
            return solve_list.count(True)

        ar = area(solve_list)
        pr = perimeter(solve_list)

        if pr == 0:
            return 0

        return  10000 * ar / pr



    def __init__(self) -> None:
        self.event_name = "smoothen"
        self.data = get_event_data(self.event_name) 
        self.announce_channel_name = "private-bot"

    @staticmethod
    def update_event_in_message(member: pe_api.Member, problem_id):

        if member.private():
            return ""

        ev = eventSmoothen()
        data = get_event_data(ev.event_name)

        current_solve_array = member.solve_array()
        previous_solve_array = copy.deepcopy(current_solve_array)

        previous_solve_array[problem_id - 1] = False

        previous_score = eventSmoothen.get_smooth_score(previous_solve_array)
        current_score = eventSmoothen.get_smooth_score(current_solve_array)

        difference = int(current_score) - int(previous_score)

        does_match = lambda element: element["username"] == member.username_option() and element["problem_id"] == problem_id

        if not any(list(map(does_match, data["solves"]))):

            data["solves"].append({
                "username": member.username_option(), 
                "problem_id": problem_id, 
                "timestamp": int(time.time()),
                "points_earned": difference 
            })

            push_event_data(ev.event_name, data)
        

        if difference > 0:
            return f"(+{difference})"
        else:
            return ""
            return f"(-{-difference})"




    @staticmethod
    def update_event(profiles): 
        return [] 

    @staticmethod
    def update_events_without_profiles():
        return []
    
    @staticmethod
    def leaderboard():
        
        ev = eventSmoothen()
        data = get_event_data(ev.event_name)

        points_earned_by_username = {}

        for solve in data["solves"]:
            
            username = solve["username"]
            points = solve["points_earned"]

            if points < 0:
                continue

            if username in points_earned_by_username.keys():
                points_earned_by_username[username] += points
            else:
                points_earned_by_username[username] = points

        return [(username, points_earned_by_username[username]) for username in points_earned_by_username.keys()]
            



            
        


def update_events_without_profiles():

    messages_to_send = []
    # messages_to_send += eventMonthly1.update_events_without_profiles()

    return messages_to_send


def update_events(profiles):
    
    messages_to_send = []
    # messages_to_send += eventMonthly1.update_event(profiles)
    messages_to_send += eventSmoothen.update_event(profiles)

    return messages_to_send



if __name__ == "__main__":
    pass

    