from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import math

import pe_api
import pe_image
import pe_global_objects as pe_global
import pe_setup

import datetime
import pytz
import time

import os
import glob
import shutil

import asyncio

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
            
            d = datetime.datetime.strptime(element["date_stat"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.utc)
            if d >= minimum_day:
                filtered_data.append({"date_stat": element["date_stat"], "solves": element["solves"]}) 

        data_len = len(filtered_data)

        days_list = [element["date_stat"] for element in filtered_data]
        counts = {element["date_stat"]: element["solves"] for element in filtered_data}
        

    plot_data = sorted(zip(map(datetime.datetime.fromisoformat, days_list), counts.values()))

    plt.style.use("ggplot")
    plt.cla()
    plt.title("Solves versus time")
    plt.plot(*zip(*plot_data))
    plt.gcf().autofmt_xdate()
    plt.savefig(save_location, bbox_inches="tight")
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
    
    # Remove \r at end of lines
    lines = list(map(lambda line: line.replace("\r", ""), new_file_content))

    solves = list(map(lambda l: l.split(seperator), lines))

    # Remove blank lines
    solves = list(filter(lambda element: len(element) > 1, solves))

    # Not showing up bonus problems for now
    solves = list(filter(lambda element: element[0][0] != "B", solves))

    for i in range(len(solves)):
        solves[i][1] = str(solves[i][1])
        # print(solves[i])
        solves[i] = [int(solves[i][0]), project_euler_date_converter(solves[i][-1])]
    solves = solves[::-1]
    
    return solves




async def generate_individual_graph(file_content: str, username: str) -> Optional[str]:
    
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

    try:
        problems = (await pe_api.problems_list())[1:-1]
    except Exception as _:
        return None

    for percentage in range(frame_count + 1):
        
        current_timestamp = starting_timestamp + difference * percentage / frame_count
        last_pb = len(list(filter(lambda el: pe_global.pe_unix_from_time(el[2]) < current_timestamp, problems)))
        
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
 


async def generate_graph_monthly(member: pe_api.Member) -> str:
    r = await member.solves_by_csv()
    username = await member.username_option()
    
    # 1. Process dates
    df = pd.DataFrame([{"date": datetime.datetime.fromtimestamp(s.unixtime())} for s in r]).sort_values(by="date")
    df['month'] = df['date'].dt.to_period('M').dt.to_timestamp()
    
    # 2. Fill empty months and calculate cumulative solves
    df_months = pd.DataFrame({'month': pd.date_range(start=df['month'].min(), end=df['month'].max(), freq='MS')})
    df_months = df_months.merge(df.groupby('month').size().reset_index(name='monthly'), on='month', how='left').fillna(0)
    df_months['cumulative'] = df_months['monthly'].cumsum()

    # 3. Build the plot
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=df_months['month'], y=df_months['monthly'], marker_color='rgba(150,150,150,0.4)'), secondary_y=False)
    fig.add_trace(go.Scatter(x=df_months['month'], y=df_months['cumulative'], mode='lines', line=dict(color='#d62728', width=4)), secondary_y=True)
    
    fig.update_layout(
        title=dict(text=f"Monthly and Cumulative Solves - {username}", font=dict(size=24)),
        plot_bgcolor='#f0f0f0',         # Inner graph area (light gray)
        paper_bgcolor='white',          # Outer margins (solid white)
        showlegend=False, 
        bargap=0.1,
        width=1200,
        height=600,
        margin=dict(l=20, r=20, t=60, b=20) 
    )
    
    # Add white grid lines for the X-axis (vertical lines)
    fig.update_xaxes(showgrid=True, gridcolor='white', gridwidth=1.5)
    
    # Add white grid lines for the primary Y-axis (horizontal lines)
    fig.update_yaxes(title_text="Monthly Solves", showgrid=True, gridcolor='white', gridwidth=1.5, secondary_y=False)
    
    # Keep the secondary Y-axis grid off to prevent messy overlapping lines
    fig.update_yaxes(title_text="Cumulative Solves", showgrid=False, secondary_y=True)
    
    # 4. Save and return path
    filename = f"images_saves/{member._username}_graph_monthly.png" 
    fig.write_image(filename, scale=2) 
    
    return filename



