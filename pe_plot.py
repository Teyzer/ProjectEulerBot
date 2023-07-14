import plotly.express as px
import plotly.io as pio

import pe_api
import pe_image
import dbqueries

import datetime
import pytz
import time

import os
import glob
import shutil


# Called when started
def graph_start():
    pio.templates.default = "plotly"


# Return a graph of the last solves during the last 'day_counts' days.
def graph_solves(day_counts: int, local: bool, smoothing = 1):

    save_location = "graphs/solves_figure.png"

    database_format = "%Y-%m-%d"
    output_format = "%Y-%m-%d"

    if local is True:

        data = pe_api.get_solves_in_database(day_counts)
        data_len = day_counts + 1

        current_day = datetime.datetime.now(pytz.utc)
        days_list = [(current_day - datetime.timedelta(days=x)).strftime(output_format) for x in range(data_len)]

        counts = {day: 0 for day in days_list}

        for i in data.keys():
            day_as_key = datetime.datetime.strptime(data[i]["solve_date"].split()[0], database_format).strftime(output_format)
            counts[day_as_key] += 1

    else:

        data = pe_api.get_global_solves_in_database(day_counts)
        data_len = len(data)

        days_list = [data[x]["DATE(date_stat)"] for x in data.keys()]
        counts = {data[x]["DATE(date_stat)"]: data[x]["solves"] for x in data.keys()}
        

    data_df = {"DATE": days_list, "SOLVES": list(counts.values())}

    figure = px.line(data_df, x="DATE", y="SOLVES")
    
    figure.write_image(save_location)
    return save_location


def generate_individual_graph(file_content: str, username: str) -> str:
    
    seperator = ","
    project_euler_time_format = "%d %b %y (%H:%M)"

    path = f"graphs/{username}/"

    try:
        os.mkdir(path)
    except:
        files = glob.glob(path + "*")
        for f in files:
            os.remove(f)

    frame_count = 100
    additional_frame_count = 25

    file_content = file_content.split("\n")
    solves = list(map(lambda l: l.split(seperator), file_content))

    solves = list(filter(lambda element: len(element) > 1, solves))

    minimal_date = datetime.datetime(1980, 1, 1, 0, 0, 0)
    converter = lambda el: minimal_date if "date" in el else datetime.datetime.strptime(el, project_euler_time_format)

    for i in range(len(solves)):
        solves[i] = [int(solves[i][1]), converter(solves[i][0])]
    solves = solves[::-1]

    temp_epsilon = 1000

    starting_timestamp = list(filter(lambda el: el[1].timestamp() - temp_epsilon > minimal_date.timestamp(), solves))[0][1].timestamp()
    difference = solves[-1][1].timestamp() - starting_timestamp + temp_epsilon

    problems = pe_api.problems_list()[1:-1]

    for percentage in range(frame_count + 1):
        current_timestamp = starting_timestamp + difference * percentage / frame_count
        last_pb = len(list(filter(lambda el: float(el[2]) < current_timestamp, problems)))
        pe_image.image_for_timestamp_user_solve(solves, current_timestamp, username, percentage, frame_count, last_pb)

    for addition in range(1, additional_frame_count + 1):
        current_timestamp = starting_timestamp + difference
        last_pb = len(problems)
        pe_image.image_for_timestamp_user_solve(solves, current_timestamp, username, percentage, frame_count, last_pb)

    for addition in range(1, additional_frame_count + 1):
        shutil.copyfile(f"graphs/{username}/frame{frame_count}.png", f"graphs/{username}/frame{frame_count + addition}.png")

    pe_image.concatenate_image_gif(username)

    return f"graphs/{username}/{username}.gif"



if __name__ == "__main__":

    with open("pjt33_history_2023_04_25_2325.csv", "r") as f:
        content = "".join(f.readlines())

    tic = time.time()

    generate_individual_graph(content, "Teyzer18")

    print(time.time() - tic)