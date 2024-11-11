import json
from datetime import date
from config import headers
import streamlit as st
import pandas as pd
import requests


YEAR = 2024

def team_information():
    with open('data/team_info.json', 'r') as file:
        data_dict = json.load(file)
    colors_logos_df = pd.DataFrame(data_dict)
    colors_logos_df = colors_logos_df[['school', 'logos']]
    # drop rows with logos = None
    colors_logos_df = colors_logos_df[colors_logos_df['logos'].notna()]
    colors_logos_df['logos'] = colors_logos_df['logos'].apply(lambda x: x[0] if isinstance(x, list) else x)
    colors_logos_df['logos'] = colors_logos_df['logos'].str.replace('http://', 'https://')

    return colors_logos_df


def get_schedule():
    url = "https://api.collegefootballdata.com/calendar"
    querystring = {"year": YEAR}
    payload = ""
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    weeks = pd.DataFrame(response.json())
    return weeks


def get_games():
    url = "https://api.collegefootballdata.com/games"
    querystring = {"year": YEAR, "week": week, "division": "fbs"}
    payload = ""
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    games = pd.DataFrame(response.json())
    return games


def get_records(year):
    url = f'https://api.collegefootballdata.com/records?year={year}'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to fetch data. Status code: {response.status_code}")


def create_records(valid_records):
    if not valid_records:
        return pd.DataFrame()
    team_records_list = []
    for record in valid_records:
        team_record = {
            'team': record['team'],  # Include teamId for merging
            'Total Wins': record['total'].get('wins', 0),
            'Total Losses': record['total'].get('losses', 0),
            'Conference Wins': record['conferenceGames'].get('wins', 0),
            'Conference Losses': record['conferenceGames'].get('losses', 0),
        }
        team_records_list.append(team_record)
    return pd.DataFrame(team_records_list)


def select_week():
    weeks_df = get_schedule()
    weeks_df['firstGameStart'] = pd.to_datetime(weeks_df['firstGameStart'])
    weeks_df['lastGameStart'] = pd.to_datetime(weeks_df['lastGameStart'])
    weeks_df['firstGameStart'] = weeks_df['firstGameStart'].dt.strftime('%b-%d')
    weeks_df['lastGameStart'] = weeks_df['lastGameStart'].dt.strftime('%b-%d')
    selected = []
    for index, row in weeks_df.iterrows():
        week_str = f"Week {row['week']} ({row['firstGameStart']} - {row['lastGameStart']})"
        selected.append(week_str)
    current_date = date.today()
    week_number = current_date.isocalendar()[1] - 35
    selected_week = st.sidebar.selectbox("Select week", selected, index=week_number)
    week = selected.index(selected_week) + 1
    return week


def clean_games(games_df):
    # Step 1: Convert 'start_date' column to datetime (if it's not already in datetime format)
    games_df['start_date'] = pd.to_datetime(games_df['start_date'], errors='coerce')

    # Check for any rows where the conversion failed and handle them
    if games_df['start_date'].isnull().any():
        raise ValueError("There are invalid date formats in the 'start_date' column.")

    # Step 2: Ensure that the 'start_date' is timezone-naive, and then localize to UTC
    if games_df['start_date'].dt.tz is None:
        games_df['start_date'] = games_df['start_date'].dt.tz_localize('UTC')

    # Step 3: Convert the datetime from UTC to Eastern Time
    games_df['start_date'] = games_df['start_date'].dt.tz_convert('US/Eastern')

    # Step 4: Add a new column for the day of the week
    games_df['day_of_week'] = games_df['start_date'].dt.day_name()

    # Step 4: Format the datetime as 'MMM-dd HH:MM AM/PM'
    games_df['start_date'] = games_df['start_date'].dt.strftime('%b-%d %I:%M %p')
    games_df = games_df[['id', 'start_date', 'day_of_week', 'home_team', 'home_points', 'home_line_scores', 'away_team', 'away_points']]
    return games_df


def get_lines():
    url = "https://api.collegefootballdata.com/lines"
    querystring = {"year": YEAR, "week": week}
    payload = ""
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    betting_lines = []
    for game in response.json():
        # Find the ESPN Bet line
        espn_line = next((line for line in game['lines'] if line['provider'] == 'ESPN Bet'), None)
        if espn_line:
            betting_lines.append({
                'id': game['id'],
                'spread': espn_line['formattedSpread'],
                'over_under': espn_line['overUnder'],
                'home_moneyline': espn_line['homeMoneyline'],
                'away_moneyline': espn_line['awayMoneyline'],
            })
    game_lines = pd.DataFrame(betting_lines)
    return game_lines


