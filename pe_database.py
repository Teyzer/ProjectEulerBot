import sqlite3
from sqlite3 import Cursor, Connection

from rich.console import Console
from typing import List, Dict, Any, Optional


from pe_global_objects import log


DATABASE_FILE = None
DB_TOTAL_REQUESTS = 0


def query(_query: str, connection: Connection) -> Optional[List[Dict[str, Any]]]:

    cur = connection.cursor()
    res = cur.execute(_query)
    connection.commit()

    if res.description is not None:
        column_names = [description[0] for description in res.description]
    else:
        column_names = None

    data = [{column: row[index] for index, column in enumerate(column_names)} for row in res.fetchall()]
    
    global DB_TOTAL_REQUESTS
    DB_TOTAL_REQUESTS += 1

    return data


def query_option(_query: str, connection: Optional[Connection] = None) -> Optional[List[Dict[str, Any]]]:
    
    if connection is not None:
        return query(_query, connection=connection)

    connection = sqlite3.connect(f"databases/{DATABASE_FILE}")
    data = query(_query, connection=connection)
    connection.close()

    return data


def query_single(_query: str) -> Optional[List[Dict[str, Any]]]:
    return query_option(_query)


def open_connection() -> Connection:
    return sqlite3.connect(f"databases/{DATABASE_FILE}")


def close_connection(connection: Connection) -> None:
    connection.close()


def database_setup(database_file: str) -> None:

    global DATABASE_FILE
    DATABASE_FILE = database_file

    members = query_single("SELECT * FROM members;")

    member_count: int = len(members)
    solve_count: int = sum([member["solved"] for member in members])
    awards_count: int = sum([member["awards"] for member in members])
    
    last_problem: int = max([len(member["solve_list"]) for member in members] + [0])

    log.info(f"[-] At login, {member_count} members in the database, with {solve_count} solves, {awards_count} awards.")
    log.info(f"[-] The database goes up to problem {last_problem}.")