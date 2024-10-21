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

# Route to initiate the Spotify login flow
@app.route('/login')
def login():
    # Define the required scopes (permissions) for the Spotify API
    scope = 'user-library-modify user-library-read playlist-modify-public playlist-modify-private'

    # Build the authorization URL to redirect the user to Spotify's login page
    auth_url = f"{AUTH_URL}?client_id={SPOTIFY_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={scope}"

    # Redirect the user to Spotify login
    return redirect(auth_url)

# Route to handle Spotify's callback after the user logs in
@app.route('/callback')
def callback():
    # Get the authorization code from Spotify's callback
    code = request.args.get('code')

    # Prepare data for requesting an access token using the authorization code
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET
    }
    print(f"Access token retrieved: {session.get('access_token')}")

    # Exchange the authorization code for an access token
    token_response = requests.post(TOKEN_URL, data=token_data).json()

    # Check if an access token was successfully retrieved
    if 'access_token' not in token_response:
        return jsonify({'error': 'Failed to get access token', 'details': token_response}), 400

    # Store the access token in the session for later use
    access_token = token_response['access_token']
    session['access_token'] = access_token

    # Redirect back to the frontend with the access token as a query parameter
    return redirect(f'https://solanh.github.io/spotify/success.html?access_token={access_token}')

# Function to handle rate limits from Spotify's API
def handle_rate_limit(response):
    """Handle Spotify rate limit errors by waiting the specified time."""
    if response.status_code == 429:  # 429 is the rate limit error code
        # Get the retry-after time from the response headers (default to 1 second if not found)
        retry_after = int(response.headers.get('Retry-After', 1))
        print(f"Rate limited by Spotify. Retrying after {retry_after} seconds.")
        time.sleep(retry_after)  # Wait for the specified time
        return True  # Indicate that the request should be retried
    return False  # No rate limit encountered

# Function to make requests to Spotify's API, with automatic handling of rate limits
def make_request_with_rate_limit(url, headers, params=None, method="GET", json_data=None):
    """Make a request to the Spotify API, handling rate limits and retries."""
    while True:
        # Determine the request method (GET, POST, DELETE, PUT) and send the request
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, json=json_data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=json_data)

        # If a rate limit is hit, wait and retry
        if handle_rate_limit(response):
            continue
        return response  # Return the response once successful

