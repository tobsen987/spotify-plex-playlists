import re
import time
import logging
from plexapi.server import PlexServer
from plexapi.audio import Track
import spotipy
import os
import spotipy.util as util
from spotipy.oauth2 import SpotifyClientCredentials
from typing import List


def filterPlexArray(plexItems=[], song="", artist="") -> List[Track]:
    for item in list(plexItems):
        if type(item) is not Track:
            plexItems.remove(item)
            continue
        if item.title.lower() != song.lower():
            plexItems.remove(item)
            continue
        artistItem = item.artist()
        if artistItem.title.lower() != artist.lower():
            plexItems.remove(item)
            continue

    return plexItems


def getSpotifyPlaylist(sp: spotipy.client, userId: str, playlistId: str) -> []:
    playlist = sp.user_playlist(userId, playlistId)
    return playlist


# Returns a list of spotify playlist objects of the user logged in
def getSpotifyLoggedUserPlaylists(sp: spotipy.client) -> []:
    playlists = sp.current_user_playlists()
    spotifyPlaylists = []
    while playlists:
        playlistItems = playlists['items']
        # logging.info(playlists['items'])
        for i, playlist in enumerate(playlistItems):
            spotifyPlaylists.append(getSpotifyPlaylist(sp, playlist['owner']['id'], playlist['id']))
        if playlists['next']:
            playlists = sp.next(playlists)
        else:
            playlists = None
    return spotifyPlaylists

# Returns a list of spotify playlist objects
def getSpotifyUserPlaylists(sp: spotipy.client, userId: str) -> []:
    playlists = sp.user_playlists(userId)
    spotifyPlaylists = []
    while playlists:
        playlistItems = playlists['items']
        for i, playlist in enumerate(playlistItems):
            if playlist['owner']['id'] == userId:
                spotifyPlaylists.append(getSpotifyPlaylist(sp, userId, playlist['id']))
        if playlists['next']:
            playlists = sp.next(playlists)
        else:
            playlists = None
    return spotifyPlaylists

def getSpotifyTracks(sp: spotipy.client, playlist: []) -> []:
    spotifyTracks = []
    tracks = playlist['tracks']
    spotifyTracks.extend(tracks['items'])
    while tracks['next']:
        tracks = sp.next(tracks)
        spotifyTracks.extend(tracks['items'])
    return spotifyTracks


def getPlexTracks(plex: PlexServer, spotifyTracks: []) -> List[Track]:
    plexTracks = []
    for spotifyTrack in spotifyTracks:
        track = spotifyTrack['track']
        logging.info("Searching Plex for: %s by %s" % (track['name'], track['artists'][0]['name']))

        try:
            musicTracks = plex.search(track['name'], mediatype='track')
        except:
            try:
                musicTracks = plex.search(track['name'], mediatype='track')
            except:
                logging.info("Issue making plex request")
                continue

        if len(musicTracks) > 0:
            plexMusic = filterPlexArray(musicTracks, track['name'], track['artists'][0]['name'])
            if len(plexMusic) > 0:
                logging.info("Found Plex Song: %s by %s" % (track['name'], track['artists'][0]['name']))
                plexTracks.append(plexMusic[0])
    return plexTracks


def createPlaylist(plex: PlexServer, sp: spotipy.Spotify, playlist: []):
    playlistName = playlist['owner']['display_name'] + " - " + playlist['name']
    logging.info('Starting playlist %s' % playlistName)
    plexTracks = getPlexTracks(plex, getSpotifyTracks(sp, playlist))
    if len(plexTracks) > 0:
        try:
            plexPlaylist = plex.playlist(playlistName)
            logging.info('Updating playlist %s' % playlistName)
            plexPlaylist.addItems(plexTracks)
        except:
            logging.info("Creating playlist %s" % playlistName)
            plex.createPlaylist(playlistName, plexTracks)

def parseSpotifyURI(uriString: str) -> {}:
    spotifyUriStrings = re.sub(r'^spotify:', '', uriString).split(":")
    spotifyUriParts = {}
    for i, string in enumerate(spotifyUriStrings):
        if i % 2 == 0:
            spotifyUriParts[spotifyUriStrings[i]] = spotifyUriStrings[i+1]

    return spotifyUriParts


def runSync(plex : PlexServer, sp : spotipy.Spotify, spotifyURIs: []):
    logging.info('Starting a Sync Operation')
    playlists = []

    for spotifyUriParts in spotifyURIs:
        if 'user' in spotifyUriParts.keys() and 'playlist' not in spotifyUriParts.keys():
            logging.info('Getting playlists for %s' % spotifyUriParts['user'])
            playlists.extend(getSpotifyUserPlaylists(sp, spotifyUriParts['user']))
        elif 'user' in spotifyUriParts.keys() and 'playlist' in spotifyUriParts.keys():
            logging.info('Getting playlist %s from user %s' % (spotifyUriParts['user'], spotifyUriParts['playlist']))
            playlists.append(getSpotifyPlaylist(sp, spotifyUriParts['user'], spotifyUriParts['playlist']))
        if os.environ.get('SPOTIPY_GET_ALL_USERS_PL') == "true":
            logging.info('Getting playlists for User that is logged in')
            playlists.extend(getSpotifyLoggedUserPlaylists(sp))
            

    for playlist in playlists:
        createPlaylist(plex, sp, playlist)


    logging.info('Finished a Sync Operation')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    spotifyUris = os.environ.get('SPOTIFY_URIS')

    if spotifyUris is None:
        logging.error("No spotify uris")

    secondsToWait = int(os.environ.get('SECONDS_TO_WAIT', 1800))
    baseurl = os.environ.get('PLEX_URL')
    token = os.environ.get('PLEX_TOKEN')
    username = os.environ.get('SPOTIFY_USER')
    plex = PlexServer(baseurl, token)

    token = util.prompt_for_user_token(username=username, scope='playlist-read-private', client_id=os.environ.get('SPOTIPY_CLIENT_ID'), client_secret=os.environ.get('SPOTIPY_CLIENT_SECRET'), redirect_uri='http://localhost/callback/', cache_path='/config/spotify-token')
    if token:
        sp = spotipy.Spotify(auth=token)

    #client_credentials_manager = SpotifyClientCredentials()
    #sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

    spotifyUris = spotifyUris.split(",")


    spotifyMainUris = []

    for spotifyUri in spotifyUris:
        spotifyUriParts = parseSpotifyURI(spotifyUri)
        spotifyMainUris.append(spotifyUriParts)

    while True:
        runSync(plex, sp, spotifyMainUris)
        time.sleep(secondsToWait)
