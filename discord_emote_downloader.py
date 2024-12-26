import httpx
from queue import Queue
import threading
from alive_progress import alive_bar
import os
import time
from dataclasses import dataclass
from enum import Enum
import argparse
from dotenv import load_dotenv
import getpass

DISCORD_ENDOPINT = "https://discordapp.com/api/v8/"
ALL_GUILD_ENDPOINT = "https://discordapp.com/api/v8/users/@me/guilds"
GUILD_EMOJI_ENDPOINT = "https://discordapp.com/api/v8/guilds/{}/emojis" 

EMOJI_ENDPOINT = "https://cdn.discordapp.com/emojis/{}.{}"
STICKER_ENDPOINT = "https://media.discordapp.net/stickers/{}.{}"
GUILD_STICKER_ENDPOINT = "https://discord.com/api/v9/guilds/{}/stickers"

INCONSPICUOUS_HEADERS = {
	'authority': 'discord.com',
	'accept-language': 'en-US',
	'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9173 Chrome/128.0.6613.186 Electron/32.2.2 Safari/537.36',
	'accept': '*/*',
}

TIMEOUTS = (9, 17)
REQ_SESSION = httpx.Client(headers=INCONSPICUOUS_HEADERS, timeout=TIMEOUTS)

DOWNLOAD_QUEUE = Queue()
DOWNLOAD_THREAD_COUNT = 16

EMOTES_DIR = "./emotes"
STICKERS_DIR = "./stickers"

# Define an Enum for the emote type
class EmoteType(Enum):
	EMOJI = 'emoji'
	STICKER = 'sticker'

@dataclass
class DownloadItem:
	type: EmoteType
	data: dict

# removes all characters that are illegal in windows filenames and all emojis
def sanitise_string(text):
	# Define a function to check if a character is an emoji
	def is_emoji(char):
		return (
			'\U0001F600' <= char <= '\U0001F64F' or  # emoticons
			'\U0001F300' <= char <= '\U0001F5FF' or  # symbols & pictographs
			'\U0001F680' <= char <= '\U0001F6FF' or  # transport & map symbols
			'\U0001F1E0' <= char <= '\U0001F1FF' or  # flags (iOS)
			'\U00002702' <= char <= '\U000027B0' or  # dingbats
			'\U000024C2' <= char <= '\U0001F251'
		)

	# Remove illegal characters for Windows filenames and emojis
	sanitized_text = ''.join(
		c for c in text
		if c not in r"\/?:<>*|#,\"" and not is_emoji(c)
	)
	
	return sanitized_text

def download_and_save_emoji(jsondata):
	name = jsondata['name']	
	emoji_id = jsondata['id']	
	gif = jsondata['animated']

	extension = "gif" if gif else "png"

	image_req = REQ_SESSION.get(EMOJI_ENDPOINT.format(emoji_id, extension))
	image_req.raise_for_status()
	filename = f"{name}_{emoji_id}.{extension}"
	filename = sanitise_string(filename)

	# Ensure the directory exists
	os.makedirs(EMOTES_DIR, exist_ok=True)

	with open(f"{EMOTES_DIR}/{filename}", "wb") as emoji_file:
		emoji_file.write(image_req.content)

def download_and_save_sticker(jsondata):
	name = jsondata['name']
	sticker_id = jsondata['id']
	format_type = jsondata['format_type']

	# Determine the file extension based on the format_type
	extension_map = {1: "png", 2: "png", 3: "json", 4: "gif"}
	extension = extension_map.get(format_type, "png")

	# Use a different endpoint for LOTTIE stickers
	if format_type == 3:
		image_req = REQ_SESSION.get(f"https://discord.com/stickers/{sticker_id}.json")
	else:
		# Request as .png but save as .apng if it's an animated PNG
		image_req = REQ_SESSION.get(STICKER_ENDPOINT.format(sticker_id, extension))
	
	image_req.raise_for_status()
	
	# Save as .apng if it's an animated PNG
	if format_type == 2:
		extension = "apng"
	
	filename = f"{name}_{sticker_id}.{extension}"
	filename = sanitise_string(filename)

	# Ensure the directory exists
	os.makedirs(STICKERS_DIR, exist_ok=True)

	with open(f"{STICKERS_DIR}/{filename}", "wb") as sticker_file:
		sticker_file.write(image_req.content)

def download_worker(bar):
	while not DOWNLOAD_QUEUE.empty():
		item = DOWNLOAD_QUEUE.get()
		try:
			if item.type == EmoteType.EMOJI:
				download_and_save_emoji(item.data)
			elif item.type == EmoteType.STICKER:
				download_and_save_sticker(item.data)
		finally:
			DOWNLOAD_QUEUE.task_done()
			bar()

def main(guild_id=None):
	load_dotenv()
	DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

	if not DISCORD_TOKEN:
		# Securely prompt for the token if not found in the .env file
		DISCORD_TOKEN = getpass.getpass("Enter your Discord token:\n")
	
	INCONSPICUOUS_HEADERS.update({'authorization': DISCORD_TOKEN})

	if guild_id:
		guilds = [{'id': guild_id}]
	else:
		all_guilds = REQ_SESSION.get(ALL_GUILD_ENDPOINT.format())
		try:
			all_guilds.raise_for_status()
		except Exception:
			print("Failed to list guilds. Your token is likely incorrect, please check it and try again.")
			exit(1)
		guilds = all_guilds.json()

	with alive_bar(len(guilds), title="Processing Guilds") as guild_bar:
		for guild in guilds:
			# Fetch and download emojis
			emoji_data = REQ_SESSION.get(GUILD_EMOJI_ENDPOINT.format(guild['id']))
			emoji_data.raise_for_status()
			emoji_data_json = emoji_data.json()

			# Add emojis to the download queue
			for single_emoji in emoji_data_json:
				DOWNLOAD_QUEUE.put(DownloadItem(type=EmoteType.EMOJI, data=single_emoji))

			# Fetch and download stickers
			sticker_data = REQ_SESSION.get(GUILD_STICKER_ENDPOINT.format(guild['id']))
			sticker_data.raise_for_status()
			sticker_data_json = sticker_data.json()

			for single_sticker in sticker_data_json:
				DOWNLOAD_QUEUE.put(DownloadItem(type=EmoteType.STICKER, data=single_sticker))

			# Avoid discord rate limits
			time.sleep(1)
			guild_bar()

	# Start download threads for emojis and stickers
	with alive_bar(DOWNLOAD_QUEUE.qsize(), title="Downloading Items") as bar:
		threads = []
		for _ in range(DOWNLOAD_THREAD_COUNT):
			thread = threading.Thread(target=download_worker, args=(bar,))
			thread.start()
			threads.append(thread)

		for thread in threads:
			thread.join()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Download Discord emotes and stickers.")
	parser.add_argument('guild_id', nargs='?', default=None, help='The ID of the guild to download emotes and stickers from.')
	args = parser.parse_args()

	main(guild_id=args.guild_id)