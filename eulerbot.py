import pe_global_objects as pe_global
import pe_discord_api
from pe_setup import setup


if __name__ == '__main__':

    discord_key = setup()
    pe_global.bot.run(discord_key)