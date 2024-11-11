# app.py
import dash
import dash_bootstrap_components as dbc
from flask import Flask
from config import PORT
from callbacks import register_callbacks
from cache_config import cache
from layout import main_layout


# Initialize Flask server
server = Flask(__name__)
# Initialize Dash app with Flask server
app = dash.Dash(__name__, server=server, external_stylesheets=[dbc.themes.BOOTSTRAP],
                suppress_callback_exceptions=True, title="CFB Games")

# Initialize cache and clear
cache.init_app(app.server)
with app.server.app_context():
   cache.clear()

# Set up the app layout with navigation and page container
app.layout = main_layout

# Register callbacks
register_callbacks(app)

# Run Dash server
if __name__ == "__main__":
    app.run_server(debug=False, host='0.0.0.0', port=PORT)