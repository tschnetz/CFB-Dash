import json
from datetime import datetime
import pytz
import plotly.graph_objs as go
from dash import html, dcc
from api import fetch_data_from_api, load_team_data
from config import (SCHEDULE_URL, SCOREBOARD_URL, GAMES_URL, ODDS_URL,
                    RECORDS_URL, MEDIA_URL, GAME_STATS_URL, YEAR)
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


def get_game_stats(week):
    querystring = {"year": YEAR, "week": week, "classification": "fbs"}
    response = fetch_data_from_api(GAME_STATS_URL, query_params=querystring)
    return response if response is not None else []


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


def create_game_stats(game_id, game_stats):
    # Find the game in the data by the specified game_id
    game_data = next((game for game in game_stats if game['id'] == game_id), None)
    if not game_data:
        return {"error": "Game not found"}

    # Initialize dictionaries for home and away team stats only
    home_team_stats = {}
    away_team_stats = {}

    # Iterate through the teams to separate home and away stats
    for team in game_data['teams']:
        # Extract stats into a dictionary with categories as keys
        team_stats = {stat['category']: stat['stat'] for stat in team['stats']}

        if team['homeAway'] == "home":
            home_team_stats = team_stats
        else:
            away_team_stats = team_stats

    return home_team_stats, away_team_stats


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
        html.Div(description, style={"width": "150px", "textAlign": "left", "fontSize": "12px", "fontWeight": "bold"}),
        html.Span(f"{away_value:.1f} ({away_rank})" if away_rank is not None else f"{away_value:.1f}",
                  style={"width": "125px", "textAlign": "right", "fontSize": "12px", "padding": "3px"}),
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
        html.Span(f"{home_value:.1f} ({home_rank})" if home_rank is not None else f"{home_value:.1f}",
                  style={"width": "125px", "textAlign": "left", "float": "right", "fontSize": "12px", "padding": "3px"}),
        html.Div(description, style={"width": "150px", "textAlign": "right", "fontSize": "12px", "fontWeight": "bold"})  # Right-side Stat label
    ], style={"display": "flex", "alignItems": "center", "marginBottom": "5px"})


