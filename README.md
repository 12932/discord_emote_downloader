# Discord Emote Downloader

Quickly download all available Discord emotes and Stickers from Guilds/servers available to your account. Emotes are downloaded into a directory called "emotes" and stickers "stickers". Emote and sticker names are preserved, but emote id appended. e.g. `LuLe_89237897293847.png`

# Installation

## Via pip
```
pip install -r requirements.txt
```

## Via [uv](https://github.com/astral-sh/uv)
```
uv venv && uv pip install -r requirements.txt
```

# Usage

## Standard
```
python3 discord_emote_downloader.py
```

## Via [uv](https://github.com/astral-sh/uv)

```
uv run discord_emote_downloader.py
```