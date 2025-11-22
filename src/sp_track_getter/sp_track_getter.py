#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2025 Eren-is
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

import re
import json
import time
import base64
import requests
import argparse
from urllib.parse import quote
from sseclient import SSEClient
from datetime import datetime, timedelta

class SpTrackGetter:
    SP_URL_PATTERN = r"https:\/\/open\.spotify\.com\/[\w\-\/]*track\/[\w?=\-&]+"
    YT_SEARCH_URL = "https://www.youtube.com/results?search_query={}"
    SP_API_AUTH_URL = "https://accounts.spotify.com/api/token"
    SP_API_TRACKS_URL = "https://api.spotify.com/v1/tracks/"
    REC_API_AUDIO_FEATURES_URL = "https://api.reccobeats.com/v1/audio-features?ids="
    SS_API_AUDIO_FEATURES_URL = "https://soundstat.info/api/v1/track/"

    def __init__(
            self,
            url: str = "",
            use_sp_api: bool = True,
            sp_client_id: str = "",
            sp_client_secret: str = "",
            use_rec_api: bool = True,
            use_ss_api: bool = False,
            ss_api_key: str = "",
            ss_convert_vals_to_sp: bool = True,
            rec_fallback_to_ss: bool = False):
        self.__sp_client_id = sp_client_id
        self.__sp_client_secret = sp_client_secret
        self.__sp_access_token = ""
        self.__sp_token_valid_until = datetime.now()
        self.__ss_api_key = ss_api_key
        self.use_sp_api = use_sp_api
        self.use_rec_api = use_rec_api
        self.use_ss_api = use_ss_api
        self.ss_convert_vals_to_sp = ss_convert_vals_to_sp
        self.rec_fallback_to_ss = rec_fallback_to_ss
        self.data = {}
        # Status variables
        self.rec_audio_features_not_found = False
        self.ss_track_analysing = False

        if len(url) > 0:
            self.load_track_data(url)
    @classmethod
    def get_id_from_url(cls, url: str) -> str:
        return url.split('/')[-1].split('&')[0].split('?')[0]

    @classmethod
    def sp_url_find(cls, string: str) -> str:
        result = re.search(cls.SP_URL_PATTERN, string)
        if result is None:
            return ""
        else:
            return result.group()

    def load_track_data(
            self,
            url: str,
            use_sp_api: bool|None = None,
            use_rec_api: bool|None = None,
            use_ss_api: bool|None = None):
        use_sp_api_ = use_sp_api if use_sp_api is not None else self.use_sp_api
        use_rec_api_ = use_rec_api if use_rec_api is not None else self.use_rec_api
        use_ss_api_ = use_ss_api if use_ss_api is not None else self.use_ss_api

        self.url = url
        self.id = self.get_id_from_url(url)

        if use_sp_api_ is True:
            # Make sure we have an API token
            self.__sp_auth()
            # Get track data
            data = self._sp_get_track_data()
            self.load_sp_data(data)

        if use_rec_api_ is True:
            self.rec_audio_features_not_found = False
            data = self._rec_get_audio_features_data()
            if len(data) > 0 and data["content"] != []:
                self.load_rec_data(data)
            else:
                self.rec_audio_features_not_found = True
                if self.rec_fallback_to_ss is True:
                    pass

        if use_ss_api_ is True:
            # Do not call ss when fallback is enabled and song has been found on rec
            if self.rec_fallback_to_ss is True and self.rec_audio_features_not_found is False:
                return

            self.ss_track_analysing = False
            data = self._ss_get_audio_features_data()
            if self.ss_track_analysing is False:
                self.load_ss_data(data)

    def load_sp_data(self, data: dict):
        # Merge dictionaries
        self.data = self.data | data
        self.youtube_search_url = self.get_yt_search_url(self.data["artists"][0]["name"], self.data["name"])

    def load_rec_data(self, data: dict):
        _data = data["content"][0]
        self.data["acousticness"] = _data["acousticness"]
        self.data["danceability"] = _data["danceability"]
        self.data["energy"] = _data["energy"]
        self.data["instrumentalness"] = _data["instrumentalness"]
        self.data["liveness"] = _data["liveness"]
        self.data["loudness"] = _data["loudness"]
        self.data["speechiness"] = _data["speechiness"]
        self.data["valence"] = _data["valence"]
        self.data["tempo"] = _data["tempo"]

    def load_ss_data(self, data: dict, ss_convert_vals_to_sp: bool|None = None):
        ss_convert_vals_to_sp_ = ss_convert_vals_to_sp if ss_convert_vals_to_sp is not None else self.ss_convert_vals_to_sp
        _data = data["features"]
        self.data["genre"] = data["genre"]
        self.data["tempo"] = _data["tempo"]
        self.data["mode"] = _data["mode"]
        self.data["key"] = _data["key"]
        self.data["key_confidence"] = _data["key_confidence"]
        self.data["energy"] = _data["energy"]
        self.data["acousticness"] = _data["acousticness"]
        self.data["danceability"] = _data["danceability"]
        self.data["instrumentalness"] = _data["instrumentalness"]
        self.data["loudness"] = _data["loudness"]
        self.data["valence"] = _data["valence"]

        if ss_convert_vals_to_sp_ is True:
            # Values from https://soundstat.info/article/Understanding-Audio-Analysis.html
            self.data["energy"] = self.data["energy"] * 2.25
            self.data["acousticness"] = self.data["acousticness"] * 0.005
            self.data["instrumentalness"] = self.data["instrumentalness"] * 0.03
            self.data["loudness"] = -(1 - self.data["loudness"]) * 14

    def get_yt_search_url(self, artist: str, title: str) -> str:
            encoded_text = quote(f"{artist} {title}")
            return self.YT_SEARCH_URL.format(encoded_text)

    def dump_data(self):
        print(json.dumps(self.data, indent=2))

    def listen_for_ss_track_analysis_status(self, total_timeout: int = 10 * 60) -> tuple[str, str]:
        header = {"accept" : "application/json",
                  "x-api-key": self.__ss_api_key}
        url = f"{self.SS_API_AUDIO_FEATURES_URL}{self.id}/status"

        time_start = time.monotonic()

        try:
            with requests.get(url, headers=header, stream=True, timeout=30) as response:
                response.raise_for_status()
                client = SSEClient(response)
                for event in client.events():
                    if time.monotonic() - time_start > total_timeout:
                        return "error", "Total timeout for listen"
                    if event.event in ("complete", "error"):
                        self.ss_track_analysing = False
                        return event.event, event.data
                # Loop exited without "complete" or "error"
                return "disconnected", None
        except requests.RequestException as e:
            return "network_error", str(e)
        except Exception as e:
            return "error", str(e)

    def _sp_get_track_data(self, timeout: int|float = 30) -> dict:
        header = {"Authorization": f"Bearer {self.__sp_access_token}"}
        url = f"{self.SP_API_TRACKS_URL}{self.id}"
        response = requests.get(url, headers=header, timeout=timeout)

        if response.status_code != 200:
            raise Exception(f"Invalid response when getting track data: {response.status_code}")

        return response.json()

    def _rec_get_audio_features_data(self, timeout: int|float = 30) -> dict:
        header = {"Accept" : "application/json"}
        url = f"{self.REC_API_AUDIO_FEATURES_URL}{self.id}"
        response = requests.get(url, headers=header, timeout=timeout)

        if response.status_code == 404:
            return {}

        if response.status_code != 200:
            raise Exception(f"Invalid response when getting audio features: {response.status_code}")

        return response.json()

    def _ss_get_audio_features_data(self, timeout: int|float = 30) -> dict:
        header = {"accept" : "application/json",
                  "x-api-key": self.__ss_api_key}
        url = f"{self.SS_API_AUDIO_FEATURES_URL}{self.id}"
        response = requests.get(url, headers=header, timeout=timeout)

        if response.status_code == 202:
            response_json = response.json()
            if "analysis in progress" in response_json["detail"]:
                self.ss_track_analysing = True
                return {}
            else:
                raise Exception(f"Invalid response for track analysis: {response.status_code} - {response_json["detail"]}")

        if response.status_code != 200:
            raise Exception(f"Invalid response when getting audio features: {response.status_code}")

        return response.json()

    def __sp_auth(self, force: bool = False):
        if (len(self.__sp_access_token) == 0 or datetime.now() > self.__sp_token_valid_until or force is True):
            auth_data = f"{self.__sp_client_id}:{self.__sp_client_secret}"
            auth_data_base64 = base64.b64encode(auth_data.encode())
            header = {"Content-Type": "application/x-www-form-urlencoded",
                      "Authorization": f"Basic {auth_data_base64.decode("ascii")}",
                      "Cache-Control": "no-cache",
                      "Pragma": "no-cache"}
            data = {"grant_type" : "client_credentials"}
            response = requests.post(self.SP_API_AUTH_URL, headers=header, data=data)

            if response.status_code != 200:
                raise Exception(f"Failed to acquire API access token: {response.status_code}")

            response_json = response.json()
            self.__sp_token_valid_until = datetime.now() + timedelta(seconds=response_json["expires_in"])
            self.__sp_access_token = response_json["access_token"]

