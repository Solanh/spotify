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
def create_playlist(playlist_name):
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
        
        playlist = sp.user_playlist_create(
            user=user['id'], name=playlist_name, public=True
        )
        return f"Playlist created: {playlist['name']} (ID: {playlist['id']})"
    except Exception as e:
        return f"Error creating playlist: {str(e)}", 400

def get_valid_token():
    
    # Get token info from the session
    token_info = session.get('token_info', None)

    # If no token info is available, return None
    if not token_info:
        return None

    # Refresh the token if it has expired
    if sp_oauth.is_token_expired(token_info):
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        session['token_info'] = token_info

    return token_info['access_token']

@app.route('/get_album_ids', methods=['GET'])
def get_album_ids():
    
    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=get_valid_token())
    
    album_ids = []
    
    try:
        offset = 0
        limit = 10
        
        while True:
            saved_albums = sp.current_user_saved_albums(limit=limit, offset=offset)
            if not saved_albums['items']:
                print("No more albums found")
                break  # Exit loop if no more albums

            for item in saved_albums['items']:
                id = item['album']
                
                album_ids.append(id['id'])
                
                
                
                #album_songs.append({'album': track['album']['name'], 'track': track['name']})
                    
            offset += limit  # Move to the next page
                    
            print(f"Found {len(album_ids)} id's")
        print(album_ids)
        return album_ids
        
        
    except Exception as e:
        return [f"Error retriving songs: {str(e)}", 400]
    
    
@app.route('/get_album_songs', methods=['GET'])
def get_album_songs():
    

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=get_valid_token())
    
    album_songs = []
    
    try:
        
        
        album_ids = ['5Bz2LxOp0wz7ov0T9WiRmc', '4wExFfncaUIqSgoxnqa3Eh', '55U9LPwlaFmsgOsLyJnrmu', '16VzTNaeadMjxI03Xi9s6n', '5g3Yi15plTSMaq6tYiuw8p', '5AkhPWlUvpvRoiFbL1H47v', '2YiFk7TmwtTAMMcvmIDbsD', '5tdmyKWNxDlCvYCdJQKGoS', '6Q7Ve532tafGJI4UWcSa5R', '4Gwf27nBqKVqEf1JwlxEBS', '0ihF0MZvYC8sj6XCoAV5gv', '1lbiE132cerWgRG2T4NBWB', '69lL1q3dNv0UxigLsQHLwm',"3esB4Gl0K2LKCgACUJa3mu","5zuQQIzkoyry8lZrmW4744","5sHvTCk793vr9EkSKcD7IT","7J84ixPVFehy6FcLk8rhk3"]
        
        print("hello")
        
        
        for i in album_ids:
            tracks = sp.album_tracks(album_id=i)
            
            for track in tracks['items']:
                album_songs.append(track)
            print("loading...")
        
                        
        print(f"Found {len(album_songs)} songs")
        return album_songs
            
        
        
        
    except Exception as e:
        return [f"Error retriving songs: {str(e)}", 400]
    
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
      
        

        # Return a combined result
        return (
            f"Main actions executed successfully!<br>"
            
            
        )
    except Exception as e:
        return f"Error executing main actions: {str(e)}", 400
    
    


if __name__ == '__main__':
    app.run(debug=False)
    