# Function to fetch all favorited albums of the user
def fetch_all_favorited_albums(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    albums_url = 'https://api.spotify.com/v1/me/albums'
    all_albums = []  # List to store all fetched albums
    offset = 0  # Used for pagination (Spotify limits 50 albums per request)

    # Fetch albums in paginated requests (limit 50 per request)
    while True:
        response = make_request_with_rate_limit(albums_url, headers, params={'limit': 50, 'offset': offset})
        response_json = response.json()

        # Stop fetching if no more albums are found
        if 'items' not in response_json or len(response_json['items']) == 0:
            break

        # Add the fetched albums to the list
        all_albums.extend(response_json['items'])
        offset += 50  # Move to the next set of albums for pagination
    
    print(f"Total favorited albums found: {len(all_albums)}")
    return all_albums

# Function to fetch all tracks from a given album
def fetch_all_tracks_from_album(album_id, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    album_tracks_url = f'https://api.spotify.com/v1/albums/{album_id}/tracks'
    all_tracks = []  # List to store all tracks
    offset = 0  # Used for pagination (Spotify limits 50 tracks per request)

    # Fetch tracks in paginated requests (limit 50 per request)
    while True:
        try:
            response = make_request_with_rate_limit(album_tracks_url, headers, params={'limit': 50, 'offset': offset})
            response_json = response.json()

            # Log the response for debugging
            print(f"Response JSON for album {album_id}: {response_json}")

            # Stop fetching if no more tracks are found or response is not as expected
            if 'items' not in response_json:
                print(f"Unexpected response format or no items found for album {album_id}.")
                break

            # Add the fetched tracks to the list
            all_tracks.extend(response_json['items'])

            # If less than 50 tracks were returned, it means we're at the end
            if len(response_json['items']) < 50:
                break

            # Move to the next set of tracks for pagination
            offset += 50

        except Exception as e:
            print(f"Error fetching tracks for album {album_id}: {str(e)}")
            break

    print(f"Total tracks fetched from album {album_id}: {len(all_tracks)}")

    # Safely return URIs, ensuring only valid tracks with 'uri' are processed
    return [track['uri'] for track in all_tracks if 'uri' in track]  # Return the URIs of the tracks


# Function to move all old liked songs to a new playlist
def move_old_liked_songs(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # Check if the "Old Liked Songs" playlist already exists
    playlists_url = 'https://api.spotify.com/v1/me/playlists'
    response = make_request_with_rate_limit(playlists_url, headers)
    for playlist in response.json()['items']:
        if playlist['name'] == 'Old Liked Songs':
            print("Old Liked Songs playlist already exists. Skipping creation.")
            return

    # Get all currently liked songs
    liked_songs_url = 'https://api.spotify.com/v1/me/tracks'
    liked_songs = []  # List to store liked songs
    offset = 0

    # Fetch liked songs in paginated requests (limit 50 per request)
    while True:
        response = make_request_with_rate_limit(liked_songs_url, headers, params={'limit': 50, 'offset': offset})
        response_json = response.json()

        # Stop fetching if no more liked songs are found
        if not response_json['items']:
            break

        # Add the fetched liked songs to the list
        liked_songs.extend([item['track']['uri'] for item in response_json['items']])
        offset += 50

    if not liked_songs:
        print("No liked songs found to move.")
        return

    # Create a new playlist for old liked songs
    user_profile_url = 'https://api.spotify.com/v1/me'
    user_profile = make_request_with_rate_limit(user_profile_url, headers).json()
    create_playlist_url = f"https://api.spotify.com/v1/users/{user_profile['id']}/playlists"
    payload = {
        "name": "Old Liked Songs",
        "description": "All your old liked songs moved from Liked Songs",
        "public": False
    }
    create_response = make_request_with_rate_limit(create_playlist_url, headers, method="POST", json_data=payload)
    old_playlist_id = create_response.json()['id']
    print(f"Created new playlist 'Old Liked Songs'.")

    # Add the liked songs to the new playlist in batches of 100
    add_tracks_url = f"https://api.spotify.com/v1/playlists/{old_playlist_id}/tracks"
    for i in range(0, len(liked_songs), 100):
        batch = liked_songs[i:i + 100]
        make_request_with_rate_limit(add_tracks_url, headers, method="POST", json_data={'uris': batch})

    # Remove the old liked songs from the user's liked songs in batches of 50
    remove_tracks_url = 'https://api.spotify.com/v1/me/tracks'
    for i in range(0, len(liked_songs), 50):
        batch = liked_songs[i:i + 50]
        make_request_with_rate_limit(remove_tracks_url, headers, method="DELETE", json_data={'ids': [uri.split(':')[-1] for uri in batch]})

    print(f"Moved {len(liked_songs)} songs to 'Old Liked Songs' and removed from Liked Songs.")



# Route to handle adding songs to user's liked songs
# Function to check if tracks are already liked by the user
# Function to check if tracks are already liked by the user
def check_liked_songs(track_uris, access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    track_ids = [uri.split(':')[-1] for uri in track_uris]  # Extract track IDs
    print(f"Checking liked status for track IDs: {track_ids}")

    liked_tracks_url = 'https://api.spotify.com/v1/me/tracks/contains'

    liked_status = []
    total_tracks = len(track_ids)  # Total number of tracks to check
    batch_size = 10  # Spotify API limit for 'contains' endpoint
    for i in range(0, total_tracks, batch_size):  # Process in batches of 50
        batch = track_ids[i:i + batch_size]  # Current batch of track IDs
        response = make_request_with_rate_limit(liked_tracks_url, headers, params={'ids': ','.join(batch)})
        
        # Check if the response is valid
        if response.status_code != 200:
            print(f"Failed to check liked songs in batch {i // batch_size + 1}: {response.json()}")
            return []  # Exit if something goes wrong

        print(f"Response for batch {i // batch_size + 1}: {response.json()}")

        liked_status.extend(response.json())  # Add the liked statuses to the list

    print(f"Final liked status: {liked_status}")
    return liked_status


@app.route('/add_songs', methods=['GET'])
def add_songs():
    access_token = request.args.get('access_token')
    offset = 0  # Start from offset 0 and process continuously

    if not access_token:
        return jsonify({'error': 'Access token not provided in request'}), 401

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    move_old_liked_songs(access_token)  # Move old liked songs to a new playlist
    
    # Check if access token is valid by hitting the /me endpoint
    token_info_url = 'https://api.spotify.com/v1/me'
    token_check = make_request_with_rate_limit(token_info_url, headers)

    if token_check.status_code != 200:
        return jsonify({
            'error': 'Invalid access token or permissions',
            'status_code': token_check.status_code,
            'details': token_check.json()
        }), 401

    # Fetch all favorited albums
    favorited_albums = fetch_all_favorited_albums(access_token)
    if not favorited_albums:
        return jsonify({'error': 'No favorited albums found'}), 400

    processed_albums = set()  # Keep track of processed albums
    total_tracks = 0
    
    
    
    while offset < len(favorited_albums):
        album = favorited_albums[offset]
        
        album_id = album['album']['id']
        
        # Some API calls might return albums in different structures
        if 'album' not in album or 'id' not in album['album']:
            offset += 1
            continue
        
        if album_id in processed_albums:
            offset += 1
            continue

        # Mark album as processed
        processed_albums.add(album_id)

        # Fetch all tracks from the album
        album_tracks = fetch_all_tracks_from_album(album_id, access_token)

        if not isinstance(album_tracks, list):
            offset += 1
            continue  # Skip if tracks could not be fetched correctly

        # Extract URIs of tracks that are not already liked
        track_uris = [track['uri'] for track in album_tracks if 'uri' in track]
        track_names = [track['name'] for track in album_tracks if 'name' in track]

        if not track_uris:
            offset += 1
            continue  # Skip if no valid track URIs were found
        
        liked_status = check_liked_songs(track_uris, access_token)
        
        tracks_to_add = [uri for uri, liked in zip(track_uris, liked_status) if not liked]

        if tracks_to_add:
            add_songs_url = 'https://api.spotify.com/v1/me/tracks'

            # Add songs in batches of 50 (Spotify's batch limit)
            for i in range(0, len(tracks_to_add), 50):
                batch = tracks_to_add[i:i + 50]
                batch_ids = [uri.split(':')[-1] for uri in batch]

                # Make the request to add the tracks
                response = make_request_with_rate_limit(add_songs_url, headers, method="PUT", json_data={'ids': batch_ids})

                if response.status_code != 200:
                    print(f"Failed to add batch {i // 50 + 1}: {response.status_code}")
                else:
                    total_tracks += len(batch)
                    print(f"Added {len(batch)} tracks to 'Liked Songs'. Batch {i // 50 + 1}.")

        # Move to the next album
        offset += 1

    return jsonify({
        'message': 'All albums processed and tracks added successfully.',
        'total_tracks_added': total_tracks
    }), 200

# Run the app when executing the script
if __name__ == '__main__':
    app.run(debug=True)
