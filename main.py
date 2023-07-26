from asyncio.log import logger
from email.charset import add_charset
from config.config import TG_TOKEN, SENDING_TIME, CHECK_INTERVAL_SECONDS, ADMINS
from sql import DataDB

from urllib.request import urlopen
import base64
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import ParseMode, MenuButtonType
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler
from datetime import datetime, date
import asyncio

ADMIN_MENU = 1
ADD_MATERIAL_MENU = 2
DELETE_MATERIAL_MENU = 3

ADD_CAPTURE = "Add capture"
ADD_TEXT = "Add text"
ADD_FILE = "Add file"
ADD_FILENAME = "Add the name of the file"
ADD_PICTURE = "Add picture"
FINISH_ADD_MATERIAL = "Finish"

GET_TEXT = False
GET_CAPTURE = False
GET_PICTURE = False
GET_FILE = False
GET_FILENAME = False

GET_ALL = "Get all materials"
GET_LAST = "Get last material"
UNSUBSCRIBE = "Unsubscribe"
ADMIN_TOOLS = "Admin Tools"
ADD_MATERIAL = "Add material"
DELETE_MATERIAL = "Delete material"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
db = DataDB()

def get_markup(user_id) -> ReplyKeyboardMarkup:
    if str(user_id) in ADMINS:
        menu_main = [[InlineKeyboardButton(GET_ALL)],
                    [InlineKeyboardButton(GET_LAST)],
                    [InlineKeyboardButton(UNSUBSCRIBE)],
                    [InlineKeyboardButton(ADMIN_TOOLS)]]
    else:
        menu_main = [[InlineKeyboardButton(GET_ALL)],
                    [InlineKeyboardButton(GET_LAST)],
                    [InlineKeyboardButton(UNSUBSCRIBE)]]
    return ReplyKeyboardMarkup(menu_main)

