# list_rooms.py
import config
from webexteamssdk import WebexTeamsAPI

try:
    api = WebexTeamsAPI(access_token=config.WEBEX_BOT_TOKEN)
    rooms = api.rooms.list()

    print("Found rooms the bot is in:")
    print("-" * 30)
    
    if not rooms:
        print("The bot is not in any rooms yet.")
    else:
        for room in rooms:
            print(f"Room Title: '{room.title}'")
            print(f"Room ID: {room.id}")
            print("-" * 30)

except Exception as e:
    print(f"An error occurred: {e}")
    print("Please ensure your WEBEX_BOT_TOKEN in config.py is correct.")

