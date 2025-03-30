# discord_pasta_bot

a discord bot that uses mongodb to make !commands for text/emoji binds

![Let's give a quick shout-out to Tobey Maguire](https://raw.githubusercontent.com/ggkevinxing/discord_pasta_bot/master/add_example.JPG)

# SETTING UP

1. [Create a new Discord App](https://discordapp.com/developers/applications/me)

2. `pip install -r requirements.txt` to install python packages such as [discord.py](https://github.com/Rapptz/discord.py) and [pymongo](https://api.mongodb.com/python/current/installation.html). Also `dnspython` is also included if you plan on using cloud DB solutions such as MongoDB Atlas.

3. Set your environment variables for `BOT_TOKEN` (found in the Discord Developers Dashboard under <Application> > Bots section) and `DATABASE_URI` at the very least; you must replace the bot token and mongodb uri, and the rest can be optionally changed as you see fit. You can see what is used as environment variables in `main.py`. If you don't want to host a MongoDB instance locally, you can use [MongoDB Atlas Free tier](https://www.mongodb.com/cloud/atlas/register?expVariant=v1&isNewUser=true) and set up a cluster in the cloud for free!

4. Add your bot to the desired Discord server(s) using `https://discordapp.com/oauth2/authorize?client_id=<CLIENT_ID>&scope=bot`, where <CLIENT_ID> is found from the Discord Developers dashboard

5. `python main.py` and enjoy

# Default Commands

- `!add <command> <pasta>`

  - creates !<command> bind such that <pasta> is posted to the channel every time a user posts !<command>
  - only administrators may add commands, but everyone can use the !<command> afterwards
  - if <command> already exists, it will be replaced with the newest <pasta>

- `!remove <command>`

  - removes !<command> bind from database
  - only administrators may remove commands

- `!help` or `!commands`

  - finds all possible custom commands for the given server and posts them in the channel where the command was used

- `!quote` or `!q` or `!rt`

  - Creates a message quote embed similar to quoting with no added message on Skype. For folks that like to quote reply without saying anything more.

- there's also an easter egg command that you probably never want to use or experience the consequences of

- features a keep alive mechanism that lets you host on free tiers of platforms like Render without worrying about instances spinning down due to inactivity

# To-Do

- Modularize and clean up
