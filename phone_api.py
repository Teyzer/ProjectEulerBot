import requests


def bot_crashed(error):

    url = "https://api.pushcut.io/YhAwjYaEHSWa1Xv109_Km/notifications/EulerBot%20crashed?text={0}"
    url = url.format("Error message: " + str(error))

    resp = requests.get(url)
    return resp.status_code == 200
