import os
import random
import sys
import logging

from flask import Flask, request, jsonify, redirect
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)

app.logger.setLevel(logging.INFO)
app.logger.log(logging.INFO, "Starting app...")

# --- Spotify API configuration --- use environment variables
CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
if not CLIENT_ID:
    app.logger.error("SPOTIFY_CLIENT_ID is not set")
    sys.exit(1)
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
if not CLIENT_SECRET:
    app.logger.error("SPOTIFY_CLIENT_SECRET is not set")
    sys.exit(1)
REDIRECT_URI = os.environ.get('SPOTIFY_REDIRECT_URI')
if not REDIRECT_URI:
    app.logger.error("SPOTIFY_REDIRECT_URI is not set")
    sys.exit(1)
SCOPE = os.environ.get('SPOTIFY_SCOPE', 'user-read-playback-state,user-modify-playback-state')
if not SCOPE:
    app.logger.error("SPOTIFY_SCOPE is not set")
    sys.exit(1)

# Create a SpotifyOAuth instance to handle token caching
sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
)

def get_spotify_client():
    token_info = sp_oauth.get_cached_token()
    if not token_info:
        raise Exception("No token found. Please log in at /login")
    sp = spotipy.Spotify(auth=token_info['access_token'])
    return sp

# --- Authentication endpoints ---
@app.route('/login')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    return "Logged in successfully – you can now use the /trigger endpoint."

@app.route('/trigger', methods=['POST'])
def trigger():
    """
    Endpoint to trigger a custom shuffled song radio based on the currently playing track.

    This endpoint performs the following steps:
    1. Retrieves the current playback information from Spotify.
    2. Extracts the primary artist of the currently playing track.
    3. Fetches detailed information about the primary artist, including their genres.
    4. Uses a random genre or the artist's name to perform a search for tracks on Spotify.
    5. Randomly selects a set of 20 tracks from the search results.
    6. Shuffles the selected tracks and starts playback with the shuffled list.

    Returns:
        JSON response containing:
        - message: Confirmation message indicating the custom radio has started.
        - seed_track: Name of the currently playing track used as the seed.
        - seed_artist: Name of the primary artist of the currently playing track.
        - search_query: The search query used to find related tracks.
        - track_uris: List of URIs of the shuffled tracks.
        - error: Error message if an exception occurs.
    """
    try:
        sp = get_spotify_client()

        # Get current playback info
        current_playback = sp.current_playback()
        if not current_playback or not current_playback.get('item'):
            return jsonify({"error": "No song is currently playing"}), 400

        current_track = current_playback['item']
        primary_artist = current_track['artists'][0]

        # Retrieve detailed info for the primary artist
        artist_details = sp.artist(primary_artist['id'])
        artist_genres = artist_details.get('genres', [])

        # Use a random genre if available; fallback to the artist's name
        if artist_genres:
            query = random.choice(artist_genres)
        else:
            query = primary_artist['name']

        # First, perform a lightweight search to get the total number of results
        initial_search = sp.search(q=query, type='track', limit=1)
        total_results = initial_search['tracks']['total']
        # Determine a random offset; ensure we have room to fetch 20 tracks
        max_offset = max(0, total_results - 20)
        offset = random.randint(0, max_offset) if max_offset > 0 else 0

        # Fetch a set of 20 tracks using the random offset
        search_results = sp.search(q=query, type='track', limit=20, offset=offset)
        tracks = search_results.get('tracks', {}).get('items', [])
        track_uris = [track['uri'] for track in tracks]

        # Shuffle the track URIs to add extra randomness
        random.shuffle(track_uris)

        # Start playback with the shuffled list of tracks
        sp.start_playback(uris=track_uris)

        return jsonify({
            "message": "Custom shuffled song radio started",
            "seed_track": current_track['name'],
            "seed_artist": primary_artist['name'],
            "search_query": query,
            "track_uris": track_uris
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Listen on all interfaces on port 5002 so the container maps correctly
    app.run(host='0.0.0.0', port=5002, debug=True)