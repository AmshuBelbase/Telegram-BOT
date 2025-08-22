import os
import json
import requests
from dotenv import load_dotenv
from groq import Groq
import urllib.parse
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from datetime import datetime

# Load environment variables
load_dotenv()

# Telegram Bot Token from environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)
MODEL = 'llama3-70b-8192'

SYSTEM_PROMPT_FILE = "system_prompt.txt"
# QA_LOG_FILE = "qa_log.txt"  # File to store Q&A pairs


def get_system_prompt():
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


# def log_qa(question, answer, user_details):
    # with open(QA_LOG_FILE, "a", encoding="utf-8") as f:
    #     now = datetime.now()
    #     timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    #     f.write(f"Time: {timestamp} User ID: {user_details.id}, Username: {user_details.username}, Name: {user_details.first_name} {user_details.last_name} \nQ: {question} \nA: {answer}\n\n")


def run_conversation(user_prompt):

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %I:%M:%S %p")

    current_time_for_context = "Time at which Question is asked: " + \
        timestamp + ".\n User Prompt: "
    user_prompt = current_time_for_context + user_prompt

    print(user_prompt)

    messages = [
        {
            "role": "system",
            "content": get_system_prompt()},
        {
            "role": "user",
            "content": user_prompt,
        }
    ]

    tools = []
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        max_tokens=4096
    )

    response_message = response.choices[0].message
    # print("Response Message: ", response_message)
    # print("")
    tool_calls = response_message.tool_calls

    if tool_calls:

        available_functions = {}
        messages.append(response_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            if function_name == "get_person_details":
                function_response = function_to_call(
                    person=function_args.get("person")
                )
            elif function_name == "get_place_info":
                function_response = function_to_call(
                    place=function_args.get("place")
                )
            else:
                function_response = function_to_call(
                    team_name=function_args.get("team_name")
                )

            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )
        # print("Message: ", messages)
        second_response = client.chat.completions.create(
            model=MODEL,
            messages=messages
        )
        print("")
        print("Second Response: ", second_response)
        print("")
        answer = second_response.choices[0].message.content
        return answer
    else:
        answer = response_message.content
        return answer


# Function to handle user messages
def handle_message(update: Update, context: CallbackContext):
    user_input = update.message.text
    user = update.message.from_user
    user_id = user.id
    username = user.username
    first_name = user.first_name
    last_name = user.last_name

    print("")

    print(
        f"User ID: {user_id}, Username: {username}, Name: {first_name} {last_name}")

    print("Q: ", user_input)
    response_message = run_conversation(user_input)
    print("A: ", response_message)
    update.message.reply_text(response_message)
    # log_qa(user_input, response_message, user)


# Function to start the bot


def start(update: Update, context: CallbackContext):
    print("Received start")
    update.message.reply_text(
        'Hello! I am your Telegram chatbot. How can I assist you today?')


def main():
    # Create the Updater and pass it your bot's token
    print("Start Program")
    updater = Updater(TELEGRAM_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Command handler for /start
    dp.add_handler(CommandHandler("start", start))

    # Message handler for regular text messages
    dp.add_handler(MessageHandler(Filters.text & ~
                   Filters.command, handle_message))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you send a signal to stop it
    updater.idle()


if __name__ == "__main__":
    main()
