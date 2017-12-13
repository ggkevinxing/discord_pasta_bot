import discord
import asyncio
import configparser
import logging

from pymongo import MongoClient

# TO-DO
# Implement !changegame, !changenick
# Clean up or modularize code
# Format messages to look better on Discord
# Format output to look better on command line

# getting env variables
config = configparser.ConfigParser()
config.read("config.ini")
token = config.get("Essential", "token")
db_uri = config.get("Essential", "db_uri", fallback=False)
nickname = config.get("Fun", "nickname") or False
game = config.get("Fun", "game") or False

gOffCooldown = True

# discord and database init
bot = discord.Client()
if db_uri != False:
	db_client = MongoClient(db_uri)
	db = db_client['Morton']
else:
	print("WARNING: Database not set")
	db_client = MongoClient()
	db = None


# posts textfilename.txt into given channel
async def post_txt(textfilename, channel):
	global gOffCooldown
	gOffCooldown = False
	print("post_txt(" + textfilename + ")")
	file = textfilename + '.txt'
	message = ''
	with open(file) as f:
		for line in f:
			# don't want to accidentally cross discord's limit of 2000, post message
			if len(message) > 1900:
				await bot.send_message(channel, message)
				message = ''
			if line.strip():
				message += line
	if message:
		await bot.send_message(channel, message)
	await asyncio.sleep(300) # arbitrary 5-min cooldown timer
	gOffCooldown = True

async def add_cmd(message):
	tmpArr = message.content.split()
	# checking that it's at least 3 words long (roughly in the form of !add <command> <pasta>)
	if len(tmpArr) > 2:
		command = tmpArr[1]
		prefix = "!add " + command
		if command.startswith("!"):
			command = command[1:]
		# checking if command is valid, i.e. contains characters after "!" and does not use special characters, isn't a default command
		if (command == "add" or command == "getfreq" or command == "help" or command == "commands"):
			await bot.send_message(message.channel, "ERROR: Cannot override hardcoded commands.")
		elif command.strip() and command.isalnum():
			pasta = message.content[len(prefix):].strip()
			# have to make sure it's not a command in itself trying to mess with things
			if pasta.startswith("!") == False and message.server is not None:
				if db is not None:
					collection = db[message.server.id] # keeping a collection for each server
					writeDocument = {}
					writeDocument['_id'] = command
					writeDocument['content'] = pasta
					result = collection.update_one({'_id': writeDocument['_id']}, {'$set': writeDocument}, upsert=True)
					
					# check if add or replace
					if result.upserted_id is not None:
						await bot.send_message(message.channel, "SUCCESS: Command '!" + command + "' has been replaced")
					else:
						await bot.send_message(message.channel, "SUCCESS: Command '!" + command + "' has been added")
				else:
					await bot.send_message(message.channel, "ERROR: No database found, can't add command.")
		else:
			await bot.send_message(message.channel, "ERROR: User " + message.author.display_name + " has provided invalid command '" + command + "' to add.\n----------\n" +
				"Please ensure that no special symbols are used.\n" +
				"Example: !add infinity In time you will know what it's like to lose. To feel so desperately that you're right, yet to fail all the same. Dread it. Run from it. Destiny still arrives.")

async def remove_cmd(message):
	tmpArr = message.content.split()
	if len(tmpArr) != 2:
		await bot.send_message(message.channel, "ERROR: !remove failed - Invalid input format. Use !remove <command>, where <command> is one word.")
	else:
		command = tmpArr[1]
		if command.startswith("!") == True:
			command = command[1:]
		if db is not None:
			collection = db[message.server.id]
			result = collection.delete_one({'_id': command})
			if result.deleted_count == 0:
				await bot.send_message(message.channel, "ERROR: Could not remove, Command '!" + command + "' not found. On the bright side, you wanted to remove it anyways, right?")
			else:
				await bot.send_message(message.channel, "SUCCESS: Command '!" + command + "' has been removed")
		else:
			await bot.send_message(message.channel, "ERROR: No database found, can't remove command.")

@bot.event
async def on_ready():
	print("Logged in as: " + bot.user.name + " | " + bot.user.id)
	if nickname:
		print(nickname)
		for member in bot.get_all_members():
			if member.id == bot.user.id:
				await bot.change_nickname(member, nickname)
	if game:
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
		await bot.change_presence(game=discord.Game(type=0, name=game))
	print("------")

@bot.event
async def on_message(message):
	if message.author != bot.user:
		print(message.author.name + ": " + message.content)
	global gOffCooldown

	# explicit commands ("!" prefix)
	# use double quotes to avoid escape characters on apostrophes PLEASE

	if message.content.startswith("!add") or message.content.startswith("!remove"):
		if message.server is None:
			await bot.send_message(message.channel, "ERROR: Sorry, I don't support adding or removing custom commands in private messages.")
		else:
			hasPermission = False
			for role in message.author.roles:
				if role.permissions.administrator == True:
					hasPermission = True
					if message.content.startswith("!add"):
						await add_cmd(message)
					else:	# perhaps this will become an elif if another admin permission needing command is made
						await remove_cmd(message)
					break
			if hasPermission == False:
				await bot.send_message(message.channel, "ERROR: User " + message.author.display_name + " has insufficient permissions to use command.")

	elif message.content.startswith("!help") or message.content.startswith("!commands"):
		await bot.send_message(message.channel, "eh i'll work on this later")

	elif message.author != bot.user and message.content.startswith("!") and len(message.content) > 1:
		# time to check if we have a database set and if it was a valid command
		command = message.content[1:]
		if db:
			collection = db[message.server.id]
			pastaDocument = collection.find_one({'_id': command})
			if pastaDocument is not None:
				await bot.send_message(message.channel, pastaDocument['content'])
			else:
				await bot.send_message(message.channel, "message starts with '!' but I don't recognize this command. Use !help or !commands to see what's available.")
		else:
			await bot.send_message(message.channel, "message starts with '!' but I don't recognize this command. I don't even have a database set, so I'm limited to just my default commands.\n" +
				"You can see what is available using !help or !commands")

	# trigger commands, aka easter eggs

	elif message.author != bot.user and (message.content.startswith("In time you will know what it's like to lose.") or
	message.content.startswith("Fun isn't something one considers from balancing the universe.") or
	message.content == "In" or message.content == "Fun"):
		if gOffCooldown == True:
			await post_txt("avengers", message.author)
			# await post_txt("avengers", message.author)
		else:
			await bot.send_message(message.channel, "Anti-Avengers Initiative is on cooldown. I'm probably still posting it to someone right now. Enjoy your freedom while you can!")

bot.run(token)