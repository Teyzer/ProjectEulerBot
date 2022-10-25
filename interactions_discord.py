import discord
import asyncio

INTER_ROLES_SLEEP = 0.7

LANGUAGES_ROLES = {
    "Assembly": [979775922683129887, "⚒️", None],
    "C#": [979775187786563584, "🎵", None],
    "C/C++": [979775061877747733, "🇨", None],
    "Go": [979776131303616555, "🏁", None],
    "Haskell": [979775640876236822, "🍛", None],
    "Java": [979775476606304286, "☕", None],
    "Julia": [1022102165176729660, "🫐", None],
    "Lua": [979776205467316275, "🌕", None],
    "Mathematica": [979775980841357342, "🔢", None],
    "Matlab": [979776087703822366, "🧪", None],
    "Nim": [979775789694341181, "🎲", None],
    "OCaml": [1034557184790503424, "🐫", None],
    "Python": [979775734233055293, "🐍", None],
    "Ruby": [979775693833531462, "♦️", None],
    "Rust": [979775594814373901, "⚙️", None],
    "Sage": [979776172462325810, "🌿", None],
    "Scala": [979776243950030898, "🧲", None],
    "Spreadsheets": [979776609378766848, "📃", None]
}

for lang_name in LANGUAGES_ROLES.keys():
    if LANGUAGES_ROLES[lang_name][2] is None:
        LANGUAGES_ROLES[lang_name][2] = "You like " + lang_name


class Dropdown(discord.ui.Select):

    #start = [False for _ in LANGUAGES_ROLES.keys()]

    def __init__(self, bot_: discord.Bot, author_: discord.User):

        #print("got point 2")

        # For example, you can use self.bot to retrieve a user or perform other functions in the callback.
        # Alternatively you can use Interaction.client, so you don't need to pass the bot instance.
        self.bot = bot_
        self.author = author_

        self.author_roles = [y.id for y in self.author.roles]
        self.bool_roles = {lang_name: LANGUAGES_ROLES[lang_name][0] in self.author_roles for lang_name in LANGUAGES_ROLES.keys()}

        #print("got point 3")
        #print(self.author_roles)
        #print(self.bool_roles)

        # Set the options that will be presented inside the dropdown:
        options = [
            discord.SelectOption(
                label=lang_name,
                description=LANGUAGES_ROLES[lang_name][2],
                emoji=LANGUAGES_ROLES[lang_name][1],
                default=self.bool_roles[lang_name]
            ) for lang_name in sorted(LANGUAGES_ROLES.keys())
        ]

        #print(options)

        # The placeholder is what will be shown when no option is selected.
        # The min and max values indicate we can only pick one of the three options.
        # The options parameter, contents shown above, define the dropdown options.
        super().__init__(
            placeholder="Choose your favorite languages:",
            min_values=0,
            max_values=min(len(LANGUAGES_ROLES.keys()), 25),
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        # Use the interaction object to send a response message containing
        # the user's favourite colour or choice. The self object refers to the
        # Select object, and the values attribute gets a list of the user's
        # selected options. We only want the first one.

        await interaction.response.defer()

        new_roles = {lang_name: lang_name in self.values for lang_name in LANGUAGES_ROLES}

        for lang_name in LANGUAGES_ROLES:
            if new_roles[lang_name] == self.bool_roles[lang_name]:
                continue
            role = discord.utils.get(self.author.guild.roles, id=LANGUAGES_ROLES[lang_name][0])
            if new_roles[lang_name] == True and self.bool_roles[lang_name] == False:
                await self.author.add_roles(role)
                await asyncio.sleep(INTER_ROLES_SLEEP)
            if new_roles[lang_name] == False and self.bool_roles[lang_name] == True:
                await self.author.remove_roles(role)
                await asyncio.sleep(INTER_ROLES_SLEEP)

        resps = ", ".join(self.values)
        print(f"User {self.author.name} updated roles to {resps}")

        await interaction.followup.send(
            f"Roles updated to {resps}",
            ephemeral=True
        )


# Defines a simple View that allows the user to use the Select menu.
class DropdownView(discord.ui.View):
    def __init__(self, bot_: discord.Bot, author: discord.User):

        self.bot = bot_
        super().__init__()

        # Adds the dropdown to our View object
        self.add_item(Dropdown(self.bot, author))

        # Initializing the view and adding the dropdown can actually be done in a one-liner if preferred:
        # super().__init__(Dropdown(self.bot))