# main.py
import os
import threading
import time
from datetime import datetime, timedelta

import schedule
from flask import Flask, json, request
from pyngrok import ngrok
from webexteamssdk import WebexTeamsAPI, Webhook

# Import our own modules
import config
import database

# --- FLASK & WEBEX API INITIALIZATION ---

app = Flask(__name__)
api = WebexTeamsAPI(access_token=config.WEBEX_BOT_TOKEN)


# --- WEBHOOK HANDLING ---

@app.route('/webex-webhook', methods=['POST'])
def webex_webhook():
    """
    Receives and processes incoming Webex messages.
    """
    if request.method == 'POST':
        # Get the message details from the webhook payload
        webhook_obj = Webhook(request.json)
        
        # Ignore messages sent by the bot itself
        if webhook_obj.data.personId == config.WEBEX_BOT_ID:
            return 'OK'

        # Log the incoming message for debugging
        print("WEBHOOK RECEIVED:")
        print(webhook_obj)

        # Get the actual message content
        message = api.messages.get(webhook_obj.data.id)
        
        # --- STATUS COLLECTION LOGIC ---
        # If the message is in the designated stand-up room, save it as a status
        if message.roomId == config.STANDUP_SPACE_ID:
            print(f"Status received from {message.personEmail}")
            database.add_status(
                person_email=message.personEmail,
                status_text=message.text,
                message_id=message.id
            )

        # --- COMMAND HANDLING LOGIC ---
        # Check if the bot is mentioned and parse for commands
        if message.text.startswith(config.WEBEX_BOT_EMAIL):
            command = message.text.replace(config.WEBEX_BOT_EMAIL, '').strip()
            
            # Help command
            if command.lower() == 'help':
                send_help_message(message.roomId)
            
            # Reminder command
            elif command.lower().startswith('remind'):
                handle_reminder_command(command, message.roomId, message.personEmail)

        return 'OK'

def send_help_message(room_id):
    """Sends a help message to the specified room."""
    help_text = """
**Repo Man Help**

I am a bot for collecting daily statuses and sending reminders.

**Commands:**
*   `help`: Shows this help message.
*   `remind in [room_name] about "[reminder_text]" on YYYY-MM-DD at HH:MM`: Sets a reminder. 
    *   `[room_name]` is the name of the room to send the reminder to.
    *   `"[reminder_text]"` must be in quotes.
    *   Example: `remind in General about "Project Demo" on 2026-04-15 at 14:30`

To provide your daily status, simply post a message in the designated stand-up channel after I ask.
"""
    api.messages.create(roomId=room_id, markdown=help_text)

def handle_reminder_command(command: str, room_id: str, created_by: str):
    """Parses and adds a reminder from a command string."""
    # This is a very basic parser and could be improved with regex
    try:
        parts = command.split('"')
        reminder_text = parts[1]
        
        meta_parts = parts[0].replace('remind in', '').strip().split(' about ')[0]
        room_name = meta_parts.strip()

        date_str = command.split(' on ')[1].strip()
        remind_at = datetime.strptime(date_str, '%Y-%m-%d at %H:%M')

        # Find the room ID for the given room name
        target_room_id = None
        rooms = api.rooms.list()
        for r in rooms:
            if r.title == room_name:
                target_room_id = r.id
                break
        
        if not target_room_id:
            api.messages.create(roomId=room_id, text=f"Error: Could not find a room named '{room_name}'.")
            return

        # Add reminder to the database
        database.add_reminder(created_by, target_room_id, reminder_text, remind_at)
        api.messages.create(roomId=room_id, text=f"OK, I will remind the '{room_name}' room on {remind_at.strftime('%Y-%m-%d at %H:%M')}.")

    except Exception as e:
        print(f"Error parsing reminder: {e}")
        api.messages.create(roomId=room_id, text="Sorry, I couldn't understand that reminder format. Please use the format: `remind in [room_name] about \"[text]\" on YYYY-MM-DD at HH:MM`")


# --- SCHEDULED JOBS ---

