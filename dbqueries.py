import pymysql
import json
import datetime
import phone_api
import pe_api

MYSQL_KEYFILE = "database_key.txt"

DB_TOTAL_REQUESTS = 0
DB_SESSION_REQUESTS = 0

def setup_database_keys(credentials):
    # Setup MySQL key found in a private file
    with open(MYSQL_KEYFILE) as f:
        key = [line.strip() for line in f.readlines()]

    credentials["password"] = key[0]
    credentials["host"] = key[1]

def open_connection(credentials):
    try:
        return pymysql.connect(
            host=credentials["host"],
            user=credentials["user"],
            password=credentials["password"],
            db=credentials["db"]
        )
    except Exception as e:
        print("Error while creating a connection to the database:", e)
        phone_api.bot_crashed("Database request crash")
        return None

def close_connection(connection):
    if connection is not None:
        connection.close()

def execute_query(query, connection):
    global DB_SESSION_REQUESTS, DB_TOTAL_REQUESTS

    DB_SESSION_REQUESTS += 1
    DB_TOTAL_REQUESTS += 1

    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            if query.startswith("SELECT"):
                result = cursor.fetchall()
                field_names = [i[0] for i in cursor.description]
                result = to_json(result, field_names)
                return result
            elif query.startswith("INSERT") or query.startswith("UPDATE"):
                connection.commit()
                return True
    except Exception as e:
        print("Error while executing the query:", e)
        phone_api.bot_crashed("Error while querying the database")
        return None

def to_json(result, headers):
    new_obj = {}
    for index1, row in enumerate(result):
        new_obj[index1] = {}
        for index2, column in enumerate(row):
            dates_f = [
                isinstance(column, datetime.date),
                isinstance(column, datetime.datetime),
                isinstance(column, datetime.time)
            ]
            if any(dates_f):
                new_obj[index1][headers[index2]] = str(column)
            else:
                new_obj[index1][headers[index2]] = column
    return new_obj

def single_request(query, running_server=True):
    connection = open_connection(credentials_server if running_server else credentials_remote)
    if connection is not None:
        result = execute_query(query, connection)
        close_connection(connection)
        return result
    return {}

if __name__ == "__main__":
    credentials_server = {"user": "euler_remote", "db": "euler"}
    credentials_remote = credentials_server.copy()
    setup_database_keys(credentials_server)
    print(single_request("SELECT * FROM friends", running_server=False))

