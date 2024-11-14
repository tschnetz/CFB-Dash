import json
from datetime import datetime
import pytz
import plotly.graph_objs as go
from dash import html, dcc
from api import fetch_data_from_api, load_team_data
from config import SCHEDULE_URL, SCOREBOARD_URL, GAMES_URL, ODDS_URL, RECORDS_URL, MEDIA_URL, TEAMSTATS_URL,YEAR
from cache_config import cache


def format_time(clock):
    # Split the time string by ":" and convert to integers
    parts = clock.split(":")

    # Parse minutes and seconds, ignoring hours
    if len(parts) == 3:
        minutes, seconds = int(parts[1]), int(parts[2])
    elif len(parts) == 2:
        minutes, seconds = int(parts[0]), int(parts[1])
    else:
        return clock  # Return as is if format is unexpected

    # Format time as "M:SS" where M is minutes, SS is seconds
    return f"{minutes}:{seconds:02}"


def to_numeric(value):
    try:
        if '.' in str(value):
            return float(value)
        return int(value)
    except (ValueError, TypeError):
        return 0


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6 or not all(c in '0123456789abcdefABCDEF' for c in hex_color):
        raise ValueError(f"Invalid hex color: {hex_color}")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def color_similarity(color1, color2, threshold=100):
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    # Calculate Euclidean distance between two RGB colors
    return ((rgb1[0] - rgb2[0]) ** 2 + (rgb1[1] - rgb2[1]) ** 2 + (rgb1[2] - rgb2[2]) ** 2) ** 0.5 < threshold


@cache.memoize(timeout=3600)
def get_logos_colors():
    # Function to clean and validate hex color
    def validate_color(color, default="#ffffff"):  # Default to white if color is invalid
        if not color or not isinstance(color, str):
            return default
        color = color.lstrip("#")
        if len(color) != 6 or not all(c in '0123456789abcdefABCDEF' for c in color):
            return default
        return f"#{color}"

    with open('data/team_info.json', 'r') as file:
        data_dict = json.load(file)

    colors_logos = [
        {
            'id': team['id'],
            'school': team['school'],
            'logo': team['logos'][0] if isinstance(team['logos'], list) else team['logos'],
            'color': validate_color(team.get('color', "#ffffff")),
            'alt_color': validate_color(team.get('alternateColor', "#ffffff")),
        }
        for team in data_dict if team.get('logos')
    ]
    for team in colors_logos:
        team['logo'] = team['logo'].replace('http://', 'https://')
    return colors_logos


@cache.memoize(timeout=3600)
def get_schedule():
    querystring = {"year": YEAR}
    response = fetch_data_from_api(SCHEDULE_URL, query_params=querystring)
    return response if response is not None else []


@cache.memoize(timeout=3600)
def get_games(week):
    querystring = {"year": YEAR, "week": week, "division": "fbs"}
    response = fetch_data_from_api(GAMES_URL, query_params=querystring)
    return response if response is not None else []


@cache.memoize(timeout=3600)
def get_records():
    querystring = {"year": YEAR}
    response = fetch_data_from_api(RECORDS_URL, query_params=querystring)
    return response if response is not None else []


@cache.memoize(timeout=1800)
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


@cache.memoize(timeout=3600)
def get_media(week):
    querystring = {"year": YEAR, "week": week}
    response = fetch_data_from_api(MEDIA_URL, query_params=querystring)
    if response is not None:
        consolidated_media = {}
        for item in response:
            consolidated_media.setdefault(item['id'], []).append(item['outlet'])
        return [{'id': k, 'outlet': ', '.join(v)} for k, v in consolidated_media.items()]
    return []


def get_scoreboard():
    querystring = {"classification": "fbs"}
    response = fetch_data_from_api(SCOREBOARD_URL, query_params=querystring)
    return response if response is not None else []


def get_team_stats(stat_type, team):
    file_name = 'data/offense_stats.json' if stat_type == "offense" else 'data/defense_stats.json'
    team_data = load_team_data(file_name, team)
    DEFAULT_STATS = {
        'total_rank': 0,
        'total_ypg': 0,
        'rush_rank': 0,
        'rush_ypg': 0,
        'pass_rank': 0,
        'pass_ypg': 0,
        'scoring_avg': 0,
        'scoring_rank': 0,
        'id': '',
    }
    if team_data is None:
        return DEFAULT_STATS.copy()

    return {
        'total_rank': to_numeric(team_data.get("Total_Rank", 0)),
        'total_ypg': to_numeric(team_data.get("Total_YPG", 0)),
        'rush_rank': to_numeric(team_data.get("Rushing_Rank", 0)),
        'rush_ypg': to_numeric(team_data.get("Rushing_YPG", 0)),
        'pass_rank': to_numeric(team_data.get("Passing_Rank", 0)),
        'pass_ypg': to_numeric(team_data.get("Passing_YPG", 0)),
        'scoring_avg': to_numeric(team_data.get("Scoring_Avg" if stat_type == "defense" else "Scoring_PPG", 0)),
        'scoring_rank': to_numeric(team_data.get("Scoring_Rank", 0)),
        'id': team_data.get("id", ""),
    }


