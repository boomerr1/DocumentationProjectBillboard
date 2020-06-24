import json
import requests
import audio_metadata
import os

api_url_base = 'https://acousticbrainz.org'

headers = {'Content-Type': 'application/json',
           'User-Agent': 'Devbom'}

def get_jsonofmbid(mbid):

    api_url_low = api_url_base + '/api/v1/' + mbid + '/low-level'
    # api_url_high = api_url_base + '/api/v1/' + mbid + '/high-level'
    low_response = requests.get(api_url_low, headers=headers)
    # high_response = requests.get(api_url_high, headers=headers)
    print(low_response.content)

# get_jsonofmbid('94cb2de5-ed29-49d6-b541-237ec3c31cea')

# rootdir = "../Billboard_private_data"
# for x in os.walk(rootdir):
#     count = 0
#     for foldername in x[1]:
#         metadata = audio_metadata.load(x[0] + '/' + foldername + "/audio.flac")
        
metadata = audio_metadata.load("../Billboard_private_data/A Taste Of Honey _-_ Boogie Oogie Oogie/audio.flac")
metadata['tags']['musicbrainz_trackid'][0]

# get_jsonofmbid('66c91549-0e6c-47f9-a313-6003d79f982e')