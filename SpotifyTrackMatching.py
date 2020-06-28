#!/usr/bin/env python

"""
Project           : McGill Billboard Project
Program name      : SpotifyTrackMatching.py
Author            : Lucas de Wolff, Jakko Vreeburg and Ruben Ahrens
Date created      : June, 2020
Purpose           : Adding Spotify analyses to specific dataset

This program is specifically used to search and match (if possible) the right Spotify analysis for multiple audio files for the McGill Billboard Project. 
The dataset must be in the following format: Eras -> Artists -> Songs -> audio_files
"""

import csv
import json
import os
import sys
import time

from difflib import SequenceMatcher
from dtw import dtw
import numpy as np
import pandas as pd
from scipy.stats import gmean
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

def divbygeomean(list):
    """
    Divide list by geometric mean.
    Input:
        list containing floats or integers, list cannot contain zeros and the funtion will produce an error if zero's are provided
    Returns:
        list containg floats or integers
    """
    return list/gmean(list)

def ExecuteTimeWarp(overwrite, root):
    """
    Determine if the Timewarp function should be executed or if it should overwrite the existing files.

    Input:    
    root: txt string containing the folder path in which the song you want to match is located
    overwrite: Bool, default = False
        If true:
            execute timewarp if differences.csv is present and overwrite it
        If False:
            execute timewarp only when differences.csv is not present.

    Returns:
        Bool:  
            True: if timewarp() should be executed
            False: if timewarp() should not be executed
    """
    if overwrite == True and os.path.isfile(root + '/spotify_track_id.csv'):
        return True

    if not os.path.isfile(root + '/differences.csv'):
        if os.path.isfile(root + '/spotify_track_id.csv'):
            return True

    return False

