import discord
import asyncio
import configparser
import logging

from pymongo import MongoClient

# getting env variables
config = configparser.ConfigParser()
config.read('config.ini')
token = config.get('Essential', 'token')
db_uri = config.get('Essential', 'db_uri', fallback=False)
nickname = config.get('Fun', 'nickname') or False

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
	await asyncio.sleep(180) # arbitrary 3-min cooldown timer
	gOffCooldown = True

async def add_cmd(message):
	tmpArr = message.content.split()
	# checking that it's at least 3 words long (roughly in the form of !add <command> <pasta>)
	if len(tmpArr) > 2:
		command = tmpArr[1]
		# checking if command is valid, i.e. contains characters after "!" and does not use special characters, isn't a default command
		if (command == "!add" or command == "!getfreq" or command == "!help" or command == "!commands"):
			await bot.send_message(message.channel, "ERROR: Cannot override hardcoded commands.")
		elif command.startswith("!") and command[1:].strip() and command[1:].isalnum():
			prefix = "!add " + command
			pasta = message.content[len(prefix):].strip()
			# have to make sure it's not a command in itself trying to mess with things
			if pasta.startswith("!") == False and message.server is not None:
				if db is not None:
					collection = db[message.server.id] # keeping a collection for each server
					writeDocument = {}
					writeDocument['_id'] = command
					writeDocument['content'] = pasta
					collection.update_one( {'_id': writeDocument['_id']}, {'$set': writeDocument} , upsert=True)
					await bot.send_message(message.channel, "SUCCESS: Command '" + command + "' added (or replaced if it previously existed)") # will probably make this smarter in the future
				else:
					await bot.send_message(message.channel, "ERROR: No database found, can't add command.")
		else:
			await bot.send_message(message.channel, "ERROR: User " + message.author.display_name + " has provided invalid command '" + command + "' to add.\n----------\n" +
				"Please ensure the command begins with a '!', has a non-zero amount of characters following the '!', and that no special symbols are used.\n" +
				"Example: !add !infinity In time you will know what it's like to lose. To feel so desperately that you're right, yet to fail all the same. Dread it. Run from it. Destiny still arrives.")

@bot.event
async def on_ready():
	print('Logged in as: ' + bot.user.name + " | " + bot.user.id)
	if nickname:
		print(nickname)
		for member in bot.get_all_members():
			if member.id == bot.user.id:
				await bot.change_nickname(member, nickname)
	print('------')

@bot.event
async def on_server_join(server):
	print('Joined ' + server.name + ' as: ' + bot.user.name + " | " + bot.user.id)
	if nickname:
		print('Nickname: ' + nickname)
		for member in bot.get_all_members():
			if member.id == bot.user.id:
				await bot.change_nickname(member, nickname)
	print('------')

@bot.event
async def on_message(message):
	if message.author != bot.user:
		print(message.author.name + ": " + message.content)
	global gOffCooldown

	# explicit commands ("!" prefix)
	# use double quotes to avoid escape characters on apostrophes PLEASE

	if message.content.startswith("!getfreq"):
		counter = 0
		tmp = await bot.send_message(message.channel, "Calculating messages...")
		async for log in bot.logs_from(message.channel, limit=250):
			if log.author == message.author:
				counter += 1
		await bot.edit_message(tmp, "You wrote {} of the last 250 messages.".format(counter))

	elif message.content.startswith('!add'):
		hasPermission = False
		for role in message.author.roles:
			if role.permissions.administrator == True:
				hasPermission = True
				await add_cmd(message)
				break
		if hasPermission == False:
			await bot.send_message(message.channel, "ERROR: User " + message.author.display_name + " has insufficient permissions to use command !add <command> <pasta>")

	elif message.content.startswith("!help") or message.content.startswith("!commands"):
		await bot.send_message(message.channel, "eh i'll work on this later")

	elif message.author != bot.user and message.content.startswith("!") and len(message.content) > 1:
		# time to check if we have a database set and if it was a valid command
		if db:
			collection = db[message.server.id]
			pastaDocument = collection.find_one({'_id': message.content})
			if pastaDocument is not None:
				await bot.send_message(message.channel, pastaDocument['content'])
			else:
				await bot.send_message(message.channel, "message starts with '!' but I don't recognize this command. Use !help or !commands to see what's available.")
		else:
			await bot.send_message(message.channel, "message starts with '!' but I don't recognize this command. I don't even have a database set, so I'm limited to just my default commands.\n" +
				"You can see what is available using !help or !commands")

	# trigger commands, aka easter eggs

	elif message.author != bot.user and (message.content.startswith("In time you will know what it's like to lose. To feel so desperately that you're right, yet to fail all the same. Dread it. Run from it. Destiny still arrives.") or
	message.content.startswith("Fun isn't something one considers from balancing the universe. But this, does put a smile on my face.")):
		if gOffCooldown == True:
			await post_txt("avengers", message.author)
			# await post_txt("avengers", message.author)
		else:
			await bot.send_message(message.channel, "Anti-Avengers Initiative is on cooldown. I'm probably still posting it to someone right now. Enjoy your freedom while you can!")

bot.run(token)