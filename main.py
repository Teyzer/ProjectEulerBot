import pe_api
import pe_discord_api
import dbqueries

DISCORD_KEYFILE = "discord_key.txt"
MYSQL_KEYFILE = "database_key.txt"


if __name__ == '__main__':

    # setup mysql key found in private file
    with open(MYSQL_KEYFILE) as f:
        key = list(map(lambda x: x.replace("\n", "").replace("\r", ""), f.readlines()))

    dbqueries.credentials_server["password"] = key[0]
    dbqueries.credentials_server["host"] = key[1]

    # setup discord key found in private file
    with open(DISCORD_KEYFILE, "r") as f:
        key = f.readline()
    key = key.replace("\n", "").replace("\r", "")

    pe_discord_api.bot.run(key)
