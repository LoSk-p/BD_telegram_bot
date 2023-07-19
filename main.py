from config.config import TG_TOKEN, SENDING_TIME, CHECK_INTERVAL_SECONDS
from sql import DataDB

import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, date
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
db = DataDB()

async def send_material(context: ContextTypes.DEFAULT_TYPE, material: list, chat_id: str):
    text_message = ""
    if material["caption"] is not None:
        text_message += f"<b>{material['caption']}</b>\n\n"
    if material["text"] is not None:
        text_message += material["text"]
    if material["file"] is not None:
        await context.bot.send_document(chat_id=chat_id, document=material["file"], filename=material["filename"], caption=text_message, parse_mode=ParseMode.HTML)
        text_message = None
    if material["picture"] is not None:
        await context.bot.send_photo(chat_id=chat_id, photo=material["picture"], caption=text_message, parse_mode=ParseMode.HTML)
    if material["file"] is None and material["picture"] is None:
        await context.bot.send_message(chat_id=chat_id, text=text_message, parse_mode=ParseMode.HTML)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")
    db.add_user(update.effective_chat.id)

async def get_all_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    materials = db.get_last_materials()
    for material in materials:
        await send_material(context, material, update.effective_chat.id)

async def get_last_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    materials = db.get_last_materials(1)
    for material in materials:
        await send_material(context, material, update.effective_chat.id)

async def callback_interval(context):
    logging.info(f"Callback interval for sending time: {SENDING_TIME}")
    delta = datetime.combine(date(1,1,1), SENDING_TIME) - datetime.combine(date(1,1,1), datetime.now().time())
    if delta.days == 0 and delta.seconds <= CHECK_INTERVAL_SECONDS:
        logging.info(f"Message will be sent after {delta.seconds/60} minutes")
        await asyncio.sleep(delta.seconds)
        for message in db.get_not_sent():
            for user in db.get_users():
                await send_material(context, message, user)
            db.set_sent(message["number"])

# async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

# async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     print(f"Context: {context}")
#     print(f"Context args: {context.args}")
#     text_caps = ' '.join(context.args).upper()
#     await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TG_TOKEN).build()
    job_queue = application.job_queue

    job_minute = job_queue.run_repeating(callback_interval, interval=CHECK_INTERVAL_SECONDS, first=10)
    
    start_handler = CommandHandler('start', start)
    get_all_handler = CommandHandler('get_all', get_all_materials)
    get_last_handler = CommandHandler('get_last', get_last_materials)
    # echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    # caps_handler = CommandHandler('caps', caps)
    
    application.add_handler(start_handler)
    application.add_handler(get_all_handler)
    application.add_handler(get_last_handler)
    # application.add_handler(echo_handler)
    # application.add_handler(caps_handler)

    application.run_polling()