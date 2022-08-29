import pymysql
import json
import datetime

import phone_api

credentials_server = {"user": "euler_remote", "db": "euler"}
credentials_remote = credentials_server


def single_req(_req, running_server=True):
    con = open_con(running_server=running_server)
    if con is False:
        phone_api.bot_crashed("Database Crash")
        print("Database request crash")
        return {}
    result = query(_req, con)
    close_con(con)
    return result


def open_con(running_server=True):
    try:
        if running_server:
            return pymysql.connect(host=credentials_server["host"], user=credentials_server["user"], password=credentials_server["password"], db=credentials_server["db"])
        else:
            return pymysql.connect(host=credentials_remote["host"], user=credentials_remote["user"], password=credentials_remote["password"], db=credentials_remote["db"])
    except Exception as e:
        print(e)
        phone_api.bot_crashed("Database request crash")
        return False


def query(_query, con):
    back = True
    if con is None:
        phone_api.bot_crashed("Database Crash")
        return {}
    cur = con.cursor()
    cur.execute(_query)
    if _query[:6] == "SELECT":
        back = cur.fetchall()
        field_names = [i[0] for i in cur.description]
        back = to_json(back, field_names)
    elif _query[:6] == "INSERT" or _query[:6] == "UPDATE":
        con.commit()
    cur.close()
    return back


def close_con(con):
    con.close()


def to_json(_object, headers):
    new_obj = {}
    for index1, row in enumerate(_object):
        new_obj[index1] = {}
        for index2, column in enumerate(row):
            dates_f = [isinstance(column, datetime.date), isinstance(column, datetime.datetime), isinstance(column, datetime.time)]
            if any(dates_f):
                new_obj[index1][headers[index2]] = str(column)
            else:
                new_obj[index1][headers[index2]] = column
    return new_obj


if __name__ == "__main__":
    print(single_req("SELECT * FROM friends", running_server=False))
