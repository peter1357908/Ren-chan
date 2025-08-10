# Ren-chan

Ren-chan is a Discord bot for riichi club management, using Google Sheets for data store. Ren-chan is based on [Ronhorn](https://github.com/Longhorn-Riichi/Ronhorn), as an effort to:
1. isolate the club management commands from the mahjong analysis commands (e.g., `/injustice`)
1. eventually create an end-to-end club management bot with minimal setup

## Repository Structure:
- `bot.py`: entry point of the Discord bot. Does the following:
    1. imports `global_stuff.py`, which does the following:
        1. load all the environment variabels from `config.env`
    1. set up the non-slash Discord commands
    1. set up command error handlers (both slash and non-slash)
- `start.sh` and `deploy.sh`: entry points of the bot as a Python application.
    - `start.sh`:
        1. if the bot is currently running, kill it (based on the presence of `app.pid` file)
        1. runs the bot under `pipenv` in the background and tracks its PID in `app.pid`.
    - `deploy.sh`:
        1. pulls from remote
        1. installs latest depdendencies according to `Pipfile.lock`
        1. calls `start.sh`.
- `/ext/`: Discord bot extensions (each extension is a suite of slash commands and their helper functions)
    - `Utilities`: various utilities, including recording in-person games, managing club membership, etc.

## Setting up the bot
First, `cp config.template.env config.env`.
### Discord Stuff
1. set up a bot account on Discord's [developer portal](https://discord.com/developers/applications) (`New Application`).
    - (SETTINGS → Bot) Privileged Gateway Intents: `SERVER MEMBERS INTENT` AND `MESSAGE CONTENT INTENT`
1. invite the bot to the respective servers. You can use the developer portal's OAuth2 URL Generator (SETTINGS → OAuth2 → URL Generator):
    - Scopes: bot
    - Bot Permissions:
        * General Permissions: Manage Roles, View Channels, Manage Events
        * Text Permissions: Send Messages, Create Public Threads, Send Messages in Threads, Manage Messages, Manage Threads, Use External Emojis
    - [Current Bot Invite URL](https://discord.com/oauth2/authorize?client_id=1264000694369910834&permissions=326686223360&integration_type=0&scope=bot)
1. fill in the `Discord Stuff` section of [config.env](config.env). The bot token can be obtained through (SETTINGS → Bot \[→ Reset Token\])
### Google Sheets Stuff
1. set up a [Google Cloud project](https://console.cloud.google.com/). [Enable Google Sheets API access](https://console.cloud.google.com/apis/library/sheets.googleapis.com), and "Create Credentials" for a service account (no need to give it access to the project). Generate a JSON key for that service account and save it as `gs_service_account.json` in the [root directory]
1. make a suitable Google Spreadsheet ([example](https://docs.google.com/spreadsheets/d/1pXlGjyz165S62-3-4ZXxit4Ci0yW8piVfbVObtjg7Is/edit?usp=sharing))
1. share the Spreadsheet with that service account.
1. fill in the `Google Sheets Stuff` section of [config.env](config.env)

## Running the bot
1. ensure you complete all steps in [the setup](#setting-up-the-bot).
1. run `./deploy.sh` (see [repo structure](#repository-structure) for details).
1. in the relevant Discord server: run `rc/sync` to sync the slash commands for that server (`rc/` is the regular command prefix).

## Relevant Links (References)
- [Ronhorn](https://github.com/Longhorn-Riichi/Ronhorn)
- [amae-koromo](https://github.com/SAPikachu/amae-koromo) and [amae-koromo-scripts](https://github.com/SAPikachu/amae-koromo-scripts)
- [Ronnie](https://github.com/RiichiNomi/ronnie)
- [mjsoul.py](https://github.com/RiichiNomi/mjsoul.py) (eventually we'll add our `mahjongsoul` module into the `mjsoul.py` package)
- [mahjong_soul_api](https://github.com/MahjongRepository/mahjong_soul_api/)

[root directory]: /
