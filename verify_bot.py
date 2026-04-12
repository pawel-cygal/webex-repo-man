# verify_bot.py
import config
from webexteamssdk import WebexTeamsAPI

try:
    api = WebexTeamsAPI(access_token=config.WEBEX_BOT_TOKEN)
    bot_details = api.people.me()

    print("--- Verifying Bot Identity ---")
    print(f"Display Name: {bot_details.displayName}")
    print(f"Email(s): {bot_details.emails}")
    print(f"Bot ID: {bot_details.id}")
    print("------------------------------")
    print("\nPlease use the email address from the 'Email(s)' field above to add the bot to your Webex space.")

except Exception as e:
    print(f"An error occurred while verifying the bot: {e}")
    print("Please double-check the WEBEX_BOT_TOKEN in your config.py file.")

