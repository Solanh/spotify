import time
import requests
from flask import Flask, redirect, request, session, jsonify
from dotenv import load_dotenv
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "https://solanh.github.io"}})
app.secret_key = os.getenv('SECRET_KEY')
load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = 'https://nameless-ocean-47665-871e4574a92b.herokuapp.com/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'

@app.route('/login')
def login():
    scope = 'user-library-modify user-library-read playlist-modify-public playlist-modify-private'
    auth_url = f"{AUTH_URL}?client_id={SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={scope}"
    return redirect(auth_url)

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
        return jsonify({'error': 'Failed to get access token', 'details': token_response}), 400

    access_token = token_response['access_token']
    
    # Store the access token in session for later use
    session['access_token'] = access_token
    
    # Redirect back to your front-end with the access token as a query parameter
    return redirect(f'https://solanh.github.io/spotify/success.html?access_token={access_token}')

def handle_rate_limit(response):
    """Handle Spotify rate limit errors by waiting the specified time."""
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 1))  # Get 'Retry-After' in seconds, default to 1 second if not found
        print(f"Rate limited by Spotify. Retrying after {retry_after} seconds.")
        time.sleep(retry_after)
        return True
    return False

def fetch_all_favorited_albums(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    albums_url = 'https://api.spotify.com/v1/me/albums'
    all_albums = []
    offset = 0

    # Fetch albums in paginated requests (50 albums per request)
    while True:
        response = requests.get(albums_url, headers=headers, params={'limit': 50, 'offset': offset})
        
        if handle_rate_limit(response):
            continue

        response_json = response.json()
        if 'items' not in response_json or len(response_json['items']) == 0:
            break
        all_albums.extend(response_json['items'])
        offset += 50
    
    print(f"Total favorited albums found: {len(all_albums)}")
    return all_albums

def fetch_all_tracks_from_album(album_id, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    album_tracks_url = f'https://api.spotify.com/v1/albums/{album_id}/tracks'
    all_tracks = []
    offset = 0

    # Fetch tracks in paginated requests (50 tracks per request)
    while True:
        response = requests.get(album_tracks_url, headers=headers, params={'limit': 50, 'offset': offset})
        
        if handle_rate_limit(response):
            continue

        response_json = response.json()
        if 'items' not in response_json or len(response_json['items']) == 0:
            break
        all_tracks.extend(response_json['items'])
        offset += 50

    print(f"Tracks fetched from album {album_id}: {len(all_tracks)}")
    return [track['uri'] for track in all_tracks]

def move_old_liked_songs(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Check if the "Old Liked Songs" playlist exists
    playlists_url = 'https://api.spotify.com/v1/me/playlists'
    response = requests.get(playlists_url, headers=headers)
    
    if handle_rate_limit(response):
        return jsonify({'message': 'Rate limited while fetching playlists. Try again later.'}), 429

    for playlist in response.json()['items']:
        if playlist['name'] == 'Old Liked Songs':
            print("Old Liked Songs playlist already exists. Skipping creation.")
            return

    # Get all current liked songs
    liked_songs_url = 'https://api.spotify.com/v1/me/tracks'
    liked_songs = []
    offset = 0

    while True:
        response = requests.get(liked_songs_url, headers=headers, params={'limit': 50, 'offset': offset})
        
        if handle_rate_limit(response):
            continue

        if not response.json()['items']:
            break
        liked_songs.extend([item['track']['uri'] for item in response.json()['items']])
        offset += 50

    if not liked_songs:
        print("No liked songs found to move.")
        return

    # Create a new playlist called "Old Liked Songs"
    user_profile_url = 'https://api.spotify.com/v1/me'
    user_profile = requests.get(user_profile_url, headers=headers).json()
    create_playlist_url = f"https://api.spotify.com/v1/users/{user_profile['id']}/playlists"
    payload = {
        "name": "Old Liked Songs",
        "description": "All your old liked songs moved from Liked Songs",
        "public": False
    }
    create_response = requests.post(create_playlist_url, headers=headers, json=payload)
    
    if handle_rate_limit(create_response):
        return jsonify({'message': 'Rate limited while creating playlist. Try again later.'}), 429
    
    old_playlist_id = create_response.json()['id']
    print(f"Created new playlist 'Old Liked Songs'.")

    # Add the liked songs to the new playlist
    add_tracks_url = f"https://api.spotify.com/v1/playlists/{old_playlist_id}/tracks"
    for i in range(0, len(liked_songs), 100):
        batch = liked_songs[i:i + 100]
        response = requests.post(add_tracks_url, headers=headers, json={'uris': batch})
        
        if handle_rate_limit(response):
            continue

    # Remove the old liked songs from the user's liked songs
    remove_tracks_url = 'https://api.spotify.com/v1/me/tracks'
    for i in range(0, len(liked_songs), 50):
        batch = liked_songs[i:i + 50]
        response = requests.delete(remove_tracks_url, headers=headers, json={'ids': [uri.split(':')[-1] for uri in batch]})
        
        if handle_rate_limit(response):
            continue

    print(f"Moved {len(liked_songs)} songs to 'Old Liked Songs' and removed from Liked Songs.")

@app.route('/add_songs', methods=['GET'])
def add_songs():
    access_token = request.args.get('access_token')

    if not access_token:
        return jsonify({'error': 'Access token not provided in request'}), 401

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Check if the access token is valid
    token_info_url = 'https://api.spotify.com/v1/me'
    token_check = requests.get(token_info_url, headers=headers)

    if token_check.status_code != 200:
        return jsonify({
            'error': 'Invalid access token or permissions',
            'status_code': token_check.status_code,
            'details': token_check.json()
        }), 401

    # Move old liked songs to a new playlist
    move_old_liked_songs(access_token)

    # Fetch all favorited albums
    favorited_albums = fetch_all_favorited_albums(access_token)

    if not favorited_albums:
        return jsonify({'error': 'No favorited albums found'}), 400

    # Fetch tracks from each favorited album
    all_track_uris = []
    for album in favorited_albums:
        album_id = album['album']['id']
        album_tracks = fetch_all_tracks_from_album(album_id, access_token)
        all_track_uris.extend(album_tracks)

    if not all_track_uris:
        return jsonify({'error': 'No tracks found in favorited albums'}), 400

    print(f"Total tracks found to add: {len(all_track_uris)}")

    # Add songs to liked songs in batches of 50
    add_songs_url = 'https://api.spotify.com/v1/me/tracks'
    for i in range(0, len(all_track_uris), 50):
        batch = all_track_uris[i:i + 50]
        response = requests.put(add_songs_url, headers=headers, json={'ids': [uri.split(':')[-1] for uri in batch]})
        
        if handle_rate_limit(response):
            continue

        if response.status_code != 200:
            print(f"Failed to add songs in batch {i//50 + 1}: {response.json()}")

    return jsonify({'message': f'Added {len(all_track_uris)} tracks to Liked Songs.'})

if __name__ == '__main__':
    app.run(debug=True)
