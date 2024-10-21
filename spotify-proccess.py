import time
import requests
from flask import Flask, redirect, request, session, jsonify
from dotenv import load_dotenv
import os
from flask_cors import CORS

# Initialize Flask application
app = Flask(__name__)

# Enable Cross-Origin Resource Sharing (CORS) for your frontend
CORS(app, resources={r"/*": {"origins": "https://solanh.github.io"}})

# Load environment variables from .env file (such as Spotify credentials)
load_dotenv()

# Secret key for sessions (ensure it's stored securely in environment variables)
app.secret_key = os.getenv('SECRET_KEY')

# Spotify API credentials from environment variables
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Spotify redirect URI after successful authorization
REDIRECT_URI = 'https://nameless-ocean-47665-871e4574a92b.herokuapp.com/callback'

# Spotify endpoints
AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'


# Function to handle rate limits from Spotify's API
def handle_rate_limit(response):
    """Handle Spotify rate limit errors by waiting the specified time."""
    if response.status_code == 429:  # 429 is the rate limit error code
        retry_after = int(response.headers.get('Retry-After', 1))
        print(f"Rate limited by Spotify. Retrying after {retry_after} seconds.")
        time.sleep(retry_after)
        return True
    return False


# Function to make requests to Spotify's API, with automatic handling of rate limits
def make_request_with_rate_limit(url, headers, params=None, method="GET", json_data=None):
    """Make a request to the Spotify API, handling rate limits and retries."""
    while True:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, json=json_data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=json_data)

        if handle_rate_limit(response):
            continue
        return response


