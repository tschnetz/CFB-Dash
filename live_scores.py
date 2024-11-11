import json
from datetime import datetime
import pandas as pd
from pytz import timezone



def get_scoreboard():

    querystring = {"classification": "fbs"}
    return fetch_data_from_api(url, query_params=querystring)


def team_information():
    with open('data/team_info.json', 'r') as file:
        data_dict = json.load(file)
    colors_logos_df = pd.DataFrame(data_dict)[['id', 'logos', 'color']]
    # Drop rows where logos or color is None
    colors_logos_df = colors_logos_df[colors_logos_df['logos'].notna() & colors_logos_df['color'].notna()]
    # Handle lists of logos
    colors_logos_df['logos'] = colors_logos_df['logos'].apply(lambda x: x[0] if isinstance(x, list) else x)
    # Update URLs to use https
    colors_logos_df['logos'] = colors_logos_df['logos'].str.replace('http://', 'https://')
    return colors_logos_df


def add_logos(games_df):
    logos_df = team_information()
    # Merge logos and colors for the home team
    games_with_logos = games_df.merge(logos_df, left_on='home_id', right_on='id', how='left')
    games_with_logos = games_with_logos.rename(columns={'logos': 'home_team_logo', 'color': 'home_team_color'}).drop(
        'id', axis=1)

    # Merge logos and colors for the away team
    games_with_logos = games_with_logos.merge(logos_df, left_on='away_id', right_on='id', how='left')
    games_with_logos = games_with_logos.rename(columns={'logos': 'away_team_logo', 'color': 'away_team_color'}).drop(
        'id', axis=1)

    return games_with_logos


def create_scoreboard():
    scoreboard = get_scoreboard()
    games_list = [
        {
            'home_id': game['homeTeam']['id'],
            'away_id': game['awayTeam']['id'],
            'home_team': game['homeTeam']['name'],
            'away_team': game['awayTeam']['name'],
            'status': game['status'],
            'period': game['period'],
            'clock': game['clock'],
            'tv': game['tv'],
            'situation': game['situation'],
            'possession': game['possession'],
            'home_team_score': game['homeTeam']['points'],
            'away_team_score': game['awayTeam']['points'],
            'spread': game['betting']['spread'],
        }
        for game in scoreboard
    ]
    return pd.DataFrame(games_list)


# Main scoreboard display function
@st.fragment(run_every="15s")
def display_scoreboard():
    # Fetch and process the scoreboard data
    games_df = create_scoreboard()
    games_with_logos = add_logos(games_df)

    # Only add the header once, not multiple times
    st.markdown(f"### Games in Progress")

    for index, game in games_with_logos.iterrows():
        if game['status'] == 'in_progress':  # Only display in-progress or finished games
            away_color = game['away_team_color'] or "#ffffff"
            home_color = game['home_team_color'] or "#ffffff"

            st.components.v1.html(f"""
                <div style="background: linear-gradient(to right, {away_color}50, {home_color}50);
                            border-radius: 20px; padding: 20px; margin-bottom: 20px; font-family: 'Verdana', sans-serif;
                            display: flex; justify-content: space-between; align-items: center; 
                            text-align: center;
                            width: 100%; max-width: 1200px; margin-left: auto; margin-right: auto; box-sizing: border-box;">

                    <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;">
                        <div style="display: flex; align-items: center; margin-bottom: 5px;">
                            <img src='{game['away_team_logo']}' width='50' style='margin-left: 10px;'>
                            {" 🏈" if game['possession'] == 'away' else ""} 
                        </div>
                        <div style="font-size: 14px; font-weight: bold; margin-top: 0; overflow: hidden;
                                    text-overflow: ellipsis; white-space: nowrap; max-width: 250px;">{game['away_team']}</div>
                        <div style="font-size: 24px; font-weight: bold; margin-top: 0;">{int(game['away_team_score'])}</div>
                    </div>

                    <div style="flex: 1; text-align: center; display: flex; flex-direction: column; justify-content: center;">
                        <h4 style="font-family: 'Verdana', sans-serif; margin: 0;">{int(game['period'])}Q</h4>
                        <p style="margin: 0;">{game['clock']}</p>
                        <p style="margin: 0; font-size: 12px"><i>{f"{game['tv']} ▪️ {game['spread']}"}</i></p><br>
                        <p style="margin: 0;">{game['situation'] or "No situation available"}</p>
                    </div>

                    <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;"> 
                        <div style="display: flex; align-items: center; margin-bottom: 5px;">
                            <img src='{game['home_team_logo']}' width='50' style='margin-left: 10px;'>
                            {" 🏈" if game['possession'] == 'home' else ""} 
                        </div>
                        <div style="font-size: 14px; font-weight: bold; margin-top: 0; overflow: hidden;
                                    text-overflow: ellipsis; white-space: nowrap; max-width: 250px;">{game['home_team']}</div>
                        <div style="font-size: 24px; font-weight: bold; margin-top: 0;">{int(game['home_team_score'])}</div>
                    </div>
                </div>
            """)

    # Display the last updated time with Verdana font applied
    edt = timezone('US/Eastern')
    # Accurate timezone handling
    now = datetime.now(edt)
    last_updated = now.strftime("%I:%M:%S %p")
    st.markdown(
        f"<div style='text-align: center; font-size: 12px; color: #888;'><i>Last updated: {last_updated}</i></div>",
        unsafe_allow_html=True
    )


# Call the display scoreboard function
display_scoreboard()