def display_matchup(game_info):
    home_id = game_info['home_id']
    away_id = game_info['away_id']
    home_offense_stats = get_team_stats('offense', home_id)
    away_offense_stats = get_team_stats('offense', away_id)
    home_defense_stats = get_team_stats('defense', home_id)
    away_defense_stats = get_team_stats('defense', away_id)

    # Check that items are indeed dictionaries.
    if not isinstance(home_defense_stats, dict):
        raise TypeError(
            f"home_defense_stats expected to be a dictionary, got {type(home_defense_stats)} instead.")
    if not isinstance(away_defense_stats, dict):
        raise TypeError(
            f"away_defense_stats expected to be a dictionary, got {type(away_defense_stats)} instead.")
    if not isinstance(home_offense_stats, dict):
        raise TypeError(
            f"home_offense_stats expected to be a dictionary, got {type(home_defense_stats)} instead.")
    if not isinstance(away_offense_stats, dict):
        raise TypeError(
            f"away_offense_stats expected to be a dictionary, got {type(away_defense_stats)} instead.")

    home_color = game_info['home_team_color']
    away_color = game_info['away_team_color']
    if color_similarity(home_color, away_color):
        home_color = game_info['home_team_alt_color']
    home_logo = game_info['home_team_logo']
    away_logo = game_info['away_team_logo']
    layout = html.Div([
        # Offense Section with centered logos
        html.Div([
            html.Div([
                html.Img(src=away_logo, height="40px"),
                html.H3("Offense (Per Game)",
                        style={"textAlign": "center", "fontSize": "14px", "fontWeight": "bold"}),
                html.Img(src=home_logo, height="40px")
            ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),

            # Offense stats comparison rows
            html.Div([
                create_comparison_row("total_ypg", "Total Yards", home_offense_stats['total_ypg'],
                                      away_offense_stats['total_ypg'],
                                      home_color, away_color, home_offense_stats['total_rank'],
                                      away_offense_stats['total_rank'], 'offense'),
                create_comparison_row("rush_ypg", "Rushing Yards", home_offense_stats['rush_ypg'],
                                      away_offense_stats['rush_ypg'], home_color, away_color,
                                      home_offense_stats['rush_rank'], away_offense_stats['rush_rank'], 'offense'),
                create_comparison_row("pass_ypg", "Passing Yards", home_offense_stats['pass_ypg'],
                                      away_offense_stats['pass_ypg'], home_color, away_color,
                                      home_offense_stats['pass_rank'], away_offense_stats['pass_rank'], 'offense'),
                create_comparison_row("scoring_avg", "Scoring Avg", home_offense_stats['scoring_avg'],
                                      away_offense_stats['scoring_avg'], home_color, away_color,
                                      home_offense_stats['scoring_rank'], away_offense_stats['scoring_rank'],
                                      'offense'),
            ]),
        ], style={"marginBottom": "20px"}),

        # Defense Section with centered logos
        html.Div([
            html.Div([
                html.Img(src=away_logo, height="40px"),
                html.H3("Defense (Per Game)",
                        style={"textAlign": "center", "fontSize": "14px", "fontWeight": "bold"}),
                html.Img(src=home_logo, height="40px")
            ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),

            # Defense stats comparison rows
            html.Div([
                create_comparison_row("total_ypg", "Total Yards", home_defense_stats['total_ypg'],
                                      away_defense_stats['total_ypg'],
                                      home_color, away_color, home_defense_stats['total_rank'],
                                      away_defense_stats['total_rank'], 'defense'),
                create_comparison_row("rush_ypg", "Rushing Yards", home_defense_stats['rush_ypg'],
                                      away_defense_stats['rush_ypg'], home_color, away_color,
                                      home_defense_stats['rush_rank'], away_defense_stats['rush_rank'], 'defense'),
                create_comparison_row("pass_ypg", "Passing Yards", home_defense_stats['pass_ypg'],
                                      away_defense_stats['pass_ypg'], home_color, away_color,
                                      home_defense_stats['pass_rank'], away_defense_stats['pass_rank'], 'defense'),
                create_comparison_row("scoring_avg", "Scoring Avg", home_defense_stats['scoring_avg'],
                                      away_defense_stats['scoring_avg'], home_color, away_color,
                                      home_defense_stats['scoring_rank'], away_defense_stats['scoring_rank'],
                                      'defense'),
            ]),
        ], style={"marginBottom": "20px"})
    ], style={
        "backgroundColor": "rgba(255, 255, 255, 0.8)",
        "borderRadius": "8px",
        "padding": "15px",
        "boxShadow": "0px 4px 8px rgba(0, 0, 0, 0.2)"
    })
    return layout


def display_results(week, game_info):
    game_stats = get_game_stats(week)
    game_id = game_info['id']
    away_id = game_info['away_id']
    home_id = game_info['home_id']
    home_color = game_info['home_team_color']
    away_color = game_info['away_team_color']
    if color_similarity(home_color, away_color):
        home_color = game_info['home_team_alt_color']
    home_logo = game_info['home_team_logo']
    away_logo = game_info['away_team_logo']
    for game in game_stats:
        if game['id'] == game_id:
            home_team_stats, away_team_stats = create_game_stats(game_id, game_stats)
            layout = html.Div([
                # Offense Section with centered logos
                html.Div([
                    html.Div([
                        html.Img(src=away_logo, height="40px"),
                        html.H3("Offense Results",
                                style={"textAlign": "center", "fontSize": "14px", "fontWeight": "bold"}),
                        html.Img(src=home_logo, height="40px")
                    ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),

                    # Offense stats comparison rows
                    html.Div([
                        create_comparison_row("total_ypg", "Total Yards", int(home_team_stats['totalYards']),
                                              int(away_team_stats['totalYards']),
                                              home_color, away_color, None, None, 'offense'),
                        create_comparison_row("rush_ypg", "Rushing Yards", int(home_team_stats['rushingYards']),
                                              int(away_team_stats['rushingYards']), home_color, away_color,
                                              int(home_team_stats['rushingAttempts']), int(away_team_stats['rushingAttempts']),
                                              'offense'),
                        create_comparison_row("pass_ypg", "Passing Yards", int(home_team_stats['netPassingYards']),
                                              int(away_team_stats['netPassingYards']), home_color, away_color,
                                              home_team_stats['completionAttempts'], away_team_stats['completionAttempts'],
                                              'offense'),
                        create_comparison_row("first_downs", "First Downs", int(home_team_stats['firstDowns']),
                                              int(away_team_stats['firstDowns']), home_color, away_color,
                                              home_team_stats['possessionTime'], away_team_stats['possessionTime'], 'offense'),
                    ]),
                ], style={"marginBottom": "20px"}),

                # Defense Section with centered logos
                html.Div([
                    html.Div([
                        html.Img(src=away_logo, height="40px"),
                        html.H3("Defense Results",
                                style={"textAlign": "center", "fontSize": "14px", "fontWeight": "bold"}),
                        html.Img(src=home_logo, height="40px")
                    ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),

                    # Defense stats comparison rows
                    html.Div([
                        create_comparison_row("tackles", "Tackles", int(home_team_stats['tackles']),
                                              int(away_team_stats['tackles']), home_color, away_color, None, None, 'offense'),
                        create_comparison_row("sacks", "Sacks", int(home_team_stats['sacks']),
                                              int(away_team_stats['sacks']), home_color, away_color, None, None,'offense'),
                        create_comparison_row("qb_hurry", "QB Hurries", int(home_team_stats['qbHurries']),
                                              int(away_team_stats['qbHurries']), home_color, away_color, None, None,'offense'),
                        create_comparison_row("turnovers", "Turnovers", int(away_team_stats['turnovers']),
                                              int(home_team_stats['turnovers']), home_color, away_color, None, None,'offense'),
                    ]),
                ], style={"marginBottom": "20px"})
            ], style={
                "backgroundColor": "rgba(255, 255, 255, 0.8)",
                "borderRadius": "8px",
                "padding": "15px",
                "boxShadow": "0px 4px 8px rgba(0, 0, 0, 0.2)"
            })
            return layout

