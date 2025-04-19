import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import pe_api
import eulerbot
import sys


sys.argv = [None, "authentic.json"]    
eulerbot.setup()



def test_last_problem():
    
    last_problem = pe_api.last_problem()
    last_problem_db = pe_api.last_problem_database()
    
    assert last_problem == last_problem_db
    


# @pytest.mark.asyncio
def test_problem_object():

    problem = pe_api.Problem(50)
    last_problem = pe_api.last_problem()
    
    for id in [484, last_problem]:
        
        problem = pe_api.Problem(id)
        
        solves = problem.solves()
        diff = problem.difficulty()
        title = problem.title()
        solvers_in_discord = problem.solvers_in_discord()
        _unix = problem.unix_publication()
        _name = problem.name()
        _pb_id = problem.problem_id()
        
        assert isinstance(solves, int)
        assert isinstance(diff, int) or diff is None
        assert isinstance(title, str)
        assert isinstance(solvers_in_discord, list) and isinstance(solvers_in_discord[0], pe_api.Member)
        
    problems = pe_api.Problem.complete_list()
    assert len(problems) == last_problem


def test_member_simple_object():
    
    member1 = pe_api.Member(_username="Teyzer18")
    
    member1.is_account_in_database()
    member1.is_discord_linked()
    
    member1.discord_id()
    member1.country()
    member1.award_array()
    member1.award_count()
    member1.has_solved(55)
    
    member1.username()
    member1.username_option()
    member1.username_ping()
    member1.nickname()
    
    member1.favorite_problem()
    member1.identity()
    member1.level()
    
    member1.private()
    
    
def test_member_advanced_object():
    
    member1 = pe_api.Member(_username="Teyzer18")
    
    member1.unsolved_problems()
    
    member1.solve_csv()
    member1.solve_csv_untouched()
    
    member1.kudo_array()
    member1.kudo_count()
    
    member1.solve_bonus_array()
    member1.position_in_discord()
    
    
def member_pre_update():
    
    member = pe_api.Member(_username="Teyzer18")
    
    member.have_awards_changed()
    member.have_solves_changed()
    
    member.have_kudos_changed()
    
    member.get_new_awards()
    member.get_new_solves()
    
    member.get_new_kudos()
    
    
@patch("pe_api.Member.have_solves_changed")
@patch("pe_api.Member.get_new_solves")
@patch("pe_api.Member.push_basics_to_database")
@patch("pe_api.Member.have_awards_changed")
@patch("pe_api.Member.get_new_awards")
@patch("pe_api.Member.push_awards_to_database")
def test_update_process(mock_solves_changed, mock_get_new_solves, mock_push_basics, mock_have_awards, mock_get_awards, mock_push_awards):
    
    mock_solves_changed.return_value = True
    mock_get_new_solves.return_value = [15, 25, 300]
    mock_push_basics.return_value = True
    mock_have_awards.return_value = True
    mock_get_awards.return_value = ([], [], [])
    mock_push_awards.return_value = True

    value = pe_api.update_process()
    
    for element in value:
        assert "member" in element and "solves" in element and "awards" in element
    
    
    