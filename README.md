# sp_track_getter

## Aggregate Spotify song/track data using Spotify API with audio features data from ReccoBeats and/or SoundStat.
Additionally creates a YouTube search url (artist + title as search query) (only after getting data from Spotify API).

Spotify data:
- [Spotify API "Get Track" reference](https://developer.spotify.com/documentation/web-api/reference/get-track)

Additionally:
- YouTube search URL

Audio features:
- ReccoBeats:
    - Acousticness
    - Danceability
    - Energy
    - Instrumentalness
    - Liveness
    - Loudness
    - Speechiness
    - Valence
    - Tempo
- SoundStat:
    - Genre
    - Tempo
    - Mode
    - Key
    - Key confidence
    - Energy
    - Acousticness
    - Danceability
    - Instrumentalness
    - Loudness
    - Valence

## SpTrackGetter arguments
When creating a new SpTrackGetter instance, you can configure it with the following parameters:
| Argument                | Type   | Default | Description                                                                                    |
| ----------------------- | ------ | ------- | ---------------------------------------------------------------------------------------------- |
| `url`                   | `str`  | `""`    | The track URL to process. Leave empty if you plan to provide the URL later via method calls.   |
| `use_sp_api`            | `bool` | `True`  | Whether to use the Spotify API for fetching track data.                                        |
| `sp_client_id`          | `str`  | `""`    | Spotify API client ID (required if `use_sp_api=True` and authentication is needed).            |
| `sp_client_secret`      | `str`  | `""`    | Spotify API client secret (required if `use_sp_api=True`).                                     |
| `use_rec_api`           | `bool` | `True`  | Whether to use the ReccoBeats API as a source of track audio features data. |
| `use_ss_api`            | `bool` | `False` | Whether to use SoundStat API as a source of track audio features data.                                |
| `ss_api_key`            | `str`  | `""`    | API key for the SoundStat API (required if `use_ss_api=True`).                                        |
| `ss_convert_vals_to_sp` | `bool` | `True`  | If `True`, values returned from the SoundStat API will be converted into Spotify-compatible values.  |
| `rec_fallback_to_ss`    | `bool` | `False` | If `True`, when the ReccoBeats API doesn't return audio features data, the SoundStat API will be used as a fallback.              |

Example:
```python
from sp_track_getter import SpTrackGetter

track = SpTrackGetter(use_rec_api=True)
track.load_track_data(url="https://open.spotify.com/track/25mgvKnePKbDpStpjy9sT1")
```

## ReccoBeats API
When using [ReccoBeats API](https://reccobeats.com) if no audio feature data was found/returned variable `rec_audio_features_not_found` will be set to `True`.

## SoundStat API
[SoundStat API](https://soundstat.info) automatically starts track analysis when it can't find audio data in its database. In such a case variable `ss_track_analysis` will be set to `True`.
SoundStat API provides a way to check on analysis status using Server-Sent Events (SSE). User can use `listen_for_ss_track_analysis_status()` to wait for track analysis to complete.

```python
# def listen_for_ss_track_analysis_status(self, total_timeout: int = 10 * 60) -> tuple[str, str]
event, description = track.listen_for_ss_track_analysis_status()
```
Possible event and description values:
| Event            | Description                  | Meaning                                                                   |
| ----------------- | ----------------------------- | ------------------------------------------------------------------------- |
| `"complete"`      | - | The analysis finished successfully |
| `"error"`         | String message                | The server reported an error during analysis.                             |
| `"disconnected"`  | `None`                        | The SSE connection ended unexpectedly without `"complete"` or `"error"`.  |
| `"network_error"` | Exception message             | A networking problem occurred (e.g., timeout, connection error).          |
| `"error"`         | Exception message             | A generic Python exception was raised while processing the request.       |
| `"error"`         | `"Total timeout for listen"`  | The analysis did not complete within `total_timeout` seconds.             |

After getting a `"complete"` event user can use `track.load_track_data(use_sp_api=False, use_rec_api=False, use_ss_api=True)` to download analyzed data.

## Usage:
Example file usage available at the bottom of the source file - [sp_track_getter.py](sp_track_getter.py)

Example usage when importing as library:
```python
from sp_track_getter import SpTrackGetter
from dotenv import dotenv_values

# Get API keys saved in local .env file
config = dotenv_values(".env")

# Use Spotify and ReccoBeats:
track = SpTrackGetter(
        url="https://open.spotify.com/track/25mgvKnePKbDpStpjy9sT1",
        use_sp_api=True,
        sp_client_id=config["SPOTIFY_CLIENT"],
        sp_client_secret=config["SPOTIFY_SECRET"],
        use_rec_api=True)

track.dump_data()
print(f"Title: {track.data["name"]}")
print(f"Artist: {track.data["artists"][0]["name"]}")
print(f"Album: {track.data["album"]["name"]}")
print(f"YouTube search URL: {track.youtube_search_url}")
if track.rec_audio_features_not_found is False:
    print(f"Track's valence: {track.data["valence"]}")
else:
    print("Track's audio features not found in ReccoBeats")

# Output:
# *track.data dictionary dump*
# Title: Rule #46 - Poet
# Artist: Fish in a Birdcage
# Album: Mentors
# YouTube search URL: https://www.youtube.com/results?search_query=Fish%20in%20a%20Birdcage%20Rule%20%2346%20-%20Poet
# Track's valence: 0.632
```
