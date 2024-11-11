import requests
from config import HEADERS

# Helper function to make HTTP requests and handle errors
def fetch_data_from_api(url, query_params=None):
    try:
        response = requests.get(url, headers=HEADERS, params=query_params)
        response.raise_for_status()  # Raise an HTTPError for bad responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
