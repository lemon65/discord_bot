# This is a bot for discord, coded in python, and a fork of: https://github.com/lemon65/lemon_bot_discord
	* Basically, what is done is that it has been ported to support Python 3.5 
	(Which is required by Discord.py v. 13). Not all features work, yet.




# Lemon Bot ![alt text](http://i.imgur.com/uhYjTMt.jpg "Lemon Bot Will Rule the World!")

## Features:
   * Youtube Integration
   * Magic EightBall
   * Weather by ZipCode
   * Currency system
   * Black Desert Online scripts
   * WolframAlpha
   * Bing translate
   * Steam common games finder
   * Simple math
   * Games:
	   * Casino:
		* Slot Machine
		* Blackjack
	   * Whosaidit:
		 - A game where you get a random quote from chatlog and you must know who said it.
   * Database functions:
	* Auto retrieving and archiving messages from discord servers to a local database
	* Multiple commands to access chatlogs: !randomquote, !top <list of who said what the most>, etc.
   * Awards for certain things (they work as archievements, basically)

## Development

### Requirements

- Python 3
- Virtualenv
- Vagrant
- Virtual Box

On Windows you also need Visual C++ build tools from http://landinghub.visualstudio.com/visual-cpp-build-tools

### Running the bot

Configure your secrets in `secrets`. Use the `secrets.example` as a template.

Initialize required services in VM by running

    init_vm

Start the bot by running

    run_bot

## Installation
   * Git clone the Repo. 
   	* git clone https://github.com/thomaxius-and-co/lemon_bot_discord
   * Install Vagrant
   * Install Virtual box
   * Install Python

 
## Commands:
| Commands        | description |
| ------------- |:-------------:|
| !youtube [search_term]| Searches youtube for text that the user passes, then gives back a link to one of the videos. |
| !enchant [target_level][fail_stacks] |  this is a Black Desert command that figures out the enchanting chances for black stone upgrades. |
| !roll |  This rolls from 0-100, and returns the users name and the roll value. |
| !coin | Simple coin toss command, gives you a 50/50 chance. |
| !8ball [question] | This returns the eightball prediction and the question the user asked. |
| !spank [target_user] | This will return with a punishment for the target user. |
| !join [server join url] | Send the join URL to a sever where lemon bot is in and he will join the other server. |
| !weather [Zip Code] | This uses a Weather API to return weather information based on the zip code. |
| !slots | runs the slots, and uses the users money from the bank.|
| !clear | clears the chat log in that channel. |
| !bet [amount] | Set the users betting amount. |
| !reviewbet | Returns the users current bet. |
| !loan | Gives the user, a little cash, Max amount of $50 bucks. |
| !bank | Shows the user how much money they have. |
| !leader | Shows the Top five users with the most money. |
| !wa [query]| Searches WolframAlpha |
| !help | Returns the github page with Help information and commands. |
| !math | Does a calculation with a maximum of 3 digits |
| !blackjack | Play blackjack versus the dealer
| !translate <language>  <text> | Translate a text to the given language
| !clearbot | Deletes 50 of bot messages. Only available to admins.
| !pickone <arguments> | Picks a random choice out of X arguments
| !randomcolor | get a random color. Powered by the colorcombos.com
| !randomquote | Retrieves a random quote from the database. Optional argument: custom <words separated by comma>.
| !top <list> | pre defined lists: spammers, whosaidit, whosaidit weekly, blackjack, slots. User defined: custom <words separated by comma>
| !steam common | <username1>, <username2>, ..., <usernameN>  - Find out what games you have in common with other user(s)
| !whosaidit | In this game you get a quote and you must guess who said it. Comes with weekly-resetting toplist.
| !trophycabinet | Check what trophies you might have.

## Help:
  * You can contact us (rce or Thomaxius) via our profile pages. 

## Notes:
  * I have seen lag issues with servers that can't parse the HTMl data quickly, for example a Raspberry-PI

## Thank you to:
  * Rapptz, for making discord.py - https://github.com/Rapptz/discord.py
  * Lemon, for the base, or skeleton of a base.

## Copyright:
Original lemon bot:
#################### Copyright (c) 2016 RamCommunity #################

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do so
