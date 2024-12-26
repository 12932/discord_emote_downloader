# Discord Emote Downloader

Quickly download all available Discord emotes and Stickers from Guilds/servers available to your account. Emotes are downloaded into a directory called "emotes" and stickers "stickers". Emote and sticker names are preserved, but emote id appended. e.g. `LuLe_89237897293847.png`

![image](https://github.com/user-attachments/assets/7dc6cb25-45de-4f53-a804-19bd20203280)


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

# Download emotes/stickers from only a single guild

```
python3 discord_emote_downloader.py guild_id
```