async def send_material(context: ContextTypes.DEFAULT_TYPE, material: list, chat_id: str):
    reply_markup = get_markup(chat_id)
    text_message = ""
    if material["caption"] is not None:
        text_message += f"<b>{material['caption']}</b>\n\n"
    if material["text"] is not None:
        text_message += material["text"]
    if material["file"] is not None:
        await context.bot.send_document(chat_id=chat_id, document=material["file"], filename=material["filename"], caption=text_message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        text_message = None
    if material["picture"] is not None:
        await context.bot.send_photo(chat_id=chat_id, photo=material["picture"], caption=text_message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    if material["file"] is None and material["picture"] is None:
        await context.bot.send_message(chat_id=chat_id, text=text_message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = get_markup(update.effective_chat.id)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="You've subscribed to sheduled messages", reply_markup=reply_markup)
    db.add_user(update.effective_chat.id)

async def get_all_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    materials = db.get_last_materials()
    for material in materials:
        await send_material(context, material, update.effective_chat.id)

async def get_last_materials(update: Update, context: ContextTypes.DEFAULT_TYPE):
    materials = db.get_last_materials(1)
    for material in materials:
        await send_material(context, material, update.effective_chat.id)

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.delete_user(str(update.effective_chat.id))
    await context.bot.send_message(chat_id=update.effective_chat.id, text="You will not see sheduled messages. To subscribe again write /start", reply_markup=get_markup())

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

async def add_material_capture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GET_CAPTURE
    GET_CAPTURE = True
    await update.callback_query.edit_message_text("Write the capture")

async def add_material_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GET_TEXT
    GET_TEXT = True
    await update.callback_query.edit_message_text("Write the text")

async def add_material_picture(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GET_PICTURE
    GET_PICTURE = True
    await update.callback_query.edit_message_text("Attach the picture")

async def add_material_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GET_FILE
    GET_FILE = True
    await update.callback_query.edit_message_text("Attach the file")

async def add_material_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GET_FILENAME
    GET_FILENAME = True
    await update.callback_query.edit_message_text("Write the name for the file")

async def finish_add_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Finish add")
    db.add_material()
    await update.callback_query.edit_message_text("Material was added")

def get_add_material_menu() -> InlineKeyboardMarkup:
    menu = [[InlineKeyboardButton(ADD_CAPTURE, callback_data=ADD_CAPTURE)],
                    [InlineKeyboardButton(ADD_TEXT, callback_data=ADD_TEXT)],
                    [InlineKeyboardButton(ADD_FILE, callback_data=ADD_FILE)],
                    [InlineKeyboardButton(ADD_FILENAME, callback_data=ADD_FILENAME)],
                    [InlineKeyboardButton(ADD_PICTURE, callback_data=ADD_PICTURE)],
                    [InlineKeyboardButton(FINISH_ADD_MATERIAL, callback_data=FINISH_ADD_MATERIAL)]]
    return InlineKeyboardMarkup(menu)

async def add_material_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("Add you material", reply_markup=get_add_material_menu())

async def delete_material_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    materials = db.get_last_materials()
    menu = []
    for material in materials:
        menu.append([InlineKeyboardButton(f"{material['number']} - {material['caption']}", callback_data=f"material_{material['number']}")])
    await update.callback_query.edit_message_text("What material do you want to delete?", reply_markup=InlineKeyboardMarkup(menu))

async def delete_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    material_number = update.callback_query.data.split("_")[-1]
    db.delete_material(int(material_number))
    await update.callback_query.edit_message_text("Material was deleted")

async def admin_tools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_admin = [[InlineKeyboardButton(ADD_MATERIAL, callback_data=ADD_MATERIAL)],
                    [InlineKeyboardButton(DELETE_MATERIAL, callback_data=DELETE_MATERIAL)]]
    reply_markup = InlineKeyboardMarkup(menu_admin)
    await update.message.reply_text("What do you want to do?", reply_markup=reply_markup)

async def text_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GET_CAPTURE
    global GET_TEXT
    global GET_FILE
    global GET_FILENAME
    global GET_PICTURE
    if GET_CAPTURE:
        db.update_material(caption=update.message.text)
        await update.message.reply_text("Add your material", reply_markup=get_add_material_menu())
        GET_CAPTURE = False
    elif GET_TEXT:
        db.update_material(text=update.message.text)
        await update.message.reply_text("Add your material", reply_markup=get_add_material_menu())
        GET_TEXT = False
    elif GET_FILE:
        file_id = await context.bot.get_file(update.message.document.file_id)
        file_url = file_id.file_path
        with urlopen(file_url) as url:
            file_data = url.read()
        db.update_material(file=file_data)
        if db.material_data.filename is None:
            db.update_material(filename=update.message.document.file_name)
        await update.message.reply_text("Add your material", reply_markup=get_add_material_menu())
        GET_FILE = False
    elif GET_FILENAME:
        db.update_material(filename=update.message.text)
        await update.message.reply_text("Add your material", reply_markup=get_add_material_menu())
        GET_FILENAME = False
    elif GET_PICTURE:
        pic = await context.bot.get_file(update.message.photo[-1].file_id)
        picture_url = pic.file_path
        with urlopen(picture_url) as url:
            picture_data = url.read()
        db.update_material(picture=picture_data)
        await update.message.reply_text("Add your material", reply_markup=get_add_material_menu())
        GET_PICTURE = False
    if update.message.text == GET_ALL:
        await get_all_materials(update, context)
    elif update.message.text == GET_LAST:
        await get_last_materials(update, context)
    elif update.message.text == UNSUBSCRIBE:
        await unsubscribe(update, context)
    elif update.message.text == ADMIN_TOOLS and str(update.effective_chat.id) in ADMINS:
        await admin_tools(update, context)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TG_TOKEN).build()
    job_queue = application.job_queue

    job_minute = job_queue.run_repeating(callback_interval, interval=CHECK_INTERVAL_SECONDS, first=10)
    
    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler((~filters.COMMAND), text_manager)
    add_material_handler = CallbackQueryHandler(add_material_start, pattern=ADD_MATERIAL)
    add_material_picture_handler = CallbackQueryHandler(add_material_picture, pattern=ADD_PICTURE)
    add_material_text_handler = CallbackQueryHandler(add_material_text, pattern=ADD_TEXT)
    add_material_capture_handler = CallbackQueryHandler(add_material_capture, pattern=ADD_CAPTURE)
    add_material_file_handler = CallbackQueryHandler(add_material_file, pattern=ADD_FILE)
    add_material_filename_handler = CallbackQueryHandler(add_material_filename, pattern=ADD_FILENAME)
    add_material_finish_handler = CallbackQueryHandler(finish_add_material, pattern=FINISH_ADD_MATERIAL)
    delete_material_start_handler = CallbackQueryHandler(delete_material_start, pattern=DELETE_MATERIAL)
    delete_material_handler = CallbackQueryHandler(delete_material, pattern="material_.")
    
    application.add_handler(start_handler)
    application.add_handler(echo_handler)
    application.add_handler(add_material_handler)
    application.add_handler(add_material_capture_handler)
    application.add_handler(add_material_picture_handler)
    application.add_handler(add_material_text_handler)
    application.add_handler(add_material_file_handler)
    application.add_handler(add_material_filename_handler)
    application.add_handler(add_material_finish_handler)
    application.add_handler(delete_material_start_handler)
    application.add_handler(delete_material_handler)

    application.run_polling()