def ask_for_standup():
    """Posts the daily stand-up question to the configured Webex space."""
    print(f"Posting stand-up question to space ID: {config.STANDUP_SPACE_ID}")
    try:
        api.messages.create(
            roomId=config.STANDUP_SPACE_ID,
            markdown=config.STANDUP_MESSAGE
        )
        print("Stand-up question posted successfully.")
    except Exception as e:
        print(f"Error posting stand-up question: {e}")
        # Optionally, notify the admin of the failure
        try:
            api.messages.create(toPersonEmail=config.ADMIN_EMAIL, text=f"Error: Could not post the stand-up message to the configured space. Please check if the bot is in the room and the STANDUP_SPACE_ID is correct. Details: {e}")
        except Exception as admin_e:
            print(f"Failed to send error notification to admin: {admin_e}")


def send_summary_report():
    """Generates and sends the daily status summary to the admin."""
    print("Generating and sending summary report...")
    statuses = database.get_statuses_for_today()
    
    if not statuses:
        summary = "No status updates were collected today."
    else:
        summary = "**Daily Status Summary**\n\n"
        current_person = ""
        for person_email, status_text in statuses:
            if person_email != current_person:
                summary += f"\n--- **{person_email}** ---\n"
                current_person = person_email
            summary += f"- {status_text}\n"
            
    try:
        api.messages.create(
            toPersonEmail=config.ADMIN_EMAIL,
            markdown=summary
        )
        print("Summary report sent successfully.")
    except Exception as e:
        print(f"Error sending summary report: {e}")


def check_reminders():
    """Checks for due reminders and sends them."""
    due_reminders = database.get_due_reminders()
    if due_reminders:
        print(f"Found {len(due_reminders)} due reminders.")
        for rem_id, room_id, text in due_reminders:
            try:
                api.messages.create(
                    roomId=room_id,
                    markdown=f"**Reminder:** {text}"
                )
                database.mark_reminder_as_sent(rem_id)
                print(f"Sent reminder ID {rem_id} to room {room_id}")
            except Exception as e:
                print(f"Error sending reminder ID {rem_id}: {e}")


# --- SCHEDULER & SERVER STARTUP ---

def run_scheduler():
    """Runs the scheduled jobs in a loop."""
    print("Scheduler started.")
    # Define the schedule
    schedule.every().day.at(config.STANDUP_TIME).do(ask_for_standup)
    schedule.every().day.at(config.SUMMARY_TIME).do(send_summary_report)
    schedule.every().minute.do(check_reminders)

    while True:
        schedule.run_pending()
        time.sleep(1)

def setup_webhook():
    """Deletes old webhooks and creates a new one for our bot."""
    print("Setting up Webex webhook...")
    try:
        # Clean up any existing webhooks
        for webhook in api.webhooks.list():
            if webhook.name == 'Repo Man Webhook':
                print(f"Deleting old webhook: {webhook.id}")
                api.webhooks.delete(webhook.id)

        # Create the new webhook
        webhook = api.webhooks.create(
            name='Repo Man Webhook',
            targetUrl=config.WEBHOOK_URL + '/webex-webhook',
            resource='messages',
            event='created'
        )
        print("Webhook created successfully:")
        print(webhook)
    except Exception as e:
        print(f"Error setting up webhook: {e}")
        # This is a critical failure, so we should probably exit.
        exit()

if __name__ == '__main__':
    # 1. Initialize the database
    print("--- Initializing Database ---")
    database.init_db()

    # 2. Set up the public URL with ngrok if no URL is in the config
    if not config.WEBHOOK_URL or 'ngrok.io' in config.WEBHOOK_URL:
        print("--- Starting ngrok Tunnel ---")
        # This assumes you have ngrok installed and authenticated.
        # It will open a tunnel to port 5000, where Flask is running.
        public_url = ngrok.connect(5000)
        # Update the config in memory with the new URL
        config.WEBHOOK_URL = public_url
        print(f"Ngrok tunnel established. Public URL: {config.WEBHOOK_URL}")
        print("IMPORTANT: You must copy this URL into your config.py file if you restart the bot.")
    
    # 3. Set up the Webex webhook
    print("\n--- Setting up Webex Webhook ---")
    setup_webhook()

    # 4. Start the scheduler in a background thread
    print("\n--- Starting Scheduler ---")
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # 5. Start the Flask web server
    print("\n--- Starting Flask Web Server ---")
    print("The bot is now running. Press Ctrl+C to exit.")
    app.run(host='0.0.0.0', port=5000)
