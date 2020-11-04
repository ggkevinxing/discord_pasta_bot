import time
import os
import sys
import discord
import asyncio
import logging

from pymongo import MongoClient

# TO-DO
# Implement !changegame, !changenick
# Clean up or modularize code
# Format messages to look better on Discord
# Format output to look better on command line

# getting env variables
token = os.environ.get("BOT_TOKEN")
db_uri = os.environ.get("DATABASE_URI")
nickname = os.environ.get("BOT_NICKNAME")
game = os.environ.get("BOT_GAME")

gOffCooldown = True

# discord and database init
bot = discord.Client()
if db_uri:
	print("CONNECTED TO DB")
	db_client = MongoClient(db_uri)
	db = db_client['Morton']
else:
	print("ERROR: Database not set")
	sys.exit()

#######################
## changing presence ##
#######################
@bot.event
async def on_ready():
	print("Logged in as: ", bot.user)
	if nickname:
		print("Nickname: " + nickname)
		for member in bot.get_all_members():
			if member.id == bot.user.id:
				await bot.change_nickname(member, nickname)
	if game:
		print("Playing: " + game)
		await bot.change_presence(game=discord.Game(type=0, name=game))	# why type=0 has to be specified here to work, i have no idea
	print("------")

@bot.event
async def on_server_join(server):
	print("Joined " + server.name + " as: " + bot.user.name + " | " + bot.user.id)
	if nickname:
		print("Nickname: " + nickname)
		for member in bot.get_all_members():
			if member.id == bot.user.id:
				await bot.change_nickname(member, nickname)
	if game:
		print("Playing: " + game)
		await bot.change_presence(game=discord.Game(type=0, name=game))
	print("------")

##################################
## database commands ##
##################################
async def add_cmd(message):
	tmpArr = message.content.split()
	# checking that it's at least 3 words long (roughly in the form of !add <command> <pasta>)
	if len(tmpArr) > 2:
		command = tmpArr[1]
		prefix = "!add " + command
		if command.startswith("!"):
			command = command[1:]
		# checking if command is valid, i.e. contains characters after "!" and does not use special characters, isn't a default command
		if (command == "add" or command == "help" or command == "commands"):
			await message.channel.send("ERROR: Cannot override hardcoded commands.")
		elif command.strip() and command.isalnum():
			pasta = message.content[len(prefix):].strip()
			# have to make sure it's not a command in itself trying to mess with things
			if pasta.startswith("!") == False and message.guild is not None:
				collection = db[str(message.guild.id)] # keeping a collection for each server
				writeDocument = {}
				writeDocument['_id'] = command
				writeDocument['content'] = pasta
				result = collection.update_one({'_id': writeDocument['_id']}, {'$set': writeDocument}, upsert=True)
				
				# check if add or replace
				if result.upserted_id is not None:
					await message.channel.send("SUCCESS: Command '!" + command + "' has been added")
				else:
					await message.channel.send("SUCCESS: Command '!" + command + "' has been replaced")
		else:
			await message.channel.send("ERROR: User " + message.author.display_name + " has provided invalid command '" + command + "' to add.\n----------\n" +
				"Please ensure that no special symbols are used in the command you want to add.\n" +
				"Example: !add infinity In time you will know what it's like to lose. To feel so desperately that you're right, yet to fail all the same. Dread it. Run from it. Destiny still arrives.")

async def remove_cmd(message):
	tmpArr = message.content.split()
	if len(tmpArr) != 2:
		await message.channel.send("ERROR: !remove failed - Invalid input format. Use !remove <command>, where <command> is one word.")
	else:
		command = tmpArr[1]
		if command.startswith("!") == True:
			command = command[1:]
		collection = db[str(message.guild.id)]
		result = collection.delete_one({'_id': command})
		if result.deleted_count == 0:
			await message.channel.send("ERROR: Could not remove, Command '!" + command + "' not found. On the bright side, you wanted to remove it anyways, right?")
		else:
			await message.channel.send("SUCCESS: Command '!" + command + "' has been removed")

