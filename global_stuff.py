import dotenv
from os import getenv

# load environmental variables
dotenv.load_dotenv("config.env")

def assert_getenv(name: str) -> str:
    value = getenv(name)
    assert value is not None, f"missing \"{name}\" in config.env"
    return value

