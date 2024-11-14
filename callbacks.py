import json
import dash
from dash import html, Input, Output, MATCH, State, callback_context
import dash_bootstrap_components as dbc
from datetime import datetime, date
from utils import (create_scoreboard, get_schedule, get_games, clean_games, get_media,
                   create_records, get_records, add_logos, get_lines, get_team_stats,
                   create_comparison_row, format_time, color_similarity, display_matchup, display_results)


initial_api_call_returned_events = True

def register_callbacks(app):

    @app.callback(
        Output('week-selector', 'options'),
        Output('week-selector', 'value'),
        [Input('week-options-store', 'data')],
    )
    def update_week_options(week_options_fetched):
        # Fetch schedule data for weeks
        weeks_data = get_schedule()  # This function should return a list of dictionaries containing week data

        # Process each week's information to create dropdown options
        week_options = []
        for week in weeks_data:
            # Parse ISO 8601 format (e.g., '2024-08-24T04:00:00.000Z')
            first_game_start = datetime.fromisoformat(week['firstGameStart'].replace('Z', '')).date() \
                if isinstance(week['firstGameStart'], str) else week['firstGameStart']
            last_game_start = datetime.fromisoformat(week['lastGameStart'].replace('Z', '')).date() \
                if isinstance(week['lastGameStart'], str) else week['lastGameStart']

            week_label = f"Week {week['week']} ({first_game_start.strftime('%b-%d')} - {last_game_start.strftime('%b-%d')})"
            week_options.append({'label': week_label, 'value': week['week'], 'lastGameStart': last_game_start})

        # Set default week selection based on the current date or the first available week
        current_date = date.today()
        selected_value = None
        for week in week_options:
            if current_date <= week['lastGameStart']:
                selected_value = week['value']
                break

        # Default to the first week if no match is found
        if selected_value is None and week_options:
            selected_value = week_options[0]['value']

        # Drop 'lastGameStart' from week_options for display
        week_options = [{'label': option['label'], 'value': option['value']} for option in week_options]

        return week_options, selected_value


    @app.callback(
        Output('games-data', 'data'),
        Input('selected-week', 'data'),
    )
    def create_display(week):
        # Fetch and process the scoreboard data
        # print(f"Creating display for week {week}")
        games = get_games(week)
        schedule = clean_games(games)  # Clean and format game data
        games_with_logos = add_logos(schedule)  # Add team logos
        media_data = get_media(week)  # Add media outlet information
        betting_lines = get_lines(week)  # Add betting info

        # Join betting lines to games by 'id'
        games_with_betting = []
        for game in games_with_logos:
            betting_info = next((bet for bet in betting_lines if bet['id'] == game['id']), None)
            game_with_betting = {**game}
            if betting_info:
                game_with_betting.update({
                    'spread': betting_info['spread'],
                    'over_under': betting_info['over_under']
                })
            else:
                game_with_betting.update({
                    'spread': 'N/A',
                    'over_under': 'N/A',
                    'home_moneyline': 'N/A',
                    'away_moneyline': 'N/A'
                })
            games_with_betting.append(game_with_betting)

        # Join media outlets to games by 'id'
        games_with_media = []
        for game in games_with_betting:
            media_info = next((media for media in media_data if media['id'] == game['id']), None)
            game_with_media = {**game}
            if media_info:
                game_with_media['outlet'] = media_info['outlet']
            else:
                game_with_media['outlet'] = "N/A"
            games_with_media.append(game_with_media)

        # Add team records
        team_records = create_records(get_records())
        team_records_by_name = {record['team']: record for record in team_records}

        games_with_records = []
        for game in games_with_media:
            home_team_record = team_records_by_name.get(game['home_team'], {
                'Total Wins': 'N/A',
                'Total Losses': 'N/A',
                'Conference Wins': 'N/A',
                'Conference Losses': 'N/A'
            })
            away_team_record = team_records_by_name.get(game['away_team'], {
                'Total Wins': 'N/A',
                'Total Losses': 'N/A',
                'Conference Wins': 'N/A',
                'Conference Losses': 'N/A'
            })

            game_with_records = {**game}
            game_with_records.update({
                'home_total_wins': home_team_record.get('Total Wins'),
                'home_total_losses': home_team_record.get('Total Losses'),
                'home_conference_wins': home_team_record.get('Conference Wins'),
                'home_conference_losses': home_team_record.get('Conference Losses'),
                'away_total_wins': away_team_record.get('Total Wins'),
                'away_total_losses': away_team_record.get('Total Losses'),
                'away_conference_wins': away_team_record.get('Conference Wins'),
                'away_conference_losses': away_team_record.get('Conference Losses')
            })

            games_with_records.append(game_with_records)

        return games_with_records


    # Main scoreboard display function
    @app.callback(
        [Output('static-game-info', 'children'), Output('init-complete', 'data')],
        [Input('week-selector', 'value')]
    )
    def display_static_items(selected_week):
        # print("Displaying static items")
        current_games = create_display(selected_week)
        # Convert DataFrame to list of dictionaries
        sorted_games = sorted(current_games, key=lambda x: (
            x['completed'] == True,
            x['completed'] == False,
        ))
        games_info = []
        for game in sorted_games:
            game_id = game['id']
            home_color = game['home_team_color']
            away_color = game['away_team_color']
            game_completed = game['completed']
            game_status = 'Scheduled'
            home_team_extra_info = ""
            away_team_extra_info = ""

            if game_completed:
                home_score = game['home_points']
                away_score = game['away_points']
                quarter_time_display = "Final"
                game_status = "Completed"
            else:
                home_score = ""
                away_score = ""
                quarter_time_display = ""

            games_info.append(
                dbc.Button(
                    dbc.Row([
                        dbc.Col(html.Img(src=game['away_team_logo'], height="100px"), width=1,
                                style={'textAlign': 'center'}),
                        dbc.Col(
                            html.Div([
                                html.H4(game['away_team'], style={'color': away_color, 'fontWeight': 'bold'}),
                                html.P(f"{game['away_total_wins']} - {game['away_total_losses']}", style={'color': away_color, 'fontWeight': 'bold', 'margin': '0', 'padding': '0'}),
                                html.H3(away_score, id={'type': 'away-score', 'index': game_id},
                                        style={'color': away_color, 'fontWeight': 'bold'}),
                                html.H6(away_team_extra_info, id={'type': 'away-extra', 'index': game_id},
                                        style={'color': away_color}),
                            ], style={'textAlign': 'center'}),
                            width=3,
                        ),
                        dbc.Col(
                            html.Div([
                                html.H6(game_status, id={'type': 'game-status', 'index': game_id},
                                        style={'fontWeight': 'bold'}),
                                html.H5(quarter_time_display, id={'type': 'quarter-time', 'index': game_id},
                                        style={'fontWeight': 'bold'}),
                                html.H6(f"{game['spread']} • O/U {game['over_under']}") if game['spread'] else "",
                                html.P(f"{game['day_of_week']}, {game['start_date']}", style={'margin': '0', 'padding': '0'}),
                                html.P(f"{game['outlet']}",
                                       style={'margin': '0', 'padding': '0'}),
                            ], style={'textAlign': 'center'}),
                            width=4
                        ),
                        dbc.Col(
                            html.Div([
                                html.H4(game['home_team'], style={'color': home_color, 'fontWeight': 'bold'}),
                                html.P(f"{game['home_total_wins']} - {game['home_total_losses']}", style={'color': home_color, 'fontWeight': 'bold', 'margin': '0', 'padding': '0'}),
                                html.H3(home_score, id={'type': 'home-score', 'index': game_id},
                                        style={'color': home_color, 'fontWeight': 'bold'}),
                                html.H6(home_team_extra_info, id={'type': 'home-extra', 'index': game_id},
                                        style={'color': home_color}),
                            ], style={'textAlign': 'center'}),
                            width=3
                        ),
                        dbc.Col(html.Img(src=game['home_team_logo'], height="100px"), width=1,
                                style={'textAlign': 'center'}),

                    ], className="game-row", style={'padding': '10px'}),
                    id={'type': 'game-button', 'index': game_id},
                    n_clicks=0,
                    color='medium',
                    className='dash-bootstrap',
                    style={
                        '--team-home-color': home_color,
                        '--team-away-color': away_color,
                        'width': '100%',
                        'textAlign': 'left'
                    },
                    value=game_id,
                )
            )
            games_info.append(html.Div(id={'type': 'matchup', 'index': game_id}, children=[]))
            games_info.append(html.Hr())

        return games_info, True


    @app.callback(
            [
                Output({'type': 'home-score', 'index': MATCH}, 'children'),
                Output({'type': 'away-score', 'index': MATCH}, 'children'),
                Output({'type': 'game-status', 'index': MATCH}, 'children'),
                Output({'type': 'quarter-time', 'index': MATCH}, 'children'),
                Output({'type': 'home-extra', 'index': MATCH}, 'children'),
                Output({'type': 'away-extra', 'index': MATCH}, 'children'),
            ],
            [Input('scores-data', 'data')],
            [State({'type': 'game-button', 'index': MATCH}, 'value')],
    )
    def display_dynamic_items(scores_data, game_id):
        game_data = next((game for game in scores_data if game.get('game_id') == game_id), None)

        if not game_data:
            return [dash.no_update] * 6

        game_status = game_data.get('status', '')
        home_score = game_data.get('home_team_score', "")
        away_score = game_data.get('away_team_score', "")
        quarter = game_data.get('period', "")
        time_remaining = game_data.get('clock', "")
        time_remaining = format_time(time_remaining)
        down_distance = game_data.get('situation', "")
        possession_team = game_data.get('possession', "")
        home_team_extra_info = "🏈 " + down_distance if possession_team == "home" else ""
        away_team_extra_info = "🏈 " + down_distance if possession_team == "away" else ""
        quarter_time_display = "Final" if game_status == "completed" else f"{quarter} Qtr ● {time_remaining}"

        return home_score, away_score, game_status, quarter_time_display, home_team_extra_info, away_team_extra_info


    @app.callback(
        [Output('scores-data', 'data'),
         Output('in-progress-flag', 'data', allow_duplicate=True),
         Output('interval-scores', 'n_intervals')],
        [Input('interval-scores', 'n_intervals'),
         Input('init-complete', 'data')],
        [State('scores-data', 'data')],
        prevent_initial_call=True
    )
    def update_game_data(n_intervals, init_complete, prev_scores_data):
        global initial_api_call_returned_events

        if not init_complete:
            return dash.no_update, dash.no_update, n_intervals

        if initial_api_call_returned_events is False:
            return dash.no_update, False, n_intervals

        try:
            games_data = create_scoreboard()  # Ensure this returns a list of games with all fields
            if not games_data:
                return dash.no_update, False, n_intervals

            updated_game_data = []
            games_in_progress = False

            for game in games_data:
                # Check if the game is in progress
                game_status = game.get('status', '')
                if game_status == "in_progress":
                    games_in_progress = True
                    game['status'] = 'In Progress'
                    updated_game_data.append(game)

                # Append the entire game dictionary with all fields

            # Check if the data has changed
            if prev_scores_data == updated_game_data:
                return dash.no_update, games_in_progress, n_intervals

            # Return updated data, in-progress flag, and interval count
            return updated_game_data, games_in_progress, n_intervals

        except Exception as e:
            print(f"Error updating game data: {e}")
            return dash.no_update, dash.no_update, n_intervals


    @app.callback(
        Output({'type': 'matchup', 'index': dash.dependencies.ALL}, 'children'),
        [Input({'type': 'game-button', 'index': dash.dependencies.ALL}, 'n_clicks'),
         Input('week-selector', 'value')],
        [State('games-data', 'data'),
         State({'type': 'game-button', 'index': dash.dependencies.ALL}, 'id')],
    )
    def display_game_detail(n_clicks_list, week, games_data, button_ids):
        outputs = [[] for _ in n_clicks_list]
        ctx = callback_context
        if not ctx.triggered:
            return outputs

        triggered_button = ctx.triggered[0]['prop_id'].split('.')[0]
        game_id = json.loads(triggered_button)['index']
        triggered_button_index = next(i for i, btn_id in enumerate(button_ids) if btn_id['index'] == game_id)

        if n_clicks_list[triggered_button_index] % 2 == 1:
            game_info = next((game for game in games_data if game['id'] == game_id), None)
            if not game_info:
                return outputs
            if game_info['completed']:
                layout = display_results(week, game_info)
            else:
                layout = display_matchup(game_info)


            outputs[triggered_button_index] = layout

        return outputs