async def get_cmds(message):
	header = message.guild.name + " commands:"
	initMsg = await message.channel.send(header)
	collection = db[str(message.guild.id)] # theoretically, we weren't passed a private message so we should have message.guild.id
	commands = collection.find().batch_size(10).sort('_id',-1)
	temp = ""

	# redundant code as seen on post_txt, welp
	for command in commands:
		if len(temp) > 1900:
			await message.channel.send(temp)
			temp = ""
		line = "!" + command['_id'] + "\n"
		temp += line
	if temp:
		await message.channel.send(temp)


####################
## misc functions ##
####################

# posts textfilename.txt into given channel
async def post_txt(textfilename, channel):
	global gOffCooldown
	gOffCooldown = False
	print("post_txt(" + textfilename + ")")
	file = textfilename + ".txt"
	message = ""
	with open(file, "rb") as f:
		for l in f:
			line = l.decode(errors='ignore')
			# don't want to accidentally cross discord's limit of 2000, post message if line with message exceeds 2000 chars
			if len(message + line) > 2000:
				await channel.send(message)
				message = ""
			if line.strip():
				message += line
	if message:
		await channel.send(message)
	await asyncio.sleep(300) # arbitrary 5-min cooldown timer
	gOffCooldown = True

################
## on_message ##
################
@bot.event
async def on_message(message):
	global gOffCooldown

	# TODO: check if starts with ! then switch statement on the word that follows the ! instead of all these ifs and repeated startswith stuff?

	if message.author != bot.user and message.guild is None:
		await message.channel.send("ERROR: I don't currently have support for any commands in private messages. Sorry!")

	elif message.author.bot == False:
		print(message.guild.name + " | " + message.channel.name + " | " + message.author.name + ": " + message.content)

		# explicit commands ("!" prefix)
		# use double quotes to avoid escape characters on apostrophes PLEASE
		if message.content.startswith("!add ") or message.content.startswith("!remove "):
			if message.channel.permissions_for(message.author).administrator == True:
				if message.content.startswith("!add"):
					await add_cmd(message)
				else:	# perhaps this will become an elif if another admin permission needing command is made
					await remove_cmd(message)
			else:
				await message.channel.send("ERROR: User " + message.author.display_name + " has insufficient permissions to use command.")

		elif message.content.startswith("!help") or message.content.startswith("!commands"):
			await get_cmds(message)

		elif message.content.startswith("!") and len(message.content) > 1:
			# time to check if we have a database set and if it was a valid command
			command = message.content[1:]
			collection = db[str(message.guild.id)]
			pastaDocument = collection.find_one({'_id': command})
			if pastaDocument is not None:
				await message.channel.send(pastaDocument['content'])
			else:
				await message.channel.send("ERROR: Message starts with '!' but I don't recognize this command. Use !help or !commands to see what's available.")

		# trigger commands, aka easter eggs

		elif (message.content.startswith("In time you will know what it's like to lose.") or
		message.content.startswith("In Time") or
		message.content.startswith("Destiny still arrives.") or
		message.content.startswith("Fun isn't something one considers from balancing the universe.") or
		message.content == "In" or message.content == "Fun"):
			if gOffCooldown == True:
				await post_txt("avengers-iw", message.author)
			else:
				await message.channel.send("Anti-Avengers Initiative is on cooldown. I'm probably still posting it to someone right now. Enjoy your freedom while you can!")

def bot_run(client, *args, **kwargs):
	# http://discordpy.readthedocs.io/en/latest/api.html#discord.Client.run
	# like Client.run except it restarts instead of closes the event loop on exception
	loop = asyncio.get_event_loop()
	while(True):
		try:
			loop.run_until_complete(client.start(*args, **kwargs))
		except Exception as e:
			print("Error", e)  # or use proper logging
			print("Waiting until restart")
			time.sleep(120)

while(True):
	try:
		bot_run(bot, token)
	except KeyboardInterrupt as e:
		print("KEYBOARD INTERRUPT, EXITING")
		sys.exit()
	except Exception as e:
		continue