def spotify_url_type(arg: str) -> str:
    if re.match(SpTrackGetter.SP_URL_PATTERN, arg) is None:
        raise argparse.ArgumentTypeError(f"Invalid URL format: {arg}")
    else:
        return arg

if __name__ == "__main__":
    from dotenv import dotenv_values

    parser = argparse.ArgumentParser(description="Get Spotify song info from a Spotify url")
    parser.add_argument("url", type=spotify_url_type, help="Song URL")
    args = parser.parse_args()

    config = dotenv_values(".env")

    if "SPOTIFY_CLIENT" not in config or "SPOTIFY_SECRET" not in config:
        raise Exception("Missing SPOTIFY_CLIENT or SPOTIFY_SECRET in .env file")

    # Only use Spotify and ReccoBeats:
    track = SpTrackGetter(
            url=args.url,
            use_sp_api=True,
            sp_client_id=config["SPOTIFY_CLIENT"],
            sp_client_secret=config["SPOTIFY_SECRET"],
            use_rec_api=True)

    # Use Spotify, ReccoBeats
    # and SoundStat as fallback (if ReccoBeats doesn't have audio features):
    # track = SpTrackGetter(
    #         url=args.url,
    #         use_sp_api=True,
    #         sp_client_id=config["SPOTIFY_CLIENT"],
    #         sp_client_secret=config["SPOTIFY_SECRET"],
    #         use_rec_api=True,
    #         use_ss_api=True,
    #         ss_api_key=config["SOUNDSTAT_KEY"])

    track.dump_data()
    print(f"Title: {track.data["name"]}")
    print(f"Artist: {track.data["artists"][0]["name"]}")
    print(f"Album: {track.data["album"]["name"]}")
    print(f"YouTube search URL: {track.youtube_search_url}")
    if track.rec_audio_features_not_found is False:
        print(f"Track's valence: {track.data["valence"]}")
    else:
        print("Track's audio features not found in ReccoBeats")
