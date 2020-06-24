import spotipy
import sys
from spotipy.oauth2 import SpotifyClientCredentials
from difflib import SequenceMatcher
import os
import csv
import json
import pandas as pd
from dtw import *
import numpy as np
from scipy.stats import gmean
import time

def divbygeomean(list):
    return list/gmean(list)

def loop(overwrite, root):
    if overwrite == True and os.path.isfile(root + '/spotify_track_id.csv'):
        return True
    if not os.path.isfile(root + '/differences.csv'):
        if os.path.isfile(root + '/spotify_track_id.csv'):
            return True
    return False

def search_song(artist, track, song_root, overwrite=False):
    """
    Search for spotify id's with the name in the filetree or in the echonest folder.
    Write the results to a csv.
    """
    if not os.path.isfile(song_root + '/spotify_track_id.csv') or overwrite == True:
        if os.path.isfile(song_root + '/echonest.json'):
            with open(song_root + '/echonest.json') as json_file:
                data = json.load(json_file)
                artist_echo = data['meta']['artist']
                title_echo = data['meta']['title']
            search_list = []
            if artist_echo and title_echo:
                tracks = spotify.search(q='artist:' + str(artist_echo) + ' track:' + str(title_echo), type='track', limit=50)
                search_list = search_list+tracks['tracks']['items']
            artist = artist.translate({ord(i):None for i in "'"})
            track = song.translate({ord(i):None for i in "'"})
            if artist_echo != artist or title_echo != track:
                tracks_folder = spotify.search(q='artist:' + artist + ' track:' + track, type='track', limit=50)
                search_list= search_list+tracks_folder['tracks']['items']
            if len(search_list) > 0:
                try:
                    os.remove(song_root + "/no_result.txt")
                except OSError:
                    pass
                df = pd.DataFrame()
                uris = []
                tempo = []
                loudness = []
                song_length = []
                features = spotify.audio_features(tracks=list(set([item['uri'] for item in search_list])))
                for feature in features:
                    uris.append(feature['uri'])
                    tempo.append(feature['tempo'])
                    loudness.append(feature['loudness'])
                    song_length.append(feature['duration_ms'])
                df.insert(len(df.columns), 'Spotify_id', uris, True)
                df.insert(len(df.columns), 'bpm', tempo, True)
                df.insert(len(df.columns), 'loudness', loudness, True)
                df.insert(len(df.columns), 'song_length', song_length, True)
                df.to_csv(str(song_root + '/spotify_track_id.csv'), index=False)
            else:
                try:
                    os.remove(song_root + "/spotify_track_id.csv")
                except OSError:
                    pass
                try:
                    os.remove(song_root + "/differences.csv")
                except OSError:
                    pass
                try:
                    os.remove(song_root + "/spotify.json")
                except OSError:
                    pass
                text_file = open(song_root + "/no_result.txt", "w")
                text_file.write('No result for: \n' + "spotify.search(q='artist:" + str(artist_echo) + " track:" + str(title_echo) + 
                "', type='track', limit=50)\nspotify.search(q=artist:'" + str(artist) + "' track:'" + track + "', type='track', limit=50)")
                text_file.close()

def timewarp(song_root, compare_features, overwrite=False, plot=False):
    """
    Evaluate search results based on audio analysis and other audio features.
    """
    if loop(overwrite, song_root):
        df = pd.read_csv(song_root + '/spotify_track_id.csv', delimiter=',')
        tempo_list = list(df['bpm'])
        with open(song_root + '/echonest.json') as json_file:
            data = json.load(json_file)
            true_tempo = data['track']['tempo']
            true_loudness = data['track']['loudness']
            true_length = data['track']['duration']*1000
        trax = df['Spotify_id']

        features = [[] for feature in compare_features]
        for track_id in trax:
            try:
                track_analysis = spotify.audio_analysis(track_id)['segments']
                for i in range(len(compare_features)):
                    if compare_features[i] == 'pitches':
                        query = []
                        for ding in data['segments']:
                            pitches_lijst = ding[compare_features[i]]
                            if not 0 in pitches_lijst:
                                lijst = divbygeomean(pitches_lijst)
                            else:
                                # Idee: haal 0-en eruit en deel de hele lijst door die mean
                                lijst = pitches_lijst/gmean([num for num in pitches_lijst if num >0])
                            query.append(lijst)
                        template = []
                        for ding in track_analysis:
                            if not 0 in pitches_lijst:
                                lijst = divbygeomean(pitches_lijst)
                            else:
                                lijst = pitches_lijst/gmean([num for num in pitches_lijst if num >0])
                            template.append(lijst)
                    else:
                        query = [ding[compare_features[i]] for ding in data['segments']]
                        template = [ding[compare_features[i]] for ding in track_analysis]
                    # divide vector by !geometric! mean before dynamic timewarping, only for pitches
                    path = dtw(query, template, keep_internals=True, dist_method="euclidean")
                    features[i].append(path.normalizedDistance)
                    if plot == True:
                        path.plot(type="threeway")
            except:
                print("404")
                track_analysis = None
                features[0].append(100)
                features[1].append(100)
            time.sleep(0.1)
            
        if "dtw_timbre" not in df.columns:
            df.insert(len(df.columns), "dtw_timbre", features[0], True)
            df.insert(len(df.columns), "dtw_pitches", features[1], True)
            delta_tempo_list = []
            for tempo in df["bpm"]:
                tempos = [tempo/2, tempo, tempo*2]
                delta_tempo_list.append(min([abs(true_tempo-tempo) for tempo in tempos]))
            df.insert(len(df.columns), "delta_bpm", [abs(true_tempo-tempo) for tempo in df["bpm"]], True)
            df.insert(len(df.columns), "delta_loudness", [abs(true_loudness-loudness) for loudness in df["loudness"]], True)
            df.insert(len(df.columns), "delta_length", [abs(true_length-length) for length in df["song_length"]], True)
        else:
            df["dtw_timbre"] = features[0]
            df["dtw_pitches"] = features[1]
        if df.shape[0] > 1:
            df.to_csv(str(song_root + '/differences.csv'), index=False)

