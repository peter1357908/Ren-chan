import dotenv
from os import getenv
import logging
import logging.handlers
import sys

# INFO level captures all except DEBUG log messages.
# the FileHandler by default appends to the given file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.handlers.RotatingFileHandler(
            "app.log",
            maxBytes=5_000_000,
            backupCount=1
        )
    ]
)

# also log the exceptions but still invoke the default exception handler.
# note that app command exceptions should be handled separately to ensure no interruption.
# here, we are really only expecting exceptions that should crash the app.
def handle_exception(exc_type, exc_value, exc_traceback):
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

# load environmental variables
dotenv.load_dotenv("config.env")

def assert_getenv(name: str) -> str:
    value = getenv(name)
    assert value is not None, f"missing \"{name}\" in config.env"
    return value

