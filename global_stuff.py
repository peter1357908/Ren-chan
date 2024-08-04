import gspread
import asyncio
import dotenv
from os import getenv

# load environmental variables
dotenv.load_dotenv("config.env")

def assert_getenv(name: str) -> str:
    value = getenv(name)
    assert value is not None, f"missing \"{name}\" in config.env"
    return value

# Google Sheets stuff
gs_client = gspread.service_account(filename='gs_service_account.json')
leaderboard_ss = gs_client.open_by_url(assert_getenv("spreadsheet_url"))
registry = leaderboard_ss.worksheet("Registry")
raw_scores = leaderboard_ss.worksheet("Raw Scores")
registry_lock = asyncio.Lock()
raw_scores_lock = asyncio.Lock()
