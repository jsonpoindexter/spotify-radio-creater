import os
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

# --- Trigger endpoint ---
@app.route('/trigger', methods=['POST'])
def trigger():
    try:
        sp = get_spotify_client()

        # Get the current playback info
        current_playback = sp.current_playback()
        if not current_playback or not current_playback.get('item'):
            return jsonify({"error": "No song is currently playing"}), 400

        current_track = current_playback['item']
        primary_artist = current_track['artists'][0]

        # Get detailed info for the primary artist, including genres.
        artist_details = sp.artist(primary_artist['id'])
        artist_genres = artist_details.get('genres', [])

        app.logger.info(f"Starting custom radio for {primary_artist['name']} ({artist_genres})")

        # Use the first genre (if available) as the search query; fallback to the artist name.
        if artist_genres:
            query = artist_genres[0]
        else:
            query = primary_artist['name']

        # Perform a search for tracks using the chosen query
        # Note: The search endpoint doesn't support a dedicated genre filter for tracks,
        # so we use the genre as a keyword.
        search_results = sp.search(q=query, type='track', limit=20)
        tracks = search_results.get('tracks', {}).get('items', [])
        track_uris = [track['uri'] for track in tracks]

        # Start playback with the list of tracks gathered from the search.
        sp.start_playback(uris=track_uris)

        return jsonify({
            "message": "Custom song radio started",
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