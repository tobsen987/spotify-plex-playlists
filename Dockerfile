FROM python:alpine

ENV SPOTIPY_CLIENT_ID ""
ENV SPOTIPY_CLIENT_SECRET ""
ENV SPOTIPY_GET_ALL_USERS_PL "false"
ENV SPOTIFY_USER ""
ENV PLEX_URL ""
ENV PLEX_TOKEN ""
ENV SPOTIFY_URIS ""
ENV SECONDS_TO_WAIT 1800

ENV HOME="/config"

WORKDIR /app/

COPY spotify-sync.py /app/spotify-sync.py
COPY requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

CMD python spotify-sync.py