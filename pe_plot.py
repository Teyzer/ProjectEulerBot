import plotly.express as px
import plotly.io as pio
import matplotlib.pyplot as plt

import pe_api
import pe_image

import datetime
import pytz
import time

import os
import glob
import shutil

import locale


# Called when started
def graph_start():
    pio.templates.default = "plotly"
    
    
def project_euler_date_converter(s: str):
    minimal_date = datetime.datetime(1980, 1, 1, 0, 0, 0)
    project_euler_time_format = "%d %b %y (%H:%M)"
    # print(datetime.datetime.strftime(datetime.datetime.now(), project_euler_time_format))
    if "date" in s:
        return minimal_date
    else:
        try:
            return datetime.datetime.strptime(s, project_euler_time_format)
        except:
            changes = [(m, m.lower() + ".") for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]]
            for change in changes:
                s = s.replace(change[0], change[1])
            return datetime.datetime.strptime(s, project_euler_time_format)
            


# Return a graph of the last solves during the last 'day_counts' days.
def graph_solves(day_counts: int, local: bool, smoothing = 1):

    save_location = "graphs/solves_figure.png"

    database_format = "%Y-%m-%d"
    output_format = "%Y-%m-%d"

    if local is True:

        data = pe_api.get_solves_in_database()
        data_len = day_counts + 1

        current_day = datetime.datetime.now(pytz.utc)
        days_list = [(current_day - datetime.timedelta(days=x)).strftime(output_format) for x in range(data_len)]

        counts = {day: 0 for day in days_list}

        for element in data:
            day_as_key = datetime.datetime.strptime(element["solve_date"].split()[0], database_format).strftime(output_format)
            if day_as_key in counts:
                counts[day_as_key] += 1

    else:

        data: list = pe_api.get_global_solves_in_database()
        minimum_day = datetime.datetime.now(pytz.utc) - datetime.timedelta(days=day_counts)

        filtered_data = []

        for element in data:
            
            d = datetime.datetime.strptime(element["date_stat"], "%Y-%m-%d %H:%M:%S")
            if d >= minimum_day:
                filtered_data.append({"date_stat": element["date_stat"], "solves": element["solves"]}) 

        data_len = len(filtered_data)

        days_list = [element["date_stat"] for element in filtered_data]
        counts = {element["date_stat"]: element["solves"] for element in filtered_data}
        

    data_df = {"DATE": days_list, "SOLVES": list(counts.values())}

    figure = px.line(data_df, x="DATE", y="SOLVES")
    
    figure.write_image(save_location)
    return save_location



def format_data_for_individual_graph(file_content: str, username: str) -> list:
    
    seperator = ","
    path = f"graphs/{username}/"

    try:
        locale.setlocale(locale.LC_TIME, "en_US")
    except Exception as e:
        pass

    try:
        os.mkdir(path)
    except:
        files = glob.glob(path + "*")
        for f in files:
            os.remove(f)

    new_file_content = file_content.split("\n")
    solves = list(map(lambda l: l.split(seperator), new_file_content))

    solves = list(filter(lambda element: len(element) > 1, solves))


    for i in range(len(solves)):
        solves[i][0] = str(solves[i][0])
        solves[i] = [int(solves[i][1]), project_euler_date_converter(solves[i][0])]
    solves = solves[::-1]
    
    return solves




def generate_individual_graph(file_content: str, username: str) -> str:
    
    minimal_date = datetime.datetime(1980, 1, 1, 0, 0, 0)
    solves = format_data_for_individual_graph(file_content, username)
    
    frame_count = 100
    additional_frame_count = 25

    temp_epsilon = 1000

    starting_timestamp = list(filter(
        lambda el: el[1].timestamp() - temp_epsilon > minimal_date.timestamp(), 
        solves
    ))[0][1].timestamp()

    difference = solves[-1][1].timestamp() - starting_timestamp + temp_epsilon

    problems = pe_api.problems_list()[1:-1]

    for percentage in range(frame_count + 1):
        
        current_timestamp = starting_timestamp + difference * percentage / frame_count
        last_pb = len(list(filter(lambda el: float(el[2]) < current_timestamp, problems)))
        
        pe_image.image_for_timestamp_user_solve(
            solves, current_timestamp, username, percentage, 
            frame_count, percentage, last_pb
        )

    for addition in range(1, additional_frame_count + 1):
        
        current_timestamp = starting_timestamp + difference
        last_pb = len(problems)

        pe_image.image_for_timestamp_user_solve(
            solves, current_timestamp, username, frame_count, 
            frame_count, frame_count + addition, last_pb
        )

    pe_image.concatenate_image_gif(username)

    return f"graphs/{username}/{username}.gif"


def generate_simple_individual_graph(solves, username):
    
    # solves = format_data_for_individual_graph(file_content, username)
    
    solve_times = []
    solve_count = 0
    
    minimal_date = datetime.datetime(1980, 1, 1, 0, 0, 0)
    temp_epsilon = 1000
    
    for solve in solves:
        solve_count += 1
        if solve[1].timestamp() - temp_epsilon > minimal_date.timestamp():
            solve_times.append([solve_count, solve[1]])

    counts = [s[0] for s in solve_times]
    times = [s[1] for s in solve_times]

    save_path = f"graphs/{username}/{username}-linear-plot.png"

    plt.cla()

    plt.style.use('ggplot')
    plt.title("Solves versus time")

    plt.plot(times, counts)    
    plt.gcf().autofmt_xdate()
    
    plt.savefig(save_path, bbox_inches='tight')
    
    return save_path
 



if __name__ == "__main__":

    with open("pjt33_history_2023_04_25_2325.csv", "r") as f:
        content = "".join(f.readlines())

    tic = time.time()

    generate_individual_graph(content, "Teyzer18")

    print(time.time() - tic)