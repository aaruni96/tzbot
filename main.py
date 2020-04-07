#!/usr/bin/python3.8

import calendar
import re
import json
import os
import time
import requests
import sqlite3
import pytz

apiURL="https://api.telegram.org/bot"
botID=#tzdata_bot
offset=0
groupID=#dnd group

def synErr():
	'''
		Throws generic syntax error string
	'''

	estr="Wrong syntax. Refer /help."
	sendMessage(estr)

def help():
	'''
		When function is fired, print bot usage
	'''

	HelpText="""Simple tzdata converter bot.
	Supported functions: /help , /register , /update , /time
	
	/help : Prints this help.
	
	/register : Registers your timezone into the database. Use only if you haven't already registered.
		Syntax : `/register TZ` , where TZ is your two digit country timezone. 'IN' for 'Asia/Kolkata', 'DE' for 'Europe/Berlin'
	
	/query : Lists all registered user and their timezone.
		Optional : `/query me` lists only your data
	
	/update : updates tzdata info when you travel.
		Syntax : `/update TZ` , where TZ is your two digit country timezone. 'IN' for 'Asia/Kolkata', 'DE' for 'Europe/Berlin'
	
	/time : time to convert. Forwards the date automatically to the next nearest Sunday
		Syntax : `/time HH:MM`
		Alt Syntax : `/time YYYY-MM-DD HH:MM` to not do the sunday assumption"""
	sendMessage(HelpText)

def initDB():
	'''
		Function initialises sqlite3 database for use
		WARNING! RUN ONLY ONCE!!!
	'''

	db = sqlite3.connect("data/db.db")
	cursor = db.cursor()
	cursor.execute('''CREATE TABLE user(userID INTEGER PRIMARY KEY, name TEXT NOT NULL, tz TEXT NOT NULL)''')   #stores user and their timezone, for future conversions
	db.commit()

def sendMessage( userCommand ):
	'''
		Function takes string and publishes to group, or prints error
	'''
	try:
		requests.get(apiURL+botID+"/sendMessage?chat_id="+str(groupID)+"&text="+str(userCommand)+"&parse_mode=Markdown")
		print("Sent!")
	except requests.exceptions.RequestException as e:
					print(e)
					print("Not Sent:(")

def registerUser(userID, userName, tzdata):
	'''
		First time user registration only. Use updateUser() for updating tzdata
	'''

	#check tzdata against known formats
	#if yesadd to database
	#if no, throw an error
	#check new user
	
	db = sqlite3.connect("data/db.db")
	cursor=db.cursor()

	cursor.execute('''SELECT userID from user''')
	d = cursor.fetchall()

	for i in range (0,len(d)):
		if (userID in d[i]):
			estr="User already registered!"
			sendMessage(estr)
			return

	if (pytz.country_timezones(tzdata)[0] in pytz.all_timezones_set):
		cursor.execute('''INSERT INTO user(userID, name,tz) VALUES(?,?,?)''',(userID, userName,tzdata))
		db.commit()
		rstr="Successfully registered !"
		sendMessage(rstr)

	else:
		estr="Invalid timezone. Enter a valid 2 letter country code."
		sendMessage(estr)
	return

def updateUser(userID, tzdata):
	'''
		Updates user tz info
	'''

	db = sqlite3.connect("data/db.db")
	cursor=db.cursor()
	cursor.execute('''SELECT userID from user''')
	d=cursor.fetchall()
	found=0
	for i in range (0,len(d)):
		if (userID in d[i]):
			found=1
	
	if(found==0):
		errstr="You must register first!"
		sendMessage(errstr)
		return


	if (pytz.country_timezones(tzdata)[0] in pytz.all_timezones_set):
		cursor.execute('''UPDATE user SET tz=? WHERE userID=? ''',(tzdata, userID))
		db.commit()
		sendMessage("Successfully updated!")
	else:
		estr="Invalid timezone. Enter a valid 2 letter country code."
		sendMessage(estr)
	return

