"""

Sample bot that echoes back messages.

This is the simplest possible bot and a great place to start if you want to build your own bot.

"""
from __future__ import annotations

from typing import AsyncIterable

from fastapi_poe import PoeBot, run
from fastapi_poe.types import QueryRequest
from fastapi_poe.client import MetaMessage, stream_request
from sse_starlette.sse import ServerSentEvent
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import json


GENRES = ['acoustic', 'afrobeat', 'alt-rock', 'alternative', 'ambient', 'anime', 'black-metal', 'bluegrass', 'blues', 'bossanova', 'brazil', 'breakbeat', 'british', 'cantopop', 'chicago-house', 'children', 'chill', 'classical', 'club', 'comedy', 'country', 'dance', 'dancehall', 'death-metal', 'deep-house', 'detroit-techno', 'disco', 'disney', 'drum-and-bass', 'dub', 'dubstep', 'edm', 'electro', 'electronic', 'emo', 'folk', 'forro', 'french', 'funk', 'garage', 'german', 'gospel', 'goth', 'grindcore', 'groove', 'grunge', 'guitar', 'happy', 'hard-rock', 'hardcore', 'hardstyle', 'heavy-metal', 'hip-hop', 'holidays', 'honky-tonk', 'house', 'idm', 'indian', 'indie', 'indie-pop', 'industrial', 'iranian', 'j-dance', 'j-idol', 'j-pop', 'j-rock', 'jazz', 'k-pop', 'kids', 'latin', 'latino', 'malay', 'mandopop', 'metal', 'metal-misc', 'metalcore', 'minimal-techno', 'movies', 'mpb', 'new-age', 'new-release', 'opera', 'pagode', 'party', 'philippines-opm', 'piano', 'pop', 'pop-film', 'post-dubstep', 'power-pop', 'progressive-house', 'psych-rock', 'punk', 'punk-rock', 'r-n-b', 'rainy-day', 'reggae', 'reggaeton', 'road-trip', 'rock', 'rock-n-roll', 'rockabilly', 'romance', 'sad', 'salsa', 'samba', 'sertanejo', 'show-tunes', 'singer-songwriter', 'ska', 'sleep', 'songwriter', 'soul', 'soundtracks', 'spanish', 'study', 'summer', 'swedish', 'synth-pop', 'tango', 'techno', 'trance', 'trip-hop', 'turkish', 'work-out', 'world-music']

g_alias = {
    'r&b': 'r-n-b'
}

PROMPT_FORMAT =  """
You are given a user prompt asking for music recommendations:
<prompt>
{prompt}
</prompt>

You should recommend music genres and artists that best match the prompt above in JSON format with the following attributes:

- "title": string short title for a playlist with the recommendations 
- "summary": string with the explanation for the recommendations inspired by the user prompt and a suggestion for the playlist title.
- "artist": array with at most 3 strings with names of artists or bands recommended, if the prompt references any artists, use them.
- "genre": array with at most 3 strings with music genres recommended, genres must be verbatim from the list: {genres}.
- "n": integer denoting the number of musics to recommend, in case the prompt specifies the amount of musics to recommend, otherwise use the default of 10

Your response should be a valid JSON, don't provide any other text than the JSON.
"""

BOT = "claude-instant"

def parse_genres(genres: list[str]) -> list[str]:
    genres = [genre.strip('\'\"') for genre in genres]
    gs = []
    for g in genres:
        g = g.lower()
        g = g.replace(' ', '-')
        g = g_alias.get(g, g)
        if g in GENRES:
            gs.append(g)
        else:
            print(f"Could not find genre {g}, ignoring it!")
    return gs

def get_artists_url(sp: spotipy.Spotify, artists: list[str]) -> list[str]:
    urls = []
    for artist in artists:
        res = sp.search(f'artist:{artist}', type="artist")['artists']['items']
        if res:
            urls.append(res[0]['external_urls']['spotify'])
    print(f"Urls: {urls}")
    return urls

class EchoBot(PoeBot):
    async def get_response(self, query: QueryRequest) -> AsyncIterable[ServerSentEvent]:
        spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
        response = ""
        prompt = query.query[-1].content
        print(f"user prompt: {prompt}")
        query.query[-1].content = PROMPT_FORMAT.format(prompt=prompt, genres=GENRES)
        async for msg in stream_request(query, BOT, query.api_key):
            if isinstance(msg, MetaMessage):
                continue
            elif msg.is_suggested_reply:
                #yield self.suggested_reply_event(msg.text)
                continue
            elif msg.is_replace_response:
                #yield self.replace_response_event(msg.text)
                continue
            else:
                response += msg.text
                #yield self.text_event(msg.text)
        print(f"res: '{response}'")
        json_res = json.loads(response.strip())
        summary = json_res.get('summary', "")
        artists = json_res.get('artist', [])
        genres = json_res.get('genre', [])
        title = json_res.get('title', "")
        n = json_res['n']
        print(f"sum: {summary}")
        print(f"art {artists}")
        print(f"gen {genres}")
        print(f"title {title}")
        print(f"n {n}")

        yield self.text_event(f"\n{summary}\nPlaylist '{title}':\n")
        art_urls = get_artists_url(spotify, artists)
        genres = parse_genres(genres)
        
        rec = spotify.recommendations(seed_genres=parse_genres(genres), seed_artists=art_urls, limit=n)
        musics = []
        for track in rec['tracks']:
            artists = ", ".join(artist['name'] for artist in track['artists'])
            music_name = track['name']
            url = track['external_urls']['spotify']
            musics.append(f"- [{music_name}]({url}) by {artists}")

        yield self.text_event("\n".join(musics))
if __name__ == "__main__":
    run(EchoBot())