@cache.memoize(timeout=3600)
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
@cache.memoize(timeout=3600)
def add_logos(games):
    team_info = get_logos_colors()
    # Filter out the faulty Charlotte logo entry
    valid_team_info = [
        team for team in team_info
        if team.get('logos') != 'https://a.espncdn.com/i/teamlogos/ncaa/500/3253.png'
    ]

    # Create dictionaries for quick lookup by school name
    team_data_by_school = {
        team['school']: {'logo': team['logo'], 'color': team.get('color', "#ffffff"), 'alt_color': team.get('alt_color', "#ffffff")}
        for team in valid_team_info
    }

    games_with_logos = []
    for game in games:
        # Fetch home team logo and color
        home_team_data = team_data_by_school.get(game['home_team'], {'logo': "N/A", 'color': "#ffffff"})
        home_team_logo = home_team_data['logo']
        home_team_color = home_team_data['color']
        home_team_alt_color = home_team_data['alt_color']

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
            'away_team_color': away_team_color,
            'home_team_alt_color': home_team_alt_color,
        }
        games_with_logos.append(game_with_logos)

    return games_with_logos


# Cleans and formats games data
@cache.memoize(timeout=3600)
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
            'home_id': game['home_id'],
            'away_team': game['away_team'],
            'away_id': game['away_id'],
            'home_points': game['home_points'],
            'home_line_scores': game['home_line_scores'],
            'away_points': game['away_points'],
            'completed': game['completed']
        }
        cleaned_games.append(cleaned_game)
    return cleaned_games


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


# Improved function to create labeled comparison rows
def create_comparison_row(stat_name, description, home_value, away_value, home_color, away_color, home_rank, away_rank, stat_type):
    if stat_type == "defense":
        # For defense stats, where lower values are better, invert the percentages
        if home_value > 0 and away_value > 0:
            home_percentage = (1 / home_value) / ((1 / home_value) + (1 / away_value)) * 100
            away_percentage = (1 / away_value) / ((1 / home_value) + (1 / away_value)) * 100
        elif home_value == 0 and away_value > 0:
            home_percentage = 100
            away_percentage = 0
        elif away_value == 0 and home_value > 0:
            home_percentage = 0
            away_percentage = 100
        else:
            home_percentage = 50
            away_percentage = 50
    else:
        # For offense stats, where higher values are better, use original percentage logic
        total_value = home_value + away_value
        if total_value > 0:
            home_percentage = (home_value / total_value) * 100
            away_percentage = (away_value / total_value) * 100
        else:
            home_percentage = 50
            away_percentage = 50

    # Generate the visual row
    return html.Div([
        html.Div(description, style={"width": "150px", "textAlign": "left", "fontSize": "12px", "fontWeight": "bold"}),  # Stat label
        html.Span(f"{away_value:.1f} ({away_rank})", style={"width": "50px", "textAlign": "right", "fontSize": "12px", "padding": "5px"}),
        dcc.Graph(
            figure=go.Figure(
                data=[
                    go.Bar(
                        x=[away_percentage], orientation='h', marker_color=away_color, showlegend=False,
                        name=f"{away_value:.1f}"
                    ),
                    go.Bar(
                        x=[home_percentage], orientation='h', marker_color=home_color, showlegend=False,
                        name=f"{home_value:.1f}"
                    )
                ],
                layout=go.Layout(
                    height=15,
                    margin=dict(l=0, r=0, t=0, b=0),
                    xaxis=dict(visible=False, range=[0, 100]),
                    yaxis=dict(visible=False),
                    barmode='stack'  # Stack the bars to show proportional segments
                )
            ),
            config={'displayModeBar': False},
            style={'height': '25px', 'width': '100%'}
        ),
        html.Span(f"{home_value:.1f} ({home_rank})",
                  style={"width": "50px", "textAlign": "left", "float": "right", "fontSize": "12px", "padding": "5px"}),
        html.Div(description, style={"width": "150px", "textAlign": "right", "fontSize": "12px", "fontWeight": "bold"})  # Right-side Stat label
    ], style={"display": "flex", "alignItems": "center", "marginBottom": "5px"})

