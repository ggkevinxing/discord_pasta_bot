# discord_pasta_bot

a discord bot that uses mongodb to make !commands for text/emoji binds

![Let's give a quick shout-out to Tobey Maguire](https://raw.githubusercontent.com/ggkevinxing/discord_pasta_bot/master/add_example.JPG)

# SETTING UP

requires mongodb and [pymongo](http://api.mongodb.com/python/current/installation.html)

use pip to install the dependencies, such as `discord.py` and `asyncio`

rename `config_example.ini` to `config.ini` and replace the bot token, mongodb uri and nickname as you see fit

`python main.py`

# Default Commands

- `!add <command> <pasta>`                
  - creates !<command> bind such that <pasta> is posted to the channel every time a user posts !<command>
  - only administrators may add commands, but everyone can use the !<command> afterwards
  - if <command> already exists, it will be replaced with the newest <pasta>

- `!remove <command>`                
  - removes !<command> bind from database
  - only administrators may remove commands

- there's also an easter egg command that you probably never want to use or experience the consequences of

# To-Do

- Implement `!help` and `!commands`
  - Dynamically return all available commands for the server based on what's stored in the database

- Tidy up the README, make the set up more comprehensible
