import cfbd
import os
from dotenv import load_dotenv

# Only load from .env if running locally
if not os.getenv("API_KEY"):
    load_dotenv()
PORT = int(os.environ.get('PORT', 8080))
API_KEY = os.getenv("API_KEY")
HEADERS = {
    'accept': 'application/json',
    'Authorization': f'Bearer {API_KEY}'
}
# CONFIG = cfbd.Configuration(access_token=API_KEY)
YEAR = '2024'
GAMES_URL = "https://api.collegefootballdata.com/games"
MEDIA_URL = "https://api.collegefootballdata.com/games/media"
ODDS_URL = "https://api.collegefootballdata.com/lines"
RECORDS_URL = f'https://api.collegefootballdata.com/records'
SCHEDULE_URL = "https://api.collegefootballdata.com/calendar"
SCOREBOARD_URL = "https://api.collegefootballdata.com/scoreboard"