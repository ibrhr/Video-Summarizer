from db import setup_database
from telegram.ext import Application
from telegram import BotCommand
from bot.handlers import setup_handlers
import bot.config as config

async def setup_bot_commands(app):
    commands = [
        BotCommand("start", "Start the bot and get help"),
        BotCommand("subscription", "Change your subscription tier"),
    ]
    await app.bot.set_my_commands(commands)

def main():
    app = Application.builder().token(config.BOT_TOKEN).post_init(setup_bot_commands).build()

    setup_database()
    print("📦 Database initialized.")

    setup_handlers(app)
    print("🤖 Bot is running...")

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
