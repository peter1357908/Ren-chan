
# ========================
# Discord Stuff
# ========================
import zoneinfo
from global_stuff import assert_getenv

GUILD_ID: int                 = int(assert_getenv("guild_id"))
TIME_ZONE: zoneinfo.ZoneInfo  = zoneinfo.ZoneInfo(assert_getenv("time_zone"))
BOT_MAINTAINER_ID: int        = int(assert_getenv("bot_maintainer_id"))
OFFICER_ROLE: str             = assert_getenv("officer_role")
ELDER_ROLE: str               = assert_getenv("elder_role")


# ========================
# Google Sheets Stuff
# ========================
import gspread
import asyncio

CLUB_LEADERBOARD_URL: str     = assert_getenv("club_leaderboard_url")
FRIENDLY_LEADERBOARD_URL: str = assert_getenv("friendly_leaderboard_url")
MAX_NAME_LEN: int     = int(assert_getenv("max_name_len"))

gs_client = gspread.service_account(filename='gs_service_account.json')
# club leaderboard
club_leaderboard_gs = gs_client.open_by_url(CLUB_LEADERBOARD_URL)
club_leaderboard_registry = club_leaderboard_gs.worksheet("Registry")
club_leaderboard_games = club_leaderboard_gs.worksheet("Games")
club_leaderboard_scores = club_leaderboard_gs.worksheet("Scores")

club_leaderboard_game_entry_lock = asyncio.Lock() # for both `games` and `scores` worksheets

# friendly leaderboard
friendly_leaderboard_gs = gs_client.open_by_url(FRIENDLY_LEADERBOARD_URL)
friendly_leaderboard_registry = friendly_leaderboard_gs.worksheet("Registry")
friendly_leaderboard_games = friendly_leaderboard_gs.worksheet("Games")
friendly_leaderboard_scores = friendly_leaderboard_gs.worksheet("Scores")

friendly_leaderboard_game_entry_lock = asyncio.Lock() # for both `games` and `scores` worksheets

# registry lock (used for both leaderboards)
registry_lock = asyncio.Lock()


# ========================
# Ruleset Stuff
# ========================
TIEBREAKER_METHOD: str        = assert_getenv("tiebreaker_method")

DEFAULT_CHOMBO_PENALTY: int   = int(assert_getenv("default_chombo_penalty"))

YONMA_STARTING_POINTS: int    = int(assert_getenv("yonma_starting_points"))
SANMA_STARTING_POINTS: int    = int(assert_getenv("sanma_starting_points"))

YONMA_HANCHAN_UMA_1: int      = int(assert_getenv("yonma_hanchan_uma_1"))
YONMA_HANCHAN_UMA_2: int      = int(assert_getenv("yonma_hanchan_uma_2"))
YONMA_HANCHAN_UMA_3: int      = int(assert_getenv("yonma_hanchan_uma_3"))
YONMA_HANCHAN_UMA_4: int      = int(assert_getenv("yonma_hanchan_uma_4"))

YONMA_TONPUU_UMA_1: int       = int(assert_getenv("yonma_tonpuu_uma_1"))
YONMA_TONPUU_UMA_2: int       = int(assert_getenv("yonma_tonpuu_uma_2"))
YONMA_TONPUU_UMA_3: int       = int(assert_getenv("yonma_tonpuu_uma_3"))
YONMA_TONPUU_UMA_4: int       = int(assert_getenv("yonma_tonpuu_uma_4"))

SANMA_HANCHAN_UMA_1: int      = int(assert_getenv("sanma_hanchan_uma_1"))
SANMA_HANCHAN_UMA_2: int      = int(assert_getenv("sanma_hanchan_uma_2"))
SANMA_HANCHAN_UMA_3: int      = int(assert_getenv("sanma_hanchan_uma_3"))

SANMA_TONPUU_UMA_1: int       = int(assert_getenv("sanma_tonpuu_uma_1"))
SANMA_TONPUU_UMA_2: int       = int(assert_getenv("sanma_tonpuu_uma_2"))
SANMA_TONPUU_UMA_3: int       = int(assert_getenv("sanma_tonpuu_uma_3"))

