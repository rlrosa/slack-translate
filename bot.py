from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from googletrans import Translator
import logging
import os
import re

# logging for all modules
logging.basicConfig(level=logging.INFO)
# now logging for my app
if os.environ.get("FLASK_DEBUG"):
    level=logging.DEBUG
    logger.info(f'Log level: {level}')
else:
    level=logging.INFO
logger = logging.getLogger("TranslateBot")
logger.setLevel(level)

app = Flask(__name__)

# Initialize Slack client and translator
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
client = WebClient(token=slack_bot_token)
translator = Translator()

CODEBLOCK = "c0d3bl0ck"
INLINECODE = "1nl1n3c0d3"

def clean_slack_formatting(text):
    # Step 1: Extract code blocks and inline code and eplace them with
    #         placeholders. Use funky stuff so translator does not pickup on
    #         them and leaves them unmodified.
    #         First do code blocks to avoid confusion.
    code_blocks = re.findall(r"```.*?```", text, re.DOTALL)
    for i, block in enumerate(code_blocks):
        logger.debug(f'Code block {i}: {block}')
        text = text.replace(block, f"{CODEBLOCK}{i}")

    inline_code = re.findall(r"`[^`]+`", text)
    for i, code in enumerate(inline_code):
        logger.debug(f'Code inline {i}: {code}')
        text = text.replace(code, f"{INLINECODE}{i}")

    # Step 2: Strip Slack markdown (bold, italic, strikethrough)
    text = re.sub(r"[*_~]", "", text)

    return text, code_blocks, inline_code

def restore_code(text, code_blocks, inline_code):
    # Step 3: Restore code. Ignore case since it can get lost in translation
    for i, block in enumerate(code_blocks):
        text = re.sub(f"{CODEBLOCK}{i}", block, text, flags=re.IGNORECASE)
    for i, code in enumerate(inline_code):
        text = re.sub(f"{INLINECODE}{i}", block, text, flags=re.IGNORECASE)
    return text

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json

    # Respond to Slack URL verification challenge
    if data.get("type") == "url_verification":
        return jsonify({"challenge": data.get("challenge")})

    # Handle event callbacks
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        user = event.get("user")
        text = event.get("text")
        subtype = event.get("subtype")
        channel = event.get("channel")
        thread_ts = event.get("ts")

        # Ignore bot messages and messages without text
        ignore_message = \
            subtype == "bot_message" or \
            not text or \
            not user or \
            event.get("bot_id") or \
            event.get("bot_profile") or \
            event.get("app_id")
        if ignore_message:
            logger.debug("Ignoring msg")
            return "", 200

        # Detect language and translate
        detected = translator.detect(text)
        lang = detected.lang

        cleaned_text, code_blocks, inline_code = clean_slack_formatting(text)

        if lang == "en":
            dest = "zh-cn"
        elif lang.lower() in ["zh-cn", "zh-cn"]:
            dest = "en"
        else:
            logger.debug(f"Ignoring detected language: {lang}")
            return "", 200  # Ignore other languages
        translated_text = translator.translate(cleaned_text, dest=dest).text

        final_text = restore_code(translated_text, code_blocks, inline_code)

        # Format the message
        formatted_message = ''
        if len(text) < 50:
            formatted_message += f"*Original:*\n{text}\n\n"
        formatted_message += f"*Translation:*\n{final_text}"

        # Post translated message in thread
        try:
            client.chat_postMessage(
                channel=channel,
                text=formatted_message,
                thread_ts=thread_ts
            )
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")

    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

