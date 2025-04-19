import pe_api
import pe_discord_api
import pe_database

from rich.console import Console

import json
import sys


def setup() -> str:

    """
    Complete setup of the Bot, and returns the discord_key
    """

    if len(sys.argv) < 2:
        raise Exception("Missing a profile filename.")
    
    with open(f"profiles/{sys.argv[1]}", "r") as f:
        profile = json.load(f)

    pe_discord_api.pe_discord_api_setup(profile["announcement_channels"])
    pe_api.pe_api_setup(profile["session_keys"], profile["pe_account"])
    pe_database.database_setup(profile["database_file"])
    
    return profile["discord_key"]
    

if __name__ == '__main__':

    temp_console = Console()
    temp_console.log(f"[*] Started session with profile '{sys.argv[1]}'")

    discord_key = setup()
    temp_console.rule()
    
    p = pe_api.Problem(15)
    print(p.solves())
    print(p)
    
    pe_discord_api.bot.run(discord_key)
    

    
    
