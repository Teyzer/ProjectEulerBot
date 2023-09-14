import json
import time
import pe_api


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


def update_events(profiles):
    
    event = eventSoPE()

    profile: pe_api.Member
    for profile in profiles:
        
        m: pe_api.Member = profile["member"]
        
        if not m.is_discord_linked():
            continue
        
        username = m.username()
        solves = profile["solves"]
        
        for solve in solves:
            event.set_solver_option(solve, username, int(time.time()))


if __name__ == "__main__":
    
    event = eventSoPE()
    
    problems = pe_api.PE_Problem.complete_list()
    score_list = {}
    
    total_percentage_score = 0
    total_longevity_score = 0

    solver_count = {}

    problem: pe_api.PE_Problem
    for problem in problems:
        
        problem_id = problem.problem_id
        if not event.is_problem_solved(problem_id):
            continue
            
        solver_name, timestamp = event.get_solver(problem_id)
        time_to_solve = timestamp - event.starting_timestamp()
        
        difficulty = problem.difficulty_rating if problem.difficulty_rating is not None else 70
        
        difficulty_score = max(5, (difficulty // 15) * 5)
        day_score = time_to_solve // 86400
        
        if solver_name not in score_list:
            score_list[solver_name] = 0
            solver_count[solver_name] = 0
            
        score_list[solver_name] += day_score + difficulty_score
        solver_count[solver_name] += 1

        total_longevity_score += day_score
        total_percentage_score += difficulty_score

    print("Best scores:", sorted(score_list.items(), key=lambda el: el[1], reverse=True)[:10])
    print("Total score:", total_percentage_score + total_longevity_score, total_percentage_score, total_longevity_score)
    print("Total solves:", len(event.data["solves"]))
    print("Best solves:", sorted(solver_count.items(), key=lambda el: el[1], reverse=True)[:5])
    print("Hardest problem solved: #763 by philiplu")
    print("First to 1000 and 2000 landmark: shcarecrow")
    print("The saddest moment of the contest: rak1507 beaten by adamant on #128 by four minutes")
    print(", ".join(list(score_list.keys())))