# Function to fetch all favorited albums of the user
def fetch_all_favorited_albums(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    albums_url = 'https://api.spotify.com/v1/me/albums'
    all_albums = []
    offset = 0

    while True:
        response = make_request_with_rate_limit(albums_url, headers, params={'limit': 50, 'offset': offset})
        response_json = response.json()

        if 'items' not in response_json or len(response_json['items']) == 0:
            break

        all_albums.extend(response_json['items'])
        offset += 50
    
    print(f"Total favorited albums found: {len(all_albums)}")
    return all_albums


# Function to fetch all tracks from a given album
def fetch_all_tracks_from_album(album_id, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    album_tracks_url = f'https://api.spotify.com/v1/albums/{album_id}/tracks'
    all_tracks = []
    offset = 0

    while True:
        response = make_request_with_rate_limit(album_tracks_url, headers, params={'limit': 50, 'offset': offset})
        response_json = response.json()

        if 'items' not in response_json:
            break

        all_tracks.extend(response_json['items'])

        if len(response_json['items']) < 50:
            break

        offset += 50

    print(f"Fetched {len(all_tracks)} tracks from album {album_id}")
    return [track['uri'] for track in all_tracks if 'uri' in track]


# Function to check if tracks are already liked by the user
def check_liked_songs(track_uris, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    track_ids = [uri.split(':')[-1] for uri in track_uris]
    liked_tracks_url = 'https://api.spotify.com/v1/me/tracks/contains'
    liked_status = []
    batch_size = 50

    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i:i + batch_size]
        response = make_request_with_rate_limit(liked_tracks_url, headers, params={'ids': ','.join(batch)})
        if response.status_code != 200:
            print(f"Failed to check liked songs for batch {i // batch_size + 1}")
            return []
        liked_status.extend(response.json())

    return liked_status


# Function to move all old liked songs to a new playlist
def move_old_liked_songs(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    playlists_url = 'https://api.spotify.com/v1/me/playlists'
    response = make_request_with_rate_limit(playlists_url, headers)
    for playlist in response.json()['items']:
        if playlist['name'] == 'Old Liked Songs':
            return

    liked_songs_url = 'https://api.spotify.com/v1/me/tracks'
    liked_songs = []
    offset = 0

    while True:
        response = make_request_with_rate_limit(liked_songs_url, headers, params={'limit': 50, 'offset': offset})
        response_json = response.json()
        if not response_json['items']:
            break
        liked_songs.extend([item['track']['uri'] for item in response_json['items']])
        offset += 50

    if not liked_songs:
        return

    user_profile_url = 'https://api.spotify.com/v1/me'
    user_profile = make_request_with_rate_limit(user_profile_url, headers).json()
    create_playlist_url = f"https://api.spotify.com/v1/users/{user_profile['id']}/playlists"
    payload = {"name": "Old Liked Songs", "description": "All your old liked songs", "public": False}
    create_response = make_request_with_rate_limit(create_playlist_url, headers, method="POST", json_data=payload)
    old_playlist_id = create_response.json()['id']

    add_tracks_url = f"https://api.spotify.com/v1/playlists/{old_playlist_id}/tracks"
    for i in range(0, len(liked_songs), 100):
        batch = liked_songs[i:i + 100]
        make_request_with_rate_limit(add_tracks_url, headers, method="POST", json_data={'uris': batch})

    remove_tracks_url = 'https://api.spotify.com/v1/me/tracks'
    for i in range(0, len(liked_songs), 50):
        batch = liked_songs[i:i + 50]
        make_request_with_rate_limit(remove_tracks_url, headers, method="DELETE", json_data={'ids': [uri.split(':')[-1] for uri in batch]})


# Function to add tracks to liked songs
def add_tracks_to_liked_songs(track_uris, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    add_songs_url = 'https://api.spotify.com/v1/me/tracks'
    for i in range(0, len(track_uris), 50):
        batch = track_uris[i:i + 50]
        batch_ids = [uri.split(':')[-1] for uri in batch]
        response = make_request_with_rate_limit(add_songs_url, headers, method="PUT", json_data={'ids': batch_ids})
        if response.status_code != 200:
            print(f"Failed to add tracks: {response.status_code}")
        else:
            print(f"Added {len(batch)} tracks to liked songs.")


# Route to initiate the Spotify login flow
@app.route('/login')
def login():
    scope = 'user-library-modify user-library-read playlist-modify-public playlist-modify-private'
    auth_url = f"{AUTH_URL}?client_id={SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={scope}"
    return redirect(auth_url)


# Route to handle Spotify's callback after the user logs in
@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET
    }
    token_response = requests.post(TOKEN_URL, data=token_data).json()
    if 'access_token' not in token_response:
        return jsonify({'error': 'Failed to get access token'}), 400

    access_token = token_response['access_token']
    session['access_token'] = access_token
    return redirect(f'https://solanh.github.io/spotify/success.html?access_token={access_token}')


# Route to handle adding songs to user's liked songs
@app.route('/add_songs', methods=['GET'])
def add_songs():
    access_token = request.args.get('access_token')
    if not access_token:
        return jsonify({'error': 'Access token not provided'}), 401

    move_old_liked_songs(access_token)

    session['processed_albums'] = 0
    session['total_albums'] = 0
    session['total_tracks_added'] = 0

    favorited_albums = fetch_all_favorited_albums(access_token)
    if not favorited_albums:
        return jsonify({'error': 'No favorited albums found'}), 400

    session['total_albums'] = len(favorited_albums)

    for album in favorited_albums:
        album_id = album['album']['id']
        album_tracks = fetch_all_tracks_from_album(album_id, access_token)

        if album_tracks:
            liked_status = check_liked_songs(album_tracks, access_token)
            tracks_to_add = [uri for uri, liked in zip(album_tracks, liked_status) if not liked]

            if tracks_to_add:
                add_tracks_to_liked_songs(tracks_to_add, access_token)

        session['processed_albums'] += 1

    return jsonify({
        'message': 'Song adding task started.',
        'total_albums': session['total_albums'],
        'processed_albums': session['processed_albums']
    }), 200


# Route to check the status of the song-adding process
@app.route('/task_status', methods=['GET'])
def task_status():
    return jsonify({
        'total_albums': session.get('total_albums', 0),
        'processed_albums': session.get('processed_albums', 0),
        'total_tracks_added': session.get('total_tracks_added', 0),
        'status': 'completed' if session.get('processed_albums', 0) == session.get('total_albums', 0) else 'in_progress'
    }), 200


# Run the app when executing the script
if __name__ == '__main__':
    app.run(debug=True)
