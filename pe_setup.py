import json
import sys

import pe_api
import pe_database
import pe_global_objects as pe_global
import pe_session


def setup() -> str:

    """
    Complete setup of the Bot, and returns the discord_key
    """

    if len(sys.argv) < 2:
        sys.argv.append("authentic.json")
        pe_global.log.warning("No profile attached, using authentic.json instead")

    pe_global.log.info(f"Started session with profile '{sys.argv[1]}'")

    profile_name = f"profiles/{sys.argv[1]}"
    with open(profile_name, "r") as f:
        profile = json.load(f)

    pe_global.pe_discord_api_setup(profile["announcement_channels"])
    pe_api.pe_api_setup(profile["session_keys"], profile["pe_account"])
    pe_database.database_setup(profile["database_file"])
    pe_session.session_setup(profile["captcha_key"], profile_name)

    return profile["discord_key"]