async def generate_graph_github(member: pe_api.Member) -> str:
    r = await member.solves_by_csv()
    username = await member.username_option()
    
    # 1. Process dates and build continuous timeline
    dates = [datetime.datetime.fromtimestamp(s.unixtime()).date() for s in r]
    df = pd.DataFrame({'date': pd.date_range(start=min(dates), end=max(dates), freq='D')})
    
    # Count solves and merge
    solve_counts = pd.Series(dates).value_counts().reset_index()
    solve_counts.columns = ['date', 'solves']
    df['date'] = df['date'].dt.date
    df = df.merge(solve_counts, on='date', how='left').fillna({'solves': 0})
    
    # 2. Grid Math (Target Aspect Ratio 3:1)
    num_rows = math.ceil(math.sqrt(len(df) / 3.0))
    df['x_index'] = df.index // num_rows
    df['y_index'] = df.index % num_rows
    
    # 3. Locate years for X-axis labels
    df['year'] = pd.to_datetime(df['date']).dt.year
    years = df.drop_duplicates(subset=['year'])
    
    # 4. Build the plot
    heatmap = df.pivot(index='y_index', columns='x_index', values='solves')
    colors = [[0.0, '#ebedf0'], [0.01, '#9be9a8'], [0.33, '#40c463'], [0.66, '#30a14e'], [1.0, '#216e39']]
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap.values, x=heatmap.columns, y=heatmap.index,
        colorscale=colors, xgap=2, ygap=2, showscale=False, hoverongaps=False
    ))
    
    fig.update_layout(
        title=dict(text=f"Solve Activity - {username}", font=dict(size=24)),
        plot_bgcolor='white', 
        paper_bgcolor='white',
        width=1200, height=500, # Adjusted height for the 3:1 ratio
        margin=dict(l=20, r=20, t=60, b=20),
        xaxis=dict(
            showgrid=False, zeroline=False, side='top', ticks="", constrain="domain",
            tickmode='array', tickvals=years['x_index'].tolist(), ticktext=years['year'].astype(str).tolist()
        ),
        yaxis=dict(
            autorange="reversed", showgrid=False, zeroline=False, showticklabels=False, 
            scaleanchor="x", scaleratio=1, constrain="domain" # Forces perfect squares
        )
    )
    
    # 5. Save and return path
    filename = f"images_saves/{member._username}_graph_github.png"
    fig.write_image(filename, scale=2)
    
    return filename


async def generate_graph_difficulty(member: pe_api.Member) -> str:
    r = await member.solves_by_csv()
    username = await member.username_option()
    
    # 1. Process dates and fetch difficulties asynchronously
    data = []
    for s in r:
        diff = await s.problem().difficulty()
        data.append({
            "date": datetime.datetime.fromtimestamp(s.unixtime()),
            "difficulty": diff if diff is not None else 0
        })
        
    df = pd.DataFrame(data).sort_values(by="date").reset_index(drop=True)
    
    # 2. Smooth by a rolling average of the last 20 solves
    df['smoothed_diff'] = df['difficulty'].rolling(window=20, min_periods=1).mean()
    
    # 3. Build the plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['smoothed_diff'], 
        mode='lines', line=dict(color='#ff7f0e', width=4) # Just the solid orange line
    ))
    
    fig.update_layout(
        title=dict(text=f"Average Difficulty Progression (Rolling 20 Solves) - {username}", font=dict(size=24)),
        plot_bgcolor='#f0f0f0',         # Inner graph area (light gray)
        paper_bgcolor='white',          # Outer margins (solid white)
        width=1200, height=600,
        margin=dict(l=20, r=20, t=60, b=20),
        showlegend=False
    )
    
    # Add the white gridlines to match the monthly graph
    fig.update_xaxes(showgrid=True, gridcolor='white', gridwidth=1.5)
    fig.update_yaxes(title_text="Difficulty (%)", showgrid=True, gridcolor='white', gridwidth=1.5, rangemode='tozero')
    
    # 4. Save and return path
    filename = f"images_saves/{member._username}_graph_difficulty.png"
    fig.write_image(filename, scale=2)
    
    return filename




if __name__ == "__main__":

    # with open("pjt33_history_2023_04_25_2325.csv", "r") as f:
    #     content = "".join(f.readlines())

    # tic = time.time()

    # generate_individual_graph(content, "Teyzer18")

    # print(time.time() - tic)

    pe_setup.setup()    

    m = pe_api.Member(_username="pacome_f")
    r = asyncio.run(m.solves_by_csv())

    
