import json
import requests
import audio_metadata
import os
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import random

spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())


overwrite = True
count_good = 0
count_match = 0

randomlist = random.choices(range(900), k = 100)
randomlist = [829, 495, 532, 462, 841, 536, 97, 136, 297, 245, 177, 761, 498, 110, 314, 648, 726, 52, 386, 475, 712, 590, 747, 342, 290, 273, 188, 443, 122, 897, 5, 533, 172, 556, 245, 818, 500, 26, 86, 877, 547, 95, 208, 481, 411, 84, 220, 755, 641, 295, 92, 127, 542, 524, 377, 176, 184, 212, 116, 401, 743, 853,6, 608, 427, 604, 372, 654, 866, 174, 53, 89, 628, 71, 719, 464, 393, 677, 817, 243, 606, 103, 735, 456, 839, 52, 697, 17, 381, 196, 661, 881, 602, 2732, 248, 45, 333, 301, 599, 515, 823, 793]
rootdir = "../Billboard_private_data"
for item in os.listdir(rootdir):
    year_root = rootdir + "/" + item
    for artist in os.listdir(year_root):
        if artist == '__MACOSX':
            break # mss verwijderen, ff vragen client
        artist_root = year_root + "/" + artist
        if not os.path.isdir(artist_root):
            error = artist_root
            break
        for song in os.listdir(artist_root):
            song_root = artist_root + "/" + song
            # for file in ['differences.csv', 'spotify_track_id.csv', 'spotify.json', 'analyses.json']:
            #     try:
            #         os.remove(song_root + "/" + file)
            #     except OSError:
            #         pass
            try:
                with open(song_root + '/spotify.json') as json_file:
                    data = json.load(json_file)
                if data == None:
                    count_bad += 1
                else:
                    count_good += 1
                    for item in randomlist:
                        if count_good == item:
                            print(year_root, [artist['name'] for artist in data['track']['artists']][0], "-", data['track']['name'], data['track']['uri'])
                            inp = input("Good?")
                            if inp == "y":
                                count_match += 1
            except:
                pass
                    
print(count_good)
print(count_match)