def weighted(lijst, pitch_weight=0.5, timbre_weight=0.5):
    weights = [pitch_weight, timbre_weight]
    total_weight = 1
    for weight in weights:
        total_weight *= weight
    length_lijst = len(lijst)
    length_song = len(lijst[0])
    for i in range(length_lijst-1):
        better = False
        main = lijst[i]
        for j in range(i+1, length_lijst):
            compare = lijst[j]
            value = 1
            for x in range(length_song):
                value *= (compare[x] / main[x]) * weights[x]
            if value < total_weight:
                better = True
                break
        if not better:
            return main
    return lijst[-1]

def threshold(song, params):
    if len(song) != len(params):
        return (0, "Not same amount of parameters given as features")
    else:
        for feature, param in zip(song, params):
            if feature > param:
                return (0, "No perfect match is available")
        return (1, song)

def select(song_root, threshold_pitch, threshold_timbre, overwrite=False):
    """
    Select the best matched songs
    """
    # if os.path.isfile(song_root + '/differences.csv') or overwrite == True and os.path.isfile(song_root + '/differences.csv'):
    if (not os.path.isfile(song_root + '/spotify.json')) and os.path.isfile(song_root + '/differences.csv') or overwrite == True and os.path.isfile(song_root + '/differences.csv'):
        df = pd.read_csv(song_root + '/differences.csv')
        if df.shape[0] < 2:
            return
        pitch, timbre = df['dtw_pitches'], df['dtw_timbre']
        lijst = [[x,y] for x, y in zip(pitch, timbre)]
        result = threshold(weighted(lijst), (threshold_pitch, threshold_timbre))
        selected_song = df['Spotify_id'][lijst.index(result[1])] if result[0] == 1 else None
        if not selected_song == None:
            data = dict()
            data["differeces"] = dict()
            for column in list(df):
                data["differeces"][column] = df[column].tolist()[lijst.index(result[1])]
            data['track'] =  spotify.track(selected_song)
            data["features"] = spotify.audio_features(selected_song)
            data["analysis"] = spotify.audio_analysis(selected_song)
            with open(song_root + '/spotify.json', 'w') as outfile:
                json.dump(data, outfile)
        else:
            with open(song_root + '/spotify.json', 'w') as outfile:
                json.dump(None, outfile)

compare_features = ['timbre', 'pitches']
overwrite = False
plot = False
threshold_pitch = 20
threshold_timbre = 60

spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

track = ''
artist = ''

rootdir = "../Billboard_private_data"
for item in os.listdir(rootdir):
    print(item)
    year_root = os.path.join(rootdir, item)
    for artist in os.listdir(year_root):
        if artist == '__MACOSX':
            break
        print(artist)
        artist_root = os.path.join(year_root, artist)
        if not os.path.isdir(artist_root):
            error = artist_root
            break
        for song in os.listdir(artist_root):
            song_root = os.path.join(artist_root, song)
            if os.path.isfile(song_root):
                break
            search_song(artist, song, song_root, overwrite=overwrite)
            timewarp(song_root, compare_features, overwrite=overwrite, plot=plot)
            select(song_root, threshold_pitch, threshold_timbre, overwrite=overwrite)