# Ranked Bot

## Download project

`git clone https://github.com/lfenart/ranked_bot.git`

## Install dependencies

### python 3

https://www.python.org/downloads/

Additional libraries
```
py -3 -m pip install -U requests
py -3 -m pip install -U discord
py -3 -m pip install -U matplotlib
py -3 -m pip install -U python-dotenv
py -3 -m pip install -U toml
py -3 -m pip install -U trueskill
```

### .Net 5.0

https://dotnet.microsoft.com/download/dotnet/5.0

## Set up the bot

In bot, rename .env.example to .env and write the discord token of your bot next to DISCORD_TOKEN.

Change the configuration in config.toml.

## Run

Start the api first: `start_api.bat`

Then start the bot: `start_bot.bat`
