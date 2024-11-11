import dash
from dash import dcc, html
import dash_bootstrap_components as dbc



main_layout = dbc.Container([
    dcc.Interval(id='interval-scores', interval=12 * 1000, n_intervals=0),
    dcc.Store(id='init-complete', data=False),
    dcc.Store(id='in-progress-flag', data=False),
    dcc.Store(id='selected-week', data=None),
    dcc.Store(id='week-options-store', data=False),
    dcc.Store(id='scores-data', data=[]),
    dcc.Store(id='games-data', data={}),

    dbc.Card([
        dbc.CardBody(
            html.Div([
                html.Img(src="assets/NCAA_logo.webp", height="100px", style={"marginRight": "15px"}),
                html.H1("CFB Games", style={
                    "display": "inline-block",
                    "verticalAlign": "middle",
                    "color": "white",
                    "padding": "10px 20px",
                    # "backgroundColor": "#1E3A5F",
                    "borderRadius": "8px",
                    "fontSize": "2.5rem",
                    "fontWeight": "bold",
                    "margin": "0"
                })
            ], style={"display": "flex", "alignItems": "center", "justifyContent": "center"})
        )
    ], style={
        "backgroundColor": "#1E3A5F",
        "marginBottom": "20px",
        "borderRadius": "8px",
        "boxShadow": "0px 4px 8px rgba(0, 0, 0, 0.3)",
        "padding": "10px"
    }),
dbc.Row(
        dbc.Col(
            dcc.Dropdown(
                id='week-selector',
                options=[],
                placeholder="Select a week",
                style={
                    "width": "100%",
                    "textAlign": "center",
                    "fontSize": "18px",
                    "padding": "3px",
                    "border": "none",
                    "borderRadius": "8px",
                    # "backgroundColor": "#FFFFFF",  # Fully opaque white background
                    "boxShadow": "0px 4px 8px rgba(0, 0, 0, 0.1)",  # Subtle shadow
                }
            ),
            width=6,  # Adjust width as needed
            style={"display": "flex", "justifyContent": "center"}  # Center the dropdown in the column
        ),
        justify="center",
        style={"marginBottom": "20px"}
    ),
# Game information loading section
    dbc.Row(
        dbc.Col(
            dcc.Loading(
                id='loading',
                type='circle',
                children=[html.Div(id='static-game-info'), html.Div(id='dynamic-game-info')]
            ),
            width=12
        )
    )
], fluid=True)


