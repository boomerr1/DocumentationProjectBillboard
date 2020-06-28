#!/usr/bin/env python

"""
Project           : McGill Billboard Project
Program name      : get_acousticbrainz.py
Author            : Lucas de Wolff, Jakko Vreeburg and Ruben Ahrens
Date created      : June, 2020
Purpose           : Adding AcousticBrainz features to specific dataset

Given a dataset in the form of 'Billboard_private_data' -> eras -> artists -> songs -> audio_files, this program 
requests the AcousticBrainz features and writes them to acousticbrainz.json.
"""

import json
import os
import time

import requests
import audio_metadata

api_url_base = 'https://acousticbrainz.org'

headers = {'Content-Type': 'application/json',
           'User-Agent': 'Biological Intelligence'}

# Given the mbid of a certain track, this function requests the low level features of that track.
def get_jsonofmbid(mbid):
    api_url_low = api_url_base + '/api/v1/' + mbid + '/low-level'
    low_response = requests.get(api_url_low, headers=headers, timeout=10)
    return low_response.content

rootdir = "../Billboard_private_data"
for item in os.listdir(rootdir):
    year_root = rootdir + "/" + item

    for artist in os.listdir(year_root):

        if artist == '__MACOSX':
            break

        artist_root = year_root + "/" + artist

        if not os.path.isdir(artist_root):
            error = artist_root
            break
        
        for song in os.listdir(artist_root):
            
            song_root = artist_root + "/" + song
            audio_root = song_root + "/audio.flac"
            # Breaks if either the file already exists or if the audio file can't be located.
            if os.path.isfile(song_root) or (not os.path.isfile(audio_root)):
                break

            # The data should have been tagged by an MusicBrainz tagger, such as Picard.
            metadata = audio_metadata.load(audio_root)

            if 'musicbrainz_trackid' in metadata['tags'].keys():
                trackid = metadata['tags']['musicbrainz_trackid'][0]
                data = json.loads(get_jsonofmbid(trackid))

                # An error message is written to the .json file if the musicbrainz_trackid can't be found.
                if data == {"message":"Not found"}:
                    data = {"message":"Acousticbrainz features not found with musicbrainz trackid"}
                    print(song_root)
                    print(trackid)

                with open(song_root + '/acousticbrainz.json', 'w') as outfile:
                    json.dump(data, outfile)
            # This time out makes sure the API won't get too many requests.
            time.sleep(0.2)
