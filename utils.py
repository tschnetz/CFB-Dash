import json
from datetime import datetime
import pytz
from api import fetch_data_from_api
from config import SCHEDULE_URL, SCOREBOARD_URL, GAMES_URL, ODDS_URL, RECORDS_URL, MEDIA_URL, YEAR


def get_scoreboard():
    querystring = {"classification": "fbs"}
    response = fetch_data_from_api(SCOREBOARD_URL, query_params=querystring)
    return response if response is not None else []


def get_logos_colors():
    with open('data/team_info.json', 'r') as file:
        data_dict = json.load(file)

    colors_logos = [
        {
            'id': team['id'],
            'school': team['school'],
            'logo': team['logos'][0] if isinstance(team['logos'], list) else team['logos'],
            'color': team.get('color', "#ffffff")
        }
        for team in data_dict if team.get('logos')
    ]
    for team in colors_logos:
        team['logo'] = team['logo'].replace('http://', 'https://')
    return colors_logos


def get_schedule():
    querystring = {"year": YEAR}
    response = fetch_data_from_api(SCHEDULE_URL, query_params=querystring)
    return response if response is not None else []


def get_games(week):
    querystring = {"year": YEAR, "week": week, "division": "fbs"}
    response = fetch_data_from_api(GAMES_URL, query_params=querystring)
    return response if response is not None else []


def get_records():
    querystring = {"year": YEAR}
    response = fetch_data_from_api(RECORDS_URL, query_params=querystring)
    return response if response is not None else []


def get_lines(week):
    querystring = {"year": YEAR, "week": week}
    response = fetch_data_from_api(ODDS_URL, query_params=querystring)
    if response is not None:
        betting_lines = [
            {
                'id': game['id'],
                'spread': line['formattedSpread'],
                'over_under': line['overUnder']
            }
            for game in response
            for line in game.get('lines', [])
            if line.get('provider') == 'ESPN Bet'
        ]
        return betting_lines
    return []


def get_media(week):
    querystring = {"year": YEAR, "week": week}
    response = fetch_data_from_api(MEDIA_URL, query_params=querystring)
    if response is not None:
        consolidated_media = {}
        for item in response:
            consolidated_media.setdefault(item['id'], []).append(item['outlet'])
        return [{'id': k, 'outlet': ', '.join(v)} for k, v in consolidated_media.items()]
    return []


def create_records(records):
    return [
        {
            'team': record['team'],
            'Total Wins': record['total'].get('wins', 0),
            'Total Losses': record['total'].get('losses', 0),
            'Conference Wins': record['conferenceGames'].get('wins', 0),
            'Conference Losses': record['conferenceGames'].get('losses', 0),
        }
        for record in records
    ]


# Merges games data with logos and colors
def add_logos(games):
    team_info = get_logos_colors()
    # Filter out the faulty Charlotte logo entry
    valid_team_info = [
        team for team in team_info
        if team.get('logos') != 'http://a.espncdn.com/i/teamlogos/ncaa/500/3253.png'
    ]

    # Create dictionaries for quick lookup by school name
    team_data_by_school = {
        team['school']: {'logo': team['logo'], 'color': team.get('color', "#ffffff")}
        for team in valid_team_info
    }

    games_with_logos = []
    for game in games:
        # Fetch home team logo and color
        home_team_data = team_data_by_school.get(game['home_team'], {'logo': "N/A", 'color': "#ffffff"})
        home_team_logo = home_team_data['logo']
        home_team_color = home_team_data['color']

        # Fetch away team logo and color
        away_team_data = team_data_by_school.get(game['away_team'], {'logo': "N/A", 'color': "#ffffff"})
        away_team_logo = away_team_data['logo']
        away_team_color = away_team_data['color']

        # Combine game data with logos and colors
        game_with_logos = {
            **game,
            'home_team_logo': home_team_logo,
            'away_team_logo': away_team_logo,
            'home_team_color': home_team_color,
            'away_team_color': away_team_color
        }
        games_with_logos.append(game_with_logos)

    return games_with_logos


# Creates a scoreboard structure for display
def create_scoreboard():
    scoreboard = get_scoreboard()
    return [
        {
            'game_id': game['id'],
            'home_id': game['homeTeam']['id'],
            'away_id': game['awayTeam']['id'],
            'home_team': game['homeTeam']['name'],
            'away_team': game['awayTeam']['name'],
            'status': game['status'],
            'period': game['period'],
            'clock': game['clock'],
            'tv': game['tv'],
            'situation': game.get('situation'),
            'possession': game['possession'],
            'home_team_score': game['homeTeam']['points'],
            'away_team_score': game['awayTeam']['points'],
            'spread': game['betting']['spread'],
        }
        for game in scoreboard
    ]

# Cleans and formats games data
def clean_games(games):
    cleaned_games = []
    for game in games:
        start_date = datetime.fromisoformat(game['start_date']).astimezone(pytz.UTC)
        start_date_est = start_date.astimezone(pytz.timezone('US/Eastern'))
        game['start_date'] = start_date_est.strftime('%b-%d %I:%M %p')
        game['day_of_week'] = start_date_est.strftime('%A')
        cleaned_game = {
            'id': game['id'],
            'start_date': game['start_date'],
            'day_of_week': game['day_of_week'],
            'home_team': game['home_team'],
            'home_points': game['home_points'],
            'home_line_scores': game['home_line_scores'],
            'away_team': game['away_team'],
            'away_points': game['away_points'],
            'completed': game['completed']
        }
        cleaned_games.append(cleaned_game)
    return cleaned_games