from youtubesearchpython.__future__ import *
from discord.ext import commands, tasks
import discord
import asyncio
import logging
import os
import re
import json
import requests
import copy

client = commands.Bot(command_prefix='=', help_command=None)

# Function to remove any unwanted or repeating results
async def redundancyFilter(redundantPos, resultFilter):
	print(redundantPos)

	for i in redundantPos:
		resultFilter[i] = None

	resultFilter = list(filter(None, resultFilter))
	return resultFilter

# Function to read from json files to list
async def readfromjsontolist(rfile, wlist):
	try:
		with open(rfile, 'r') as fp:
			wlist = json.load(fp)
			return wlist
	except FileNotFoundError:
		wlist = []
		return wlist

# Function to write to json files from list
async def writetojsonfromlist(wfile, rlist):
	with open(wfile, 'w') as fp:
		json.dump(rlist, fp, sort_keys=1, indent=5)

# YOUTUBE SCRAPE PART
@tasks.loop(minutes=5)
async def YTSCRP():
	videosSearch = []
	videosResult = []
	filteredResult = []
	redundantPositions = []
	OldResult = []
	bannedChannels = []
	settings = []

	OldResult = await readfromjsontolist('OldResults.json', OldResult)
	bannedChannels = await readfromjsontolist('BannedChannels.json', bannedChannels)

	videosSearch = CustomSearch('Original+War', VideoSortOrder.uploadDate, limit=6)
	videosResult = await videosSearch.next()

	for i in range(6):
		filteredResult.append(
			{
				"title": videosResult['result'][i]['title'],
				"link": videosResult['result'][i]['link'],
				"publishedTime": videosResult['result'][i]['publishedTime'],
				"channelLink": videosResult['result'][i]['channel']['link'],
				"description": videosResult['result'][i]['descriptionSnippet'],
				"thumbnail": videosResult['result'][i]['thumbnails'][0]['url'],
				"chanthumb": videosResult['result'][i]['channel']['thumbnails'][0]['url'],
				"channame": videosResult['result'][i]['channel']['name']
			})

	await writetojsonfromlist('OldResults.json', filteredResult)

	for i in range(len(OldResult)):
		for j in range(len(filteredResult)):
			if OldResult[i]['link'] == filteredResult[j]['link']:
				redundantPositions.append(j)
				continue

	filteredResult = await redundancyFilter(redundantPositions, filteredResult)
	del redundantPositions[:]

	for i in range(len(filteredResult)):
		for j in range(len(bannedChannels)):
			if filteredResult[i]['channelLink'] == bannedChannels[j]:
				redundantPositions.append(i)
				continue

	filteredResult = await redundancyFilter(redundantPositions, filteredResult)
	del redundantPositions[:]

	for i in range(len(filteredResult)):
		j = requests.get(filteredResult[i]['link'], cookies={'CONSENT': 'YES+42'}).text
		if len(re.findall('/channel/UCiV6WyFWNFtys43gzQ7omsw', j)) == 0:
			redundantPositions.append(i)
			continue

	filteredResult = await redundancyFilter(redundantPositions, filteredResult)

	settings = await readfromjsontolist('Settings.json', settings)
	channel = client.get_channel(settings[0])

	for i in range(len(filteredResult)):
		await channel.send(f"New video has been posted. \n Link = {filteredResult[i]['link']} \n Channel = {filteredResult[i]['channelLink']}")

@client.command()
@commands.has_any_role("Admin","Moderator","Marshals","Propaganda Officers")
async def banchan(ctx, argument, chanlink=None):
	settings = []
	bannedChannels = []
	settings = await readfromjsontolist('Settings.json', settings)
	channel = client.get_channel(settings[0])

	if argument == 'add' and chanlink != None:
		bannedChannels = await readfromjsontolist('BannedChannels.json', bannedChannels)
		bannedChannels = set(bannedChannels)

		if chanlink in bannedChannels:
			await channel.send(f"Channel {chanlink} is already in the banned channels list")
		else:
			bannedChannels = list(bannedChannels)
			bannedChannels.append(chanlink)
			await writetojsonfromlist('BannedChannels.json', bannedChannels)
			await channel.send(f"Channel {chanlink} banned")

	elif argument == 'remove' and chanlink != None:
		bannedChannels = await readfromjsontolist('BannedChannels.json', bannedChannels)
		bannedChannels = set(bannedChannels)

		if chanlink in bannedChannels:
			bannedChannels = list(bannedChannels)
			bannedChannels.remove(chanlink)
			await writetojsonfromlist('BannedChannels.json', bannedChannels)
			await channel.send(f"Ban on {chanlink} removed")
		else:
			await channel.send(f"This channel is not in the banned channels list")

	elif argument == 'list' and chanlink == None:
		bannedChannels = await readfromjsontolist('BannedChannels.json', bannedChannels)

		if bannedChannels != []:
			await channel.send('\n'.join(bannedChannels))
		else:
			await channel.send("List is empty")

	elif argument == 'add' or 'remove' and chanlink == None:
		await channel.send('No channel posted. Please post a channel link after "add/remove"')

	else:
		await channel.send('Wrong argument. Allowed "add/remove/list" "channel link"')

@client.command(aliases=['sbchannel'])
@commands.has_any_role("Admin","Moderator","Marshals","Propaganda Officers")
async def setbroadcastchannel(ctx, *, name=None):
	settings = []
	settings = await readfromjsontolist('Settings.json', settings)
	if settings == []:
		settings.append(None)

	for channel in ctx.guild.channels:
		if channel.name == name:
			settings[0] = channel.id

	await writetojsonfromlist('Settings.json', settings)
	await ctx.send(f"Channel {channel.name} set as a broadcast channel")

@client.command()
@commands.has_any_role("Admin","Moderator","Marshals","Propaganda Officers")
async def stopsearch(ctx):
	YTSCRP.cancel()
	settings = []
	settings = await readfromjsontolist('Settings.json', settings)
	channel = client.get_channel(settings[0])
	await channel.send('Youtube scrubbing stopped')

@client.command()
@commands.has_any_role("Admin","Moderator","Marshals","Propaganda Officers")
async def startsearch(ctx):
	YTSCRP.start()
	settings = []
	settings = await readfromjsontolist('Settings.json', settings)
	channel = client.get_channel(settings[0])
	await channel.send('Youtube scrubbing started at intervals of 5 minutes')

@client.command()
@commands.has_any_role("Admin","Moderator","Marshals","Propaganda Officers")
async def help(ctx):
	helptext = discord.Embed(title="Help", description="List of all commands for this bot \n\n **sbchannel (arg1)** --- Set channel for the bot to post all the information. \n **arg1** = discord channel name \n\n **banchan (arg1) (arg2)** --- Ban/unban channels. \n **arg1** = add, remove, list \n **arg2** = channel link \n\n **startsearch** --- Initiate YouTube OW content scrubbing \n\n **stopsearch** --- Stop YouTube OW content scrubbing")
	await ctx.send(embed=helptext)

@client.event
async def on_ready():
	print('Bot is ready')

client.run('ODQ1NDEyMzgyNjI4NzczOTQw.YKglow.SZlD0j-DZw3PTZ3-92m0cVWlG9E')
