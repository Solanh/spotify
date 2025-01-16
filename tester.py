import os
from flask import Flask, redirect, request, session, url_for
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables
load_dotenv()

# Spotify credentials from .env
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URI')

# Validate environment variables
if not all([SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, REDIRECT_URI]):
    raise EnvironmentError("Missing Spotify credentials in .env file")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default_secret_key')

# Spotipy OAuth
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-library-read playlist-modify-public playlist-modify-private user-read-playback-state"
)


@app.route('/')
def index():
    """Redirect user to Spotify authorization URL."""
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route('/callback')
def callback():
    # Handle Spotify authorization callback.
    code = request.args.get('code')
    if not code:
        return "Authorization failed. Please try again.", 400

    # Exchange code for access token
    try:
        token_info = sp_oauth.get_access_token(code)
        session['token_info'] = token_info  # Store token in session
        return redirect(url_for('profile'))
    except Exception as e:
        return f"Error retrieving access token: {str(e)}", 400


@app.route('/profile')
def profile():
    """Fetch and display the user's Spotify profile."""
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('index'))  # Redirect to login if no token

    # Check and refresh token if needed
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user = sp.current_user()
    return f"Logged in as: {user['display_name']} (ID: {user['id']})"


@app.route('/create_playlist', methods=['GET'])
def create_playlist():
    #Create a new playlist for the user."""
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('index'))  # Redirect to login if no token

    # Check and refresh token if needed
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user = sp.current_user()

    # Create a playlist
    try:
        playlist_name = "Album songs"
        playlist = sp.user_playlist_create(
            user=user['id'], name=playlist_name, public=True
        )
        return f"Playlist created: {playlist['name']} (ID: {playlist['id']})"
    except Exception as e:
        return f"Error creating playlist: {str(e)}", 400

@app.route('/get_album_songs', methods = ['GET'])
def get_album_tracks():
    token_info = session.get('token_info', None)
    
    album_tracks = []
    
    if not token_info:
        print("oops1")
        return redirect(url_for('index'))  # Redirect to login if no token
        

    # Check and refresh token if needed
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info
        print("oops2")

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user = sp.current_user()
    
    try:
        print("oops3")
        offset = 0
        limit = 10

        while True:
            print("oops4")
            print(offset)
            saved_albums = sp.current_user_saved_albums(limit=limit, offset=offset)
            if not saved_albums['items']:
                print("No more albums found")
                break  # Exit loop if no more albums

            for item in saved_albums['items']:
                print("uh oh")
                album = item['album']
                print(f"Fetching tracks for album: {album['name']} (ID: {album['id']})")

                #print(album)
                tracks = sp.album_tracks(album['id'])
                print("hello")
                print(f"Tracks response: {tracks}")

                for track in tracks['items']:
                    print("uh oh again")
                    album_tracks.append({'album': album['name'], 'track': track['name']})
                    
            offset += limit  # Move to the next page
                    
            print(f"Fetched {len(album_tracks)} tracks")
            
        return album_tracks
        
    except Exception as e:
        return f"Error creating playlist: {str(e)}", 400
    
    
@app.route('/check_liked_songs', methods=['GET'])
def check_liked_songs():
    token_info = session.get('token_info', None)
    
    liked_songs_l = []
    
    if not token_info:
        return redirect(url_for('index'))  # Redirect to login if no token

    # Check and refresh token if needed
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    user = sp.current_user()
    
    try:
        offset = 0
        limit = 10
        
        while True:
            liked_songs = sp.current_user_saved_tracks(limit=limit, offset=offset)
            if not liked_songs['items']:
                print("No more albums found")
                break  # Exit loop if no more albums

            for item in liked_songs['items']:
                track = item['track']
                
                liked_songs_l.append({'album': track['album']['name'], 'track': track['name']})
                    
            offset += limit  # Move to the next page
                    
            print(f"Found {len(liked_songs_l)} tracks")
            
        return liked_songs_l
        
        
    except Exception as e:
        return f"Error retriving songs: {str(e)}", 400
    
        
@app.route('/main', methods=['GET'])
def main():
    token_info = session.get('token_info', None)
    if not token_info:
        return redirect(url_for('index'))  # Redirect to login if no token

    # Check and refresh token if needed
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=token_info['access_token'])

    try:
        # Call the functions and collect their results
        album_tracks_count = get_album_tracks()
        print(len(album_tracks_count))
        liked_songs_count = check_liked_songs()
        print(len(liked_songs_count))
        

        # Return a combined result
        return (
            f"Main actions executed successfully!<br>"
            f"Album tracks processed: {album_tracks_count}<br>"
            
        )
    except Exception as e:
        return f"Error executing main actions: {str(e)}", 400
    
    


if __name__ == '__main__':
    app.run()
    
