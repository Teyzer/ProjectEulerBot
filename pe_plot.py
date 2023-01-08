import plotly.express as px
import plotly.io as pio

import pe_api
import dbqueries

import datetime
import pytz


# Called when started
def graph_start():
    pio.templates.default = "plotly"


# Return a graph of the last solves during the last 'day_counts' days.
def graph_solves(day_counts: int, smoothing = 1):

    save_location = "graphs/solves_figure.png"

    database_format = "%Y-%m-%d"
    output_format = "%Y-%m-%d"

    data = pe_api.get_solves_in_database(day_counts)
    data_len = day_counts + 1

    current_day = datetime.datetime.now(pytz.utc)
    days_list = [(current_day - datetime.timedelta(days=x)).strftime(output_format) for x in range(data_len)]

    counts = {day: 0 for day in days_list}

    for i in data.keys():
        day_as_key = datetime.datetime.strptime(data[i]["solve_date"].split()[0], database_format).strftime(output_format)
        counts[day_as_key] += 1

    data_df = {"DATE": days_list, "SOLVES": list(counts.values())}

    figure = px.line(data_df, x="DATE", y="SOLVES")
    
    figure.write_image(save_location)
    return save_location


if __name__ == "__main__":

    dbqueries.setup_database_keys()
    graph_start()
    graph_solves(100)