def get_media():
    url = "https://api.collegefootballdata.com/games/media"
    querystring = {"year": YEAR, "week": week}
    payload = ""
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    media = []
    for game in response.json():
        # Get the media outlet for each game
        media.append({
            'id': game['id'],
            'outlet': game['outlet'],
        })
    # If media has games with duplicate id, concatenate the outlets in one and remove the duplicate
    media_df = pd.DataFrame(media)
    media_df = media_df.groupby('id')['outlet'].apply(', '.join).reset_index()
    return media_df


def add_logos():
    logos_df = team_information()
    # Drop faulty Charlotte logo
    logos_df = logos_df[logos_df['logos'] != 'http://a.espncdn.com/i/teamlogos/ncaa/500/3253.png']

    # Merge logos for the home team
    games_with_logos = games_df.merge(logos_df, left_on='home_team', right_on='school', how='left')
    games_with_logos = games_with_logos.rename(columns={'logos': 'home_team_logo'}).drop('school', axis=1)

    # Merge logos for the visiting team
    games_with_logos = games_with_logos.merge(logos_df, left_on='away_team', right_on='school', how='left')
    games_with_logos = games_with_logos.rename(columns={'logos': 'away_team_logo'}).drop('school', axis=1)
    return games_with_logos


def display_schedule(home_team, home_team_logo, home_score, away_team, away_team_logo, away_score, game_date, weekday,
                     spread, over_under, home_moneyline, away_moneyline, outlet,
                     home_total_wins, home_total_losses, home_conf_wins, home_conf_losses,
                     away_total_wins, away_total_losses, away_conf_wins, away_conf_losses):
    home_score_display = int(home_score) if not pd.isna(home_score) else ""  # Blank if NaN
    away_score_display = int(away_score) if not pd.isna(away_score) else ""  # Blank if NaN

    return f"""
    <div style="display: flex; align-items: center; justify-content: space-between;">
        <div style="text-align: center; font-size: 16px;">{weekday}<br>{game_date}</div>
        <div style="text-align: center;">
            <img src="{away_team_logo}" width="50"><br>
            <span style="font-size: 20px;"><b>{away_team}</b></span><br>
            <span style="font-size: 18px;">{away_total_wins}-{away_total_losses}, {away_conf_wins}-{away_conf_losses}</span><br>
            <span style="font-size: 30px; font-weight: bold;">{away_score_display}</span>  <!-- Larger score -->
        </div>
        <div style="text-align: center; font-size: 18px;">at</div>
        <div style="text-align: center;">
            <img src="{home_team_logo}" width="50"><br>
            <span style="font-size: 20px;"><b>{home_team}</b></span><br>
            <span style="font-size: 18px;">{home_total_wins}-{home_total_losses}, {home_conf_wins}-{home_conf_losses}</span><br>
            <span style="font-size: 30px; font-weight: bold;">{home_score_display}</span>  <!-- Larger score -->
        </div>
        <div style="text-align: center; font-size: 14px; margin-top: 5px;">
            <b>{spread}</b><br>{over_under} O/U<br>a:{away_moneyline} h: {home_moneyline} <br>{outlet}
        </div>
    </div>
    <hr>
    """


# Main body
week = select_week()
games_df = get_games()
schedule = clean_games(games_df)
games_with_logos = add_logos() # Add team logos
media_df = get_media() # Add media outlet
betting_df = get_lines() # Add betting info
if not betting_df.empty:
    games_with_betting = games_with_logos.merge(betting_df, on='id', how='left')
    games_with_media = games_with_betting.merge(media_df, on='id', how='left')
else:
    games_with_media = games_with_logos.merge(media_df, on='id', how='left')
    games_with_media['spread'] = 'N/A'
    games_with_media['over_under'] = 'N/A'
    games_with_media['home_moneyline'] = 'N/A'
    games_with_media['away_moneyline'] = 'N/A'

records = create_records(get_records(YEAR)) # Add team records
games_with_records = games_with_media.merge(records, left_on='home_team', right_on='team', how='left', suffixes=('', '_home'))
games_with_records = games_with_records.merge(records, left_on='away_team', right_on='team', how='left', suffixes=('', '_away'))

st.header(f"Week {week} CFB Schedule", divider='blue')
for index, row in games_with_records.iterrows():
    st.markdown(display_schedule(
        row['home_team'],  # Home team name
        row['home_team_logo'],  # Home team logo
        row['home_points'],  # Home team score
        row['away_team'],  # Away team name
        row['away_team_logo'],  # Away team logo
        row['away_points'],  # Away team score
        row['start_date'],  # Game date
        row['day_of_week'],  # Day of the week
        row['spread'],  # Spread
        row['over_under'],  # Over/Under
        row['home_moneyline'],  # Home team moneyline
        row['away_moneyline'],  # Away team moneyline
        row['outlet'],  # Media outlet
        row['Total Wins'], row['Total Losses'], row['Conference Wins'], row['Conference Losses'],  # Home team records
        row['Total Wins_away'], row['Total Losses_away'], row['Conference Wins_away'], row['Conference Losses_away'], # Away team records
    ), unsafe_allow_html=True)