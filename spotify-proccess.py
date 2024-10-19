import requests
from flask import Flask, redirect, request, session, url_for, jsonify
from dotenv import load_dotenv
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This allows requests from any domain
app.secret_key = os.getenv('SECRET_KEY')
load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = 'https://nameless-ocean-47665-871e4574a92b.herokuapp.com/callback'

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'

@app.route('/login')
def login():
    scope = 'user-library-modify user-library-read'
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
    access_token = token_response['access_token']
    
    # Store the access token in session for later use
    session['access_token'] = access_token
    
    # Redirect back to your front-end with the access token as a query parameter
    return redirect(f'https://solanh.github.io/?access_token={access_token}')

@app.route('/add_songs')
def add_songs():
    access_token = session.get('access_token')
    if not access_token:
        return jsonify({'error': 'Access token not found in session'}), 401

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    # Fetch favorited albums
    albums_url = 'https://api.spotify.com/v1/me/albums'
    response = requests.get(albums_url, headers=headers).json()

    if 'items' not in response:
        return jsonify({'error': 'Failed to fetch albums', 'details': response}), 400

    track_uris = []

    # Get tracks from each album
    for item in response['items']:
        album_id = item['album']['id']
        album_tracks_url = f'https://api.spotify.com/v1/albums/{album_id}/tracks'
        tracks_response = requests.get(album_tracks_url, headers=headers).json()

        if 'items' not in tracks_response:
            return jsonify({'error': 'Failed to fetch tracks for album', 'album_id': album_id, 'details': tracks_response}), 400

        track_uris += [track['uri'] for track in tracks_response['items']]

    # Add songs to liked songs
    add_songs_url = 'https://api.spotify.com/v1/me/tracks'
    for i in range(0, len(track_uris), 50):  # Spotify allows adding up to 50 songs per request
        requests.put(add_songs_url, headers=headers, json={'ids': track_uris[i:i+50]})
    
    return "Songs added to Liked Songs!"
