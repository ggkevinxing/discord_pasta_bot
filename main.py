import discord
import asyncio
import configparser
import logging

from pymongo import MongoClient

# TO DO:
# - figure out best way to use string manipulation to isolate command and pasta in !add <command> <pasta>
# - database integration, i.e. insert_one() on !add, find_one() on !<command>
#   - key = command, value = pasta
# - finalize ini config format
# - optional work
#   - !changegame
#   - !changenick / !removenick

# getting env variables
config = configparser.ConfigParser()
config.read('config.ini')
token = config.get('Essential', 'token')
db_uri = config.get('Essential', 'uri', fallback=False)
game_name = config.get('Fun', 'game', fallback=False)

# discord and database init
bot = discord.Client()
if db_uri != False:
    db_client = MongoClient(db_uri)
else:
    db_client = MongoClient()

@bot.event
async def on_ready():
    print('Logged in as: ' + bot.user.name + " | " + bot.user.id)
    print('------')
    if game_name != False:
        await bot.change_presence(game=discord.Game(name=game_name))

@bot.event
async def on_message(message):
    print(message.author.name + ": " + message.content)

    if message.content.startswith('!test'):
        counter = 0
        tmp = await bot.send_message(message.channel, 'Calculating messages...')
        async for log in bot.logs_from(message.channel, limit=100):
            if log.author == message.author:
                counter += 1

        await bot.edit_message(tmp, 'You have {} messages.'.format(counter))
    # elif message.content.startswith('!sleep'):
    #     await asyncio.sleep(5)
    #     await bot.send_message(message.channel, 'Done sleeping')

    elif message.content.startswith('!add '):
        await bot.send_message(message.channel, '!add <command> <pasta> will make it so !<command> will have the bot post <pasta>. Under the hood, <command> is added to the database as the key, and <pasta> as the value.')

    # elif message.content.startswith('!changegame '):
    #     new_name = message.content
    #     await bot.change_presence(game=discord.Game(name=game_name))

    elif message.content.startswith('!'):
        await bot.send_message(message.channel, "message starts with '!' but isn't a default command, eventually I will check the database for the command as the key and return the value, or an error message otherwise")

    elif message.author != bot.user:
        # for testing, pls remove
        await bot.send_message(message.channel, "__**" + message.author.name + "**__: " + message.content)

bot.run(token)