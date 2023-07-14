import pe_api
import pe_discord_api
import dbqueries

DISCORD_KEYFILE = "discord_key.txt"


if __name__ == '__main__':

    dbqueries.setup_database_keys()

    # setup discord key found in private file
    with open(DISCORD_KEYFILE, "r") as f:
        key = f.readline()
    key = key.replace("\n", "").replace("\r", "")

    pe_discord_api.bot.run(key)
    
    
    
