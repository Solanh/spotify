import os
from flask import Flask, redirect, request, session, url_for
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

import logging



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
    scope="user-library-read playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private user-read-playback-state"

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



def create_playlist(name):
    #Create a new playlist for the user."""
    

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=get_valid_token())    
    user = sp.current_user()
 

    # Create a playlist
    try:
        print("hello")
        playlist = sp.user_playlist_create(
            user=user['id'], name=name, public=False
        )
        print("hello2")
        return playlist['id']
    except Exception as e:
        return f"Error creating playlist: {str(e)}", 400

def get_valid_token():
    """
    Retrieves a valid access token from the session.
    Refreshes the token if it has expired.
    Raises an exception if no valid token is available.
    """
    token_info = session.get('token_info', None)
    if not token_info:
        raise ValueError("No token found in session. User must log in.")

    try:
        if sp_oauth.is_token_expired(token_info):
            token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
            session['token_info'] = token_info
        return token_info['access_token']
    except Exception as e:
        # Log the error and clear token info if needed
        logging.error(f"Token refresh error: {str(e)}")
        session.pop('token_info', None)
        raise ValueError("Error refreshing token. Please log in again.")




def get_album_songs(album_ids):
    

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=get_valid_token())
    
    album_songs = []
    print(f"Fetching tracks for {len(album_ids)} albums...")

    for album_id in album_ids:
        # Fetch tracks from the album
        tracks = sp.album_tracks(album_id=album_id)

        # Extract track IDs and append them
        album_songs.extend([track['id'] for track in tracks['items']])
    
    print(f"Found {len(album_songs)} songs.")
    return album_songs
    

def check_liked_songs():
    """
    Fetch all liked songs for the current user.
    Returns a list of dictionaries with album names and track IDs.
    """
    sp = spotipy.Spotify(auth=get_valid_token())

    liked_songs = []
    limit = 50  # Maximum allowed by Spotify API
    offset = 0

    try:
        while True:
            results = sp.current_user_saved_tracks(limit=limit, offset=offset)

            if not results or not results.get("items"):
                break  # Exit loop when no more liked songs are found

            # Extract track data efficiently
            new_tracks = [
                item["track"]["id"] for item in results["items"]
            ]
            liked_songs.extend(new_tracks)

            offset += limit  # Move to the next batch
            print(f"Retrieved {len(liked_songs)} liked songs so far...")

            # Stop if there are no more pages to fetch
            if not results.get("next"):
                break

        return liked_songs

    except Exception as e:
        logging.error(f"Error retrieving liked songs: {str(e)}")
        return {"error": f"Error retrieving liked songs: {str(e)}"}, 400


    
def get_album_ids():  
    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=get_valid_token())
    
    album_ids = []
    results = sp.current_user_saved_albums()
    
    
        
    while results:
        album_ids.extend([item["album"]["id"] for item in results["items"]])  # Store raw IDs
        print(f"Found {len(album_ids)} IDs")
        
        if results["next"]:
            results = sp.next(results)  # Fetch next page
        else:
            break  # Exit loop properly
    
        
    return album_ids


def clear_playlist(playlist_id):
    sp = spotipy.Spotify(auth=get_valid_token())
    
    tracks = []
    results = sp.playlist_tracks(playlist_id)

    # Collect all track URIs
    while results:
        tracks.extend([{"uri": item["track"]["uri"]} for item in results["items"]])
        results = sp.next(results) if results["next"] else None

    # Remove in batches of 100
    for i in range(0, len(tracks), 100):
        sp.playlist_remove_all_occurrences_of_items(playlist_id, [t["uri"] for t in tracks[i:i+100]])
        print(f"Removed {i+100 if i+100 < len(tracks) else len(tracks)} tracks...")

    print("Playlist cleared successfully!")

def check_playlist_songs():
    sp = spotipy.Spotify(auth=get_valid_token())
    
    playlist_songs = []
    
    
    try:
        count = 0
        print("zero")
        playlist_songs_num = sp.playlist_tracks(playlist_id='6wLXeAJtOgDGDkW3vNpsKF', limit=1)['total']
        print(playlist_songs_num)
        print("one")
        for i in playlist_songs['items']:
            count += 1
            print("hello")
            playlist_songs.append(i['track']['id'])
            if count % 100 == 0:
                print(f"Found {count} songs")
            
        return playlist_songs
    except Exception as e:
        return f"Error checking playlist songs: {str(e)}", 400

def add_songs_to_playlist(track_ids, playlist_id):
    sp = spotipy.Spotify(auth=get_valid_token())

    
    
    batch_size = 100
    for i in range(0, len(track_ids), batch_size):
        sp.playlist_add_items(playlist_id=playlist_id, items=track_ids[i:i + batch_size])
        
        
    return "Songs added to playlist"

    
    
    

def get_playlist_id(name):
    
    sp = spotipy.Spotify(auth=get_valid_token())
    print("1")
    
    try:
        print("3")
        playlists = sp.current_user_playlists()
        print("2")
        for playlist in playlists['items']:
            if playlist['name'] == name:
                return playlist['id']
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error retrieving playlist ID: {str(e)}", 400

@app.route('/main', methods=['GET'])
def main():
    logging.debug(f"Received request at /main from {request.remote_addr}")  # Log each request

    create_new_playlist = False
    album_songs_to_playlist = False
    clear_existing_playlist = False
    get_album_id = False
    transfer_liked_songs = True

    sp = spotipy.Spotify(auth=get_valid_token())

    try:
        if get_album_id:
            album_ids = get_album_ids()
            return f"Main actions executed successfully! Found {len(album_ids)} albums.<br>"
        elif album_songs_to_playlist and create_new_playlist:
            album_ids = get_album_ids()
           
            album_songs = get_album_songs(album_ids)
        
            playlist_id = create_playlist("Album Songss")
      
            add_songs_to_playlist(album_songs, playlist_id)
            return "Songs added!"
        elif clear_existing_playlist:
            playlist_id = get_playlist_id("Album Songss")
         
            clear_playlist(playlist_id)
            return "Playlist cleared!"
        elif transfer_liked_songs:
            liked_songs = check_liked_songs()
           
            playlist_id = create_playlist("Album Songs")
            
            add_songs_to_playlist(liked_songs, playlist_id)
            return "Liked songs transferred!"
            

        return "Main actions executed successfully!"
    
    except Exception as e:
        logging.error(f"Error in /main: {str(e)}")
        return f"Error executing main actions: {str(e)}", 400
    
    


if __name__ == '__main__':
    app.run(debug=False)
    
