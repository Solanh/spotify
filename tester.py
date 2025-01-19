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
    

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=get_valid_token())    
    user = sp.current_user()

    # Create a playlist
    try:
        
        playlist = sp.user_playlist_create(
            user=user['id'], name=playlist_name, public=False
        )
        return playlist['id']
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
def get_album_songs(album_ids):
    

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=get_valid_token())
    
    album_songs = []
    
    try:
        
        
        album_idss = ['5Bz2LxOp0wz7ov0T9WiRmc', '4wExFfncaUIqSgoxnqa3Eh', '55U9LPwlaFmsgOsLyJnrmu', '16VzTNaeadMjxI03Xi9s6n', '5g3Yi15plTSMaq6tYiuw8p', '5AkhPWlUvpvRoiFbL1H47v', '2YiFk7TmwtTAMMcvmIDbsD', '5tdmyKWNxDlCvYCdJQKGoS', '6Q7Ve532tafGJI4UWcSa5R', '4Gwf27nBqKVqEf1JwlxEBS', '0ihF0MZvYC8sj6XCoAV5gv', '1lbiE132cerWgRG2T4NBWB', '69lL1q3dNv0UxigLsQHLwm',"3esB4Gl0K2LKCgACUJa3mu","5zuQQIzkoyry8lZrmW4744","5sHvTCk793vr9EkSKcD7IT","7J84ixPVFehy6FcLk8rhk3"]
        
        print("hello")
        
        
        for i in album_ids:
            tracks = sp.album_tracks(album_id=i)
            
            for track in tracks['items']:
                album_songs.append(track['id'])
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
    
    
@app.route('/clear_songs_from_playlist', methods=['GET'])
def clear_songs_from_playlist():
    sp = spotipy.Spotify(auth=get_valid_token())
    
    try:
        playlist_id = '41Zy0SgcV5GVQ60rB4X4Tl'
        tracks = sp.playlist_tracks(playlist_id=playlist_id)
        track_ids = [track['track']['id'] for track in tracks['items']]
        
        for i in track_ids:
            sp.playlist_remove_all_occurrences_of_items(playlist_id=playlist_id, items=i)
            
            
        return "Songs removed from playlist"
    except Exception as e:
        return f"Error clearing songs from playlist: {str(e)}", 400
    
@app.route('/check_playlist_songs', methods=['GET'])
def check_playlist_songs():
    sp = spotipy.Spotify(auth=get_valid_token())
    
    playlist_songs = []
    
    try:
        playlist_songs = sp.playlist_tracks(playlist_id='41Zy0SgcV5GVQ60rB4X4Tl')
        for i in playlist_songs['items']:
            
            playlist_songs.append(i['track']['id'])
            
        return playlist_songs
    except Exception as e:
        return f"Error checking playlist songs: {str(e)}", 400

