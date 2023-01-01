import plotly.express as px
import plotly.io as pio

import pe_api


# Called when started
def graph_start():
    pio.templates.default = "plotly"


# Return a graph of the last solves during the last 'day_counts' days.
def graph_solves(day_counts: int, smoothing = 1):
    
    #df = px.data.stocks()
    #df = {"date": [15, 12], "GOOG": [13, 14]}

    data = pe_api.get_solves_in_database(day_counts)
    
    pass

    #print(type(df))
    #fig = px.line(df, x='date', y="GOOG")
    #fig.write_image("graphs/fig1.png")


if __name__ == "__main__":

    graph_start()
    graph_solves(5)