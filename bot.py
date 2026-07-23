import os
import sys
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from anthropic import Anthropic

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

relevant_keys = ["TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY"]
logger.info("Checking environment variables...")
for key in relevant_keys:
    status = "SET" if os.environ.get(key) else "MISSING"
    logger.info(f"  {key}: {status}")


def get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        logger.error(
            f"Missing required environment variable: {name}. "
            f"Go to Railway -> your service -> Variables tab, add it, then redeploy."
        )
        sys.exit(1)
    return value


TELEGRAM_TOKEN = get_required_env("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY = get_required_env("ANTHROPIC_API_KEY")

client = Anthropic(api_key=ANTHROPIC_API_KEY)

conversations = {}
MAX_HISTORY = 10


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! I'm ChatMateDaoBot 🤖\n"
        "Send me any message and I'll respond. Use /reset to clear our conversation."
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversations.pop(chat_id, None)
    await update.message.reply_text("Conversation history cleared.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_message = update.message.text

    history = conversations.get(chat_id, [])
    history.append({"role": "user", "content": user_message})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1000,
            messages=history,
        )
        reply_text = response.content[0].text
    except Exception as e:
        logger.error(f"API error: {e}")
        await update.message.reply_text(
            "Sorry, something went wrong generating a response. Try again in a moment."
        )
        return

    history.append({"role": "assistant", "content": reply_text})
    conversations[chat_id] = history[-MAX_HISTORY:]

    await update.message.reply_text(reply_text)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
