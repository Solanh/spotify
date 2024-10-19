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

def create_old_liked_songs_playlist(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Check if the "Old Liked Songs" playlist exists
    playlists_url = 'https://api.spotify.com/v1/me/playlists'
    response = requests.get(playlists_url, headers=headers).json()

    for playlist in response['items']:
        if playlist['name'] == 'Old Liked Songs':
            print("Old Liked Songs playlist already exists. Skipping playlist creation.")
            return playlist['id']  # Return the playlist ID if it already exists

    # Create the playlist if it doesn't exist
    user_profile_url = 'https://api.spotify.com/v1/me'
    user_profile = requests.get(user_profile_url, headers=headers).json()

    create_playlist_url = f"https://api.spotify.com/v1/users/{user_profile['id']}/playlists"
    payload = {
        "name": "Old Liked Songs",
        "description": "All your old liked songs moved from Liked Songs",
        "public": False  # You can change this to True if you want the playlist to be public
    }
    create_response = requests.post(create_playlist_url, headers=headers, json=payload).json()

    print(f"Created new playlist 'Old Liked Songs'.")
    return create_response['id']  # Return the new playlist ID

def move_and_remove_old_liked_songs(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Get all the current liked songs
    liked_songs_url = 'https://api.spotify.com/v1/me/tracks'
    liked_songs = []
    offset = 0

    while True:
        response = requests.get(liked_songs_url, headers=headers, params={'limit': 50, 'offset': offset}).json()
        if not response['items']:
            break

        liked_songs.extend([item['track']['uri'] for item in response['items']])
        offset += 50

    if not liked_songs:
        print("No liked songs found to move.")
        return

    print(f"Found {len(liked_songs)} liked songs.")

    # Create or get the "Old Liked Songs" playlist
    old_playlist_id = create_old_liked_songs_playlist(access_token)

    # Add the liked songs to the new playlist
    add_tracks_url = f"https://api.spotify.com/v1/playlists/{old_playlist_id}/tracks"
    for i in range(0, len(liked_songs), 100):  # Add tracks in batches of 100
        batch = liked_songs[i:i + 100]
        add_response = requests.post(add_tracks_url, headers=headers, json={'uris': batch})
        if add_response.status_code != 201:
            print(f"Failed to add tracks to 'Old Liked Songs'. Response: {add_response.json()}")

    print("Moved all liked songs to 'Old Liked Songs'.")

    # Remove the liked songs from the user's liked songs
    remove_tracks_url = 'https://api.spotify.com/v1/me/tracks'
    for i in range(0, len(liked_songs), 50):  # Remove tracks in batches of 50
        batch = liked_songs[i:i + 50]
        remove_response = requests.delete(remove_tracks_url, headers=headers, json={'ids': [uri.split(':')[-1] for uri in batch]})
        if remove_response.status_code != 200:
            print(f"Failed to remove tracks from Liked Songs. Response: {remove_response.json()}")

    print("Removed old liked songs from 'Liked Songs'.")

@app.route('/add_songs', methods=['GET'])
def add_songs():
    # Use the access token from the request query parameters or headers
    access_token = request.args.get('access_token')

    if not access_token:
        return jsonify({'error': 'Access token not provided in request'}), 401

    print("Access token found, proceeding to add songs.")  # Debugging

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

    # Trigger the first-time move of old liked songs
    move_and_remove_old_liked_songs(access_token)

    # Continue with adding new songs to liked songs as per your original logic
    # Fetch favorited albums and process as in the original script...
    
    return jsonify({'message': 'Songs added to Liked Songs!'})

if __name__ == '__main__':
    app.run(debug=True)
