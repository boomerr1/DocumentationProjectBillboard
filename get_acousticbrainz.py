import json
import requests
import audio_metadata
import os
import time

api_url_base = 'https://acousticbrainz.org'

headers = {'Content-Type': 'application/json',
           'User-Agent': 'Biological Intelligence'}

def get_jsonofmbid(mbid):

    api_url_low = api_url_base + '/api/v1/' + mbid + '/low-level'
    # api_url_high = api_url_base + '/api/v1/' + mbid + '/high-level'
    low_response = requests.get(api_url_low, headers=headers, timeout=10)
    # high_response = requests.get(api_url_high, headers=headers)
    return low_response.content

# print(get_jsonofmbid("92a33c7d-0bc0-46bb-8186-59541e1d089e"))


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
            audio_root = song_root + "/audio.flac"
            if os.path.isfile(song_root) or (not os.path.isfile(audio_root)):
                break
            # print(song_root)
            metadata = audio_metadata.load(audio_root)
            # print(metadata)
            if 'musicbrainz_trackid' in metadata['tags'].keys():
                trackid = metadata['tags']['musicbrainz_trackid'][0]
                data = json.loads(get_jsonofmbid(trackid))
                if data == {"message":"Not found"}:
                    data = {"message":"Acousticbrainz features not found with musicbrainz trackid"}
                    print(song_root)
                    print(trackid)
                with open(song_root + '/acousticbrainz.json', 'w') as outfile:
                    json.dump(data, outfile)
                    # print("v")
            time.sleep(0.2)