def tzconv(userID,tstr,dstr):
	'''
		Grabs a timestring in HH:MM format, and converts it into next sunday + timezones
	'''

	#check if time is within bounds
	if int(tstr.split(':')[0])<0 or int(tstr.split(':')[0])>23 or int(tstr.split(':')[1])<0 or int(tstr.split(':')[1])>59 :
		estr="Please provide a valid time"
		sendMessage(estr)
		return
	#check if day is within bounds
	if(dstr!='1'):
		if int(dstr.split('-')[0])<0 or int(dstr.split('-')[0])>9999 or int(dstr.split('-')[1])<1 or int(dstr.split('-')[1])>12 or int(dstr.split('-')[2])<1 or int(dstr.split('-')[2])>31:
			estr="Please provide a valid date"
			sendMessage(estr)
			return
		if int(dstr.split('-')[1]) == 2:
			if calendar.isleap(int(dstr.split('-')[0])):
				if int(dstr.split('-')[2]) > 29:
					estr="Please provide a valid date"
					sendMessage(estr)
					return
			else:
				if int(dstr.split('-')[2]) > 28:
					estr="Please provide a valid date"
					sendMessage(estr)
					return


	db = sqlite3.connect("data/db.db")
	cursor = db.cursor()

	cursor.execute('''SELECT userID from user where userID=?''',[userID])
	d=cursor.fetchone()
	if d==None:
		estr = "You must register first!"
		sendMessage(estr)
		return

	#convert time into all other registered timezones
	time=pytz.datetime.datetime.strptime(tstr, "%H:%M")
	nowtime=pytz.datetime.datetime.now()
	time=time.replace(year=nowtime.year, month=nowtime.month, day=nowtime.day)
	if(dstr=='1'):
		if(time.weekday() != 6):
			time=time.replace(day=time.day + (6-time.weekday()))	#sends to the next sunday if not already a sunday
	else:
		nowtime=pytz.datetime.datetime.strptime(dstr, "%Y-%m-%d")
	cursor.execute('''SELECT tz from user WHERE userID=? ''',[userID])
	tzdata=cursor.fetchone()[0]	
	cursor.execute('''SELECT DISTINCT tz from user''')
	d = cursor.fetchall()
	t1=pytz.timezone(pytz.country_timezones(tzdata)[0])
	nowtime=t1.normalize(t1.localize(nowtime))
	time=t1.normalize(t1.localize(time))
	sendstr=''
	for x in range(0,len(d)):
		curtobj=time.astimezone(pytz.timezone((pytz.country_timezones(d[x][0]))[0]))
		sendstr=sendstr+str(curtobj.year) + '-' + str(curtobj.month) + '-' + str(curtobj.day) + ' ' + ('0'+str(curtobj.hour) if curtobj.hour<10 else str(curtobj.hour)) + ':' + ('0'+str(curtobj.minute) if curtobj.minute<10 else str(curtobj.minute)) + ' in ' + str(curtobj.tzinfo)
		sendstr=sendstr+'\n'
		print(sendstr)
	sendMessage(sendstr)

def userQuery(user):
	'''
		Function reads data from db prints to chat
	'''

	db=sqlite3.connect("data/db.db")
	c=db.cursor()
	if(user=='all'):
		c.execute('''SELECT name,tz from user''')
	else:
		c.execute('''SELECT name,tz from user where userID=?''',[user])
	d = c.fetchall()
	sendstr=''
	for x in range(0,len(d)):
		sendstr=sendstr+str(d[x])+'\n'
	sendMessage(sendstr)


def getInput():
	'''
		Function gets input string from bot, or prints error
	'''
	global offset
	global apiURL
	global botID
	global groupID

	while(1):
		try:
			r=requests.get(apiURL+botID+"/getUpdates?offset="+str(offset))
		except requests.exceptions.RequestException as e:
						print(e)
						continue
		data=json.loads(r.content.decode('utf-8'))
		if (len(data['result']) > 0):
			updateID=data['result'][0]['update_id']
			if not 'entities' in data['result'][0]['message']:
				#do nothing
				offset=updateID+1
				print("Command not for me")
				continue
			if (data['result'][0]['message']['entities'][0]['type'] != 'bot_command'):
				#do nothing
				offset=updateID+1
				continue
			userInput=data['result'][0]['message']['text']
			userID=data['result'][0]['message']['from']['id']
			userName=data['result'][0]['message']['from']['first_name']
			if('last_name' in data['result'][0]['message']['from']):
				userName=userName+' '+data['result'][0]['message']['from']['last_name']
			offset=updateID+1
			if(len(userInput.split('@')) > 1):
				if(userInput.split('@')[1].split(' ')[0]!="tzdata_bot"):
					print("not for me")
					#do nothing
					offset=updateID+1
					continue
				userCommand=userInput.split('@')[0]
			else:
				userCommand=userInput.split(' ')[0]
			print("Usercommand is")
			print(userCommand)
			if (userCommand=='/help'):
				help()
				continue
			elif (userCommand=='/register'):
				if(len(userInput.split()) != 2):
					synErr()
					continue
				elif(len(userInput.split(' ')[1])!=2):
					synErr()
					continue
				else:
					registerUser(userID,userName,userInput.split(' ')[1])
			elif (userCommand=='/update'):
				if(len(userInput.split()) != 2):
					synErr()
					continue
				elif(len(userInput.split(' ')[1])!=2):
					synErr()
					continue
				else:
					updateUser(userID,userInput.split(' ')[1])
			elif (userCommand=='/query'):
				if(len(userInput.split(' ')) == 1):
					userQuery('all')
					continue
				elif(len(userInput.split(' ')) == 2):
					if(userInput.split(' ')[1].lower() == 'me'):
						userQuery(userID)
						continue
				synErr()					
				continue
			elif (userCommand=='/update'):
				if(len(userInput.split(' ')) != 2):
					synErr()
				else:
					updateUser(userID,userInput.split(' ')[1])
			elif(userCommand=='/time'):
				if(len(userInput.split(' ')) == 2):
					tstring=userInput.split(' ')[1]
					if re.match("[0-9][0-9]:[0-9][0-9]$",tstring):
						tzconv(userID,tstring,'1')
					else:
						synErr()
				elif(len(userInput.split(' ')) == 3):
					dstring=userInput.split(' ')[1]
					tstring=userInput.split(' ')[2]
					if(re.match("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]",dstring)):
						if re.match("[0-9][0-9]:[0-9][0-9]$",tstring):
							tzconv(userID,tstring,dstring)
						else:
							synErr()
					else:
						synErr()
				else:
					synErr()

			elif(userCommand[0]!='/'):
				#do nothing
				continue
			else:
				erstr='Invalid command. Try /help'
				sendMessage(erstr)

#initDB()
getInput()