def search_song(artist, track, song_root, overwrite=False):
    """
    Search for spotify id's with the name in the filetree or in the echonest folder.
    The results are written to a csv file.

    Input:
        artist: txt string containing artist name
        track:  txt string containing track title
        song_root: txt string containing the folder path in which the song you want to match is located
        overwrite: Bool default = False
            If true:
                search when spotify_track_id.csv is present and overwrite it
            If False:
                search only when spotify_track_id.csv is not present.
    Returns:
        Nothing
    """
    if not os.path.isfile(song_root + '/spotify_track_id.csv') or overwrite == True:

        if os.path.isfile(song_root + '/echonest.json'):

            # We need to load the data of the echonest.json in order to extract the artist- and trackname.
            with open(song_root + '/echonest.json') as json_file: 
                data = json.load(json_file)
                artist_echo = data['meta']['artist']
                title_echo = data['meta']['title']
                artist_echo = artist_echo.translate({ord(i):None for i in "'"}) 
                title_echo = title_echo.translate({ord(i):None for i in "'"})
            search_list = []

            # Removes apostrophes in order to improve the API search results.
            artist = artist.translate({ord(i):None for i in "'"}) 
            track = song.translate({ord(i):None for i in "'"})

            # This checks if both the artist and title of the echonest features are non_empty strings.
            if artist_echo and title_echo:
                tracks = spotify.search(q='artist:' + str(artist_echo) + ' track:' + str(title_echo), type='track', limit=50) # This uses echonest to look for tracks with the Spotify API
                search_list = search_list+tracks['tracks']['items']

            # If the echonest names are the exact same as the folder names, the Spotify API query would be the exact same.
            if artist_echo != artist or title_echo != track:
                # This uses the folder names to look for tracks with the Spotify API
                tracks_folder = spotify.search(q='artist:' + artist + ' track:' + track, type='track', limit=50)
                # The search results are also added to the search_list. This obviously could result in duplicates. This will be taken care of later.
                search_list= search_list+tracks_folder['tracks']['items']

            # Sometimes no results are found
            if len(search_list) > 0:

                # In case the code is run multiple times and it created a no_result.txt file when there were no search results.
                try:
                    os.remove(song_root + "/no_result.txt") 
                except OSError:
                    pass

                df = pd.DataFrame()
                uris = []
                tempo = []
                loudness = []
                song_length = []

                # Before extracting the audio features of each individual track, the duplicate tracks are removed with the set() function.
                features = spotify.audio_features(tracks=list(set([item['uri'] for item in search_list])))
                
                # extract all needed data and write this to the csv file
                
                for feature in features:
                    if feature:
                        uris.append(feature['uri'])
                        tempo.append(feature['tempo'])
                        loudness.append(feature['loudness'])
                        song_length.append(feature['duration_ms'])

                df.insert(len(df.columns), 'Spotify_id', uris, True)
                df.insert(len(df.columns), 'bpm', tempo, True)
                df.insert(len(df.columns), 'loudness', loudness, True)
                df.insert(len(df.columns), 'song_length', song_length, True)
                df.to_csv(str(song_root + '/spotify_track_id.csv'), index=False)

            # In case no results are found. This will create a 'no_result.txt' file, containing the query.
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
    This results in a .csv file containing a spotify trackid with the corresponding dtw_timbre, dtw_pithces, 
    delta_bpm, delta_loudness and delta_length.

    Input:
        song_root: txt string containing the folder path in which the song you want to match is located
        compare_features: list containing features to execute timewarping on, using something other than timbre and
        pitches could require changes to the function.
    
    Returns:
        Nothing
    """
    # Only execute timewarp() if True is returned
    if ExecuteTimeWarp(overwrite, song_root):

        # Extract the spotify track ids of a given track
        df = pd.read_csv(song_root + '/spotify_track_id.csv', delimiter=',')

        with open(song_root + '/echonest.json') as json_file:
            # data also contains the timbre and pitches, which the dynamic time warping function needs.
            data = json.load(json_file)
            true_tempo = data['track']['tempo']
            true_loudness = data['track']['loudness']
            # The echonest songlength is originally in seconds and needs to be in miliseconds in order to match spotify's format.
            true_length = data['track']['duration']*1000

        trax = df['Spotify_id']
        features = [[] for feature in compare_features]
        for track_id in trax:
            # In case either the spotify analysis doesn't exist or something else prevents the retrieval process.
            try:
                # The 'segments' tag contains low-level audio features segmented into multiple small time segments.
                track_analysis = spotify.audio_analysis(track_id)['segments']
                for i in range(len(compare_features)):
                    
                    if compare_features[i] == 'pitches':
                        query = []

                        # Normalize each pitches segment with the geometric mean function. 
                        for segment in data['segments']:
                            pitches_lijst = segment[compare_features[i]]

                            if not 0 in pitches_lijst:
                                lijst = divbygeomean(pitches_lijst)
                            else:
                                # This prevents a 'ZeroDivisionError'.
                                lijst = pitches_lijst/gmean([num for num in pitches_lijst if num >0])

                            query.append(lijst)

                        template = []
                        # Also normalize the Spotify pitch segments
                        for segment in track_analysis:
                            pitches_lijst = segment[compare_features[i]]
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
                    # Only plot if the user wants to.
                    if plot == True:
                        path.plot(type="threeway")

            except:
                print("404")
                track_analysis = None
                features[0].append(100)
                features[1].append(100)
            # This prevents the Spotify API from getting too many requests at once and returning an error.
            time.sleep(0.1)
            
        if "dtw_timbre" not in df.columns:
            df.insert(len(df.columns), "dtw_timbre", features[0], True)
            df.insert(len(df.columns), "dtw_pitches", features[1], True)
            delta_tempo_list = []
            # Sometimes the tempo is measured differently e.g. 2 times as fast or 2 times as slow, these should still be recognized as the same tempo.
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
    """
    Determines the best track, given the pitch and timber combination and corresponding weights.
    The algorithm loops over every track and breaks once a track is found which has no relatively better track. 
    Otherwise it keeps searching until it does. Ultimately the last song is selected if no previous song was selected.
    
    Input:
        lijst: A list containing the pitches and timbres in the following format -> [[x,y] for x, y in zip(pitch, timbre)]
        pitch_weight: The weight given to the pitch feature.
        timbre_weight: The weight given to the timbre feature.

    Returns:
        The best pitch-timber combination.
    """
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
    """
    Input:
        song: A list in the format of [pitch, timbre] selected by the weighted() function
        params: A tuple that contains the threshold values (threshold_pitch, threshold_timbre).
    Returns:
        A tuple:
            First element:
                0, if no perfect match is found or an error occured
                1, if the perfect match is found
            Second element:
                Either an error message when the first element is 0 or the matched song.
    """
    if len(song) != len(params):
        return (0, "Not same amount of parameters given as features")

    else:
        for feature, param in zip(song, params):

            if feature > param:
                return (0, "No perfect match is available")

        return (1, song)

def select(song_root, threshold_pitch, threshold_timbre, overwrite=False):
    """
    Select the best matched songs.

    Input:
        song_root: the song you want to 

    Returns:

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

if __name__ == "__main__":
    compare_features = ['timbre', 'pitches']
    overwrite = False
    plot = False
    threshold_pitch = 0.5
    threshold_timbre = 50

    spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

    track = ''
    artist = ''

    # The dataset should be in a folder called 'Billboard_private_data' and in the same parentfolder as this code.
    rootdir = "../Billboard_private_data"

    for item in os.listdir(rootdir):
        year_root = os.path.join(rootdir, item)

        for artist in os.listdir(year_root):

            if artist == '__MACOSX':
                break
            
            
            artist_root = os.path.join(year_root, artist)

            if not os.path.isdir(artist_root):
                error = artist_root
                break

            for song in os.listdir(artist_root):
                song_root = os.path.join(artist_root, song)

                if os.path.isfile(song_root):
                    break
                
                print(song_root)

                search_song(artist, song, song_root, overwrite=overwrite)
                timewarp(song_root, compare_features, overwrite=overwrite, plot=plot)
                select(song_root, threshold_pitch, threshold_timbre, overwrite=overwrite)