@app.route('/add_songs_to_playlist', methods=['GET'])
def add_songs_to_playlist(track_ids, playlist_id):
    sp = spotipy.Spotify(auth=get_valid_token())
    
    
    
    try:
        
        track_idss = ["0hy3f5LxZjH95QbuysY5OO","4lV1tx0EdlIChOw7Kz7fP0","4sJLWVtLug7LTsuFNqt82k","2e9sPx5xxJFyCecgNpq3Zb","07emIvmVExzrUNRraeC3JJ","6Mxqj3ClyindysAxYqqrrg","1VjyWxlrbNPF4ZtHZiw0Tp","6BSstu7y08lkJT5dNlEOkN","5bCxQhumlHXRjfyjOS2ib6","3tcaltthSz9s6awB6koVRo","6GXlXAfXR7C6u1VjR3VMsm","1RIsAtnYOlo8zGMycNFioq","0ducHx1R45CnEloZ6tUVuC","1uBMgVAUYLnzVL5uQT88FP","3Qjm0halGOZZGIS1tNaXlI","3I7a9joX0lJnK9XzE38GnD","2uuMXKKmdXrY2XxsqTsGp0","3Wunwn44wcWRNB4zb03AvA","7HQrFPtLEpgTJaEVujH8OO","3nsUVlntPIksDvhHdZZhiu","3BGwxsmbbOe2jmZfh5CUAO","12wlYeErSUNGg1B5d64077","6gQOsok1o9YY6vU1W5ZzWX","35XlkvHy9WHPI4Tf9eax4t","5iNr7y6iWNkwVvVeOXSLT5","55ZL7fjGAWfClmpnsK6Xon","6mkBbzyfK0EpywDk17taBg","5kxqPQ5Gasw1jXyBDCPDkN","5v2vkoTamoisazJFanHJjk","4KF1kzyeyPrgafyVm2UgQg","4wCMKxkE3eMOTtlAx0NFEM","7uBnSdqm07uMBrp7nBmMu9","5UdShl12E6eHEgS8lQ1bPr","2UBUvScBA21UPHoLSIEz3V","0VGmxQSqrFFEvZLC1HDGcr","7sYOXMXgA34jo9WkXZLEOG","4lVjHdUBgQhdwOfHStticK","6pS0PVQYaBYGkKPRxT5PEl","4z0YPAr8kcoHrJXhrJsFV3","4McullpiOd45TwEHlOISgs","70i1XQrudvwC4M4qKs9tpA","5dAoUZkkkmx0YDMK9Bmy2g","2ireIPn0SKV7BXXvZ3zdRa","0mE46SXrCohWNSk17AVfbP","6jutYLUIuEUYZnVHflVjUK","7LtSEY5R0vTmFmJxWpH0Kc","2pBobrYuBAVFKhvORvYFee","7Cao2G1t2BbYbSo6YjS4cx","3bntzrqfCdrTjJxRhbf7rs","1OpkNblM40C0Ol0fxldcm3","2nUyMD5cvEwiB6EuLFyCHo","7fyqFZSv5FKmPcx4LhmTPm","51PvMspXXFjLWUfePpeImt","3p9GbXMy1f9Efhdfj0QNBG","4F0GyDm11VAjqQmj7mRYPI","7F8Oirc8pVBeXQ9NFerUXs","43GalYZWoUi9cciYdv0Bej","2gQsVggoV49YeMdoYW03tJ","50M69sNDibJQfgDYNqFfH2","70B5oP5ng1QYClkJ9CeWly","2YGFDRqaOnejsnTkKe4VKE","7dhM0KUBxuZV9z5iNodLyn","2XVGfOXvRWy5QP2xPGXvZj","6KZaXNcnsHYWLT9b2Rdy6H","1EjQRTG53jsinzk2xlVVJP","0C6EIiQu8CS4eYtOCMEiAd","4pxzJlQsVjvjrtbTsey5vX","6BnyhvqA12zhsmcvoqwtz4","6u3hSyz0KAuZMyE4JtbQNp","1QpwjJmuow6GhUJGw6W74P","0IM5GMjsngXb6ub7BXkOnj","3TliaLRGyaZzrw3ffYaNBl","1mouSqtUHU3FtBmEODBqAn","4adskxvtdhBhsq3onGFWXQ","4ccbmgUx4GHmI2aG8BuYj8","5VBXdpi6QULy8N6WUBqnsS","6ZS9riQEtak8T0FitSjGc7","0xuVIKd6k2sLanHe9WcvNi","5C0WgwzC4jhUtAfziMaPxD","5ojPnZWtC3vBdxBKVhwFDn","1smRZTALo3Hwj3WkeQJe74","0kzfORnpKQE9qQeV0661Ue","0rcHIJUwAV7Ea9KxCj1atD","5TadOUh1LUMMfep93Fyy2L","7Eo8B4PQZqcklwHuHUgmBI","0Z4TBn1tde0ta3GAT8oUid","3qhprSKMkxBTvsBDO95ZHy","1yIWIPQ5hKJ7USdTdQIfpp","1ei3OFzWuOLMozHdsiNTou","7CbZjHN8wjfWRkUEXFiFGO","3ED4zmmCHDrFD5LKd8RaEK","0BeXtvkMm4tkAdXBBq9Slc","4Es8LLtaEX0qwRUoQ3vUKw","5gmQKRTzICBzlASai8hA2B","0ddItdjSTDsy0McT0fgug3","0o0qByHcXfGtmZmmkK7pcD","7r4xZTeYE78B1bbc9Gwwnk","01jcX2gEJYIWCxnsiOeYgD","6Xx77z1Z67f6bKXlj6z342","7sw5lEyG3Q2b1X19b7ulxG","2u4fnzW3mQ0FwXkZpsD2o8","4uBwHRHe1EhWwyCXCIljhH","1Pvc8QFH4oxCersJ7GaH8O","1SZO4SCfBSFhTGMlUpZB1O","1hDwBeBz3G5xVYftAjK2BQ","2KMLGJ1mPfRE4GNdL92rl3","1Ny6vWtIlFvPMFLZzUjrlB","6BTTmqavOi1KKpMBMRiYZ8","7euHyiqapZIQ08A4lerMOK","6eoXV1fjEBB9ussPSftEwA","5ifi01PWSK7Nx1FbIZ0jT8","0um7RSSiq1YiFkkYheLVuS","7gu99i0zbE2SIKzXkKW8ZA","4U6gIusvEnrkrSqJDQxCKA","52ifLFAEeFXYfQWMHe0X7y","6KZWM62G22AAOATjRKkHs9","4Q4OPuuuCJ4KHQ5EJvGLIz","0AYPWlZmdBqukG0OOp2Ine","2PPh5d93KFv70OUaUcqDtb","28eSkxyYbmE89HIeZTMnsC","4n3axXPWHMpFBMGZ4GMhgM","1iRG2KAY5bVz7HncTQF14h","3HHc8Vff5i1ogMlXHEoogb","2lL0L2vPfIZ9xdxpEJiQ3S","6Sorz09TdlUnyo2Ja4uNzb","4hD8Y7hZh8btoxflDyLugZ","3fcGcamR01XVSsV44qbNke","7LjkYjpf2uURgrZoCi5KOj","4UGOaZPk8uBm74Pc7hueQi","6pktnzWEkli12iDo6Y1jTz","3hyZYDPhYpZx3IfrrlCEiV","7JY0CTHiOogxhmJBrTBcp0","47cmrLpx1evFKWVsgdLqnX","1tJDnftYNFy9KgDfW0V3Pl","1xYKGXZF1R1AmIO9sayi1b","6BF1zkgQllvTwu5LSl27MU","4qqw1sObbcCIbkg00armxj","1lE1kfzgoTKpWYYADYrwIe","6sdaGuPCEW4kOtOelRxZjX","3Lp49Ke7d6pjz7XTVMXwzV","6qqsCLb53W6dzqijbzAUrn","7CbQNZFLfSk4g0IcjhZRXi","0UHN6K1BofQn0yciyilJGT","41yC7uY7DcptdwNx1afHtv","6XdxafgMPNj7sPtDQPijPo","63oM1GngVrACWQdFdaWeSE","6kDxBKwbpmfzxbF9j9kFSk","5AbLAP2HPoEsK99RXsNL1a","6t7PLCmMFrAXkf1UCwpQz7","43fnC9EwpHeyHNPXXAxq71","5pDx2xXt8Bxu1KawK5X2IH","77HfdYVU9F9RiRJSeKPKPJ","4ppMrMWZB3RPJwaFp2DNm3","6yznYy0ivwdpMVXQ9vbN0d","1XVwLqT5sFiwYxpNzq4RSB","6DabwaBU8Q0b5EG6YndySK","0vCsCgU9SgshVemF34OWwf","2Um6hfUdtXjYf5tHPBND6w","0AuKj2m1pbLk6JABCGmGkD","56IWAEGoeIhChibtncKOin","39TvIkd6vc7wPnGHCGIYmW","0K1SIWZFYeuteaFPn3sCPe","7LUOeqUkDBn5QEeSJZqOaq","2o1GalnDpsjABbU9fTEKQI","2X1EwEwZnwDiNcLk6hVI8W","5zZHskZUtCrvOTkPAECCiU","0SxD0MB6a7gvonrRUIqcwT","7oRNJJs5xn8elH8cb2Nhf4","6CvPC47gpqTznkWt6FY2RO","0kDVug5XXdD1mAOVz7P3El","0B4DXcYatKb19k25NT3p9S","4zULslnXBKMWVOJbvaUKWi","1vXZuXKnTyoDBAJOCtjJFq","0trTpNYmHAK3EihaZBd2h6","4T1168WOWj7Ch7DbbNEFp7","4Dp1NwpExFHNlSjO5jc7zx","3PuS7Y8gmF2mAOTbhJU9lg","5iJ27E0IOYs9eaFLFJwxR6","3vRYYiBghmEKMOnZcKj7MB","2Hxo0qwge0a4DS0Bj2J2hw","49q4JJ9PNjYoZFz2h6oLFY","1fjZGlwC7sBt3qx3fQjQfM","4Hxcdj7lXiOKY1SSBkrap5","2qQNgNregevtyWNX7OiUKI","739wZZ4Qqtm0pnzVHzeKxo","5zHzofWXEpq1KiYIqTv7s2","1ZCDInnCGU2rRTfEhrJaSS","2M7iasCe4t2UgOHVrVK6TM","1iwbnSrCMXUGXY6a6mjTTL","1SC86EEp5h0feV89TI5ECv","4flgLEXHoaXSQ2R8YZkSIe","0fe7AHSTWRryNOYCTci2LE","103XkIUGvwnefUIqDv5XNM","0lHSJ0ZP8uUPnJXhMdGjOK","0mmaX70fKuhgg0hDrfsS29","0lP4HYLmvowOKdsQ7CVkuq","7sMSEO2Xm4qa36nNq43JVE","4kRf54PG35X6wkYHqFUsbl","3UobpTI1cP54bPL1l3l2jP","1JBa9B1iA4yNVpJ5wVGrZH","6xKos15gJxZ9J3Q9qnSUU5","7BvLTfOGjYhxwbAA5CbMJ7","7hZRh76Rl1Tc99jZseanbZ","5XApNGBfWN8qXlhmPhErQb","6UScyVeYTENNMPgkkCYWHg","0DnYvbdoVg88EF2ddh7Tn6","6PY49R5SjxYDiOMFQj7Gsq","0i7AGJG9DX0vI1w798IVKZ","62jc4VA6WPoANaL9Duu8db","3tcMadg7fSfH0mFDo0408i","3WXhshrs1fzwF3rQE399Gq","6kh5fj610DhNF1e02og1PL","6NEyZ1rdMgO90cZ7U4UjO5","7ssKQDHJe7PhzFt0RBFlgt","7eXFZCiP9GqdMUashk96UF","7v9t1j6m5nYYGG1etmAD12","1QxbBB80IuPwhwW1ygGfPh","5R8T6F32PjJflb58Y564G0","01dQHUYz6EerSF6JQDolCC"]
        
        
        temp_playlist_id = '41Zy0SgcV5GVQ60rB4X4Tl'
        for i in track_ids:
            sp.playlist_add_items(playlist_id=playlist_id, items=[i])
            print("something")
            
        return "Songs added to playlist"

        
        
    except Exception as e:
        return f"Error adding songs to playlist: {str(e)}", 400
    
    
@app.route('/get_playlist_id', methods=['GET'])
def get_playlist_id():
    
    sp = spotipy.Spotify(auth=get_valid_token())
    
    try:
        playlists = sp.current_user_playlists()
        for playlist in playlists['items']:
            if playlist['name'] == 'My New Flask Playlist':
                return playlist['id']
        return None
    except Exception as e:
        return f"Error retrieving playlist ID: {str(e)}", 400

@app.route('/main', methods=['GET'])
def main():
    

    # Initialize Spotify client with valid token
    sp = spotipy.Spotify(auth=get_valid_token())

    try:
        # Call the functions and collect their results
        album_ids = get_album_ids()
        print("done1")
        album_songs = get_album_songs(album_ids)
        print("done2")
        get_playlist_id = create_playlist('tester')
        print("done3")
        add_songs_to_playlist(album_songs, get_playlist_id)
        print("done4")
      
      
        

        return (
            f"Main actions executed successfully!<br>"
            
            
        )
    except Exception as e:
        return f"Error executing main actions: {str(e)}", 400
    
    


if __name__ == '__main__':
    app.run(debug=False)
    
