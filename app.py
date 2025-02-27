import json
import os
import random
import sys
import logging

import openai
import requests
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
SCOPE = os.environ.get('SPOTIFY_SCOPE')
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

# --- OpenAI API Configuration ---
openai.api_key = os.getenv("OPENAI_API_KEY", os.environ.get('OPENAI_API_KEY'))
if not openai.api_key:
    app.logger.info("OPENAI_API_KEY is not set")

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

# --- OpenAI-Enhanced Trigger Endpoint ---
@app.route('/trigger-openai', methods=['POST'])
def trigger_openai():
    try:
        sp = get_spotify_client()

        # Get the current playback info
        current_playback = sp.current_playback()
        if not current_playback or not current_playback.get('item'):
            return jsonify({"error": "No song is currently playing"}), 400

        current_track = current_playback['item']
        primary_artist = current_track['artists'][0]
        # Spotify Track ID
        track_id = current_track['id']

        app.logger.info(f"Current track: {current_track['name']} by {primary_artist['name']} (ID: {track_id})")

        # Prepare a prompt for OpenAI
        prompt = (
            f"I'm currently listening to '{current_track['name']}' by '{primary_artist['name']}'. "
            "Can you suggest 20 similar genre / mood (but not mainstream) track recommendations? "
            "Please provide the answer only as a JSON array of objects, where each object has exactly two keys: "
            "'track_name' and 'artist'."
        )

        app.logger.info(f"OpenAI prompt: {prompt}")

        # Call OpenAI API using ChatCompletion
        openai_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful music expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600,
        )
        response_message = openai_response.choices[0].message.content.strip()
        app.logger.info(f"OpenAI response: {response_message}")

        # Attempt to parse the JSON response from OpenAI
        try:
            recommendations = json.loads(response_message)
        except Exception as parse_error:
            return jsonify({
                "error": "Failed to parse OpenAI response as JSON",
                "openai_response": response_message,
                "parse_error": str(parse_error)
            }), 500

        if not isinstance(recommendations, list):
            return jsonify({"error": "OpenAI response JSON is not a list"}), 500


        app.logger.info(f"OpenAI recommendations: {recommendations}")

        # For each recommendation, use Spotify Search to find the track URI.
        track_uris = []
        for rec in recommendations:
            track_query = f"{rec.get('track_name', '')} {rec.get('artist', '')}"
            search_result = sp.search(q=track_query, type='track', limit=1)
            items = search_result.get('tracks', {}).get('items', [])
            if items:
                track_uri = items[0]['uri']
                track_uris.append(track_uri)

        if not track_uris:
            return jsonify({"error": "No tracks found from OpenAI recommendations"}), 500

        # Shuffle the track URIs for additional randomness
        random.shuffle(track_uris)

        # Start playback with the collected URIs
        sp.start_playback(uris=track_uris)

        return jsonify({
            "message": "Custom radio generated using OpenAI recommendations",
            "openai_recommendations": recommendations,
            "track_uris": track_uris
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- ReccoBeats Trigger Endpoint ---
@app.route('/trigger-reccobeats', methods=['POST'])
def trigger_reccobeats():
    try:
        sp = get_spotify_client()

        # Retrieve current playback info from Spotify.
        current_playback = sp.current_playback()
        if not current_playback or not current_playback.get('item'):
            return jsonify({"error": "No song is currently playing"}), 400

        current_track = current_playback['item']
        primary_artist = current_track['artists'][0]
        track_name = current_track['name']
        artist_name = primary_artist['name']
        track_id = current_track['id']

        # Log the seed info (optional)
        app.logger.info(f"Current track: {track_name} by {artist_name} (ID: {track_id})")

        # Call the ReccoBeats API using the provided example
        reccobeats_url = "https://api.reccobeats.com/v1/track/recommendation"
        params = {
            "size": 20,
            "seeds": [track_id] # >= 1, <= 5 List of Track's ReccoBeats ID or Spotify ID.
        }
        headers = {
            'Accept': 'application/json'
        }
        # In this example, we do not pass additional parameters.
        response = requests.get(reccobeats_url, params=params, headers=headers)
        app.logger.info(f"ReccoBeats API response: {response.status_code} - {response.text}")
        if response.status_code != 200:
            return jsonify({
                "error": f"ReccoBeats API error: {response.status_code}",
                "response_text": response.text
            }), 500

        # Parse the JSON recommendations from ReccoBeats.
        json_response = response.json()
        # recommendations is under .content key
        recommendations = json_response.get('content', [])
        app.logger.info(f"ReccoBeats recommendations: {recommendations}")

        if not isinstance(recommendations, list):
            return jsonify({"error": "ReccoBeats response JSON is not a list"}), 500

        # For each recommendation, search Spotify to find the track URI.
        track_uris = []
        for rec in recommendations:
            rec_href=rec.get('href', '')
            track_uris.append(rec_href)

        if not track_uris:
            return jsonify({"error": "No tracks found from ReccoBeats recommendations"}), 500

        # Shuffle the list for additional randomness.
        random.shuffle(track_uris)

        # Start playback on the active Spotify device.
        sp.start_playback(uris=track_uris)

        return jsonify({
            "message": "Custom radio generated using ReccoBeats recommendations",
            "reccobeats_recommendations": recommendations,
            "track_uris": track_uris
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Listen on all interfaces on port 5002 so the container maps correctly
    app.run(host='0.0.0.0', port=5002, debug=True)