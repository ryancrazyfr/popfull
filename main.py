
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram import Update, ChatPermissions
import os
import json
import re
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread

BOT_TOKEN = os.environ['BOT_TOKEN']
GOOGLE_JSON = os.environ['GOOGLE_JSON']
SHEET_NAME = "POP Submissions"
DRIVE_FOLDER_ID = "1GvJdGDW7ZZPTyhbxNW-W9P1J94unyGvp"
ADMIN_USER_ID = 6276794389
POP_DIR = "pop_submissions"
SELLERS_FILE = "sellers.json"
GROUP_IDS = [
    -1001906279445,
    -1001623432634,
    -1001821941202,
    -1001923306291,
    -1001709491100
]

if not os.path.exists(POP_DIR):
    os.makedirs(POP_DIR)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_JSON)
sheets_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(sheets_creds)
sheet = client.open(SHEET_NAME).sheet1
drive_creds = service_account.Credentials.from_service_account_info(creds_dict)
drive_service = build("drive", "v3", credentials=drive_creds)

def get_or_create_user_folder(username):
    query = f"name = '{username}' and mimeType = 'application/vnd.google-apps.folder' and '{DRIVE_FOLDER_ID}' in parents"
    response = drive_service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
    files = response.get("files", [])
    if files:
        return files[0]["id"]
    file_metadata = {"name": username, "mimeType": "application/vnd.google-apps.folder", "parents": [DRIVE_FOLDER_ID]}
    folder = drive_service.files().create(body=file_metadata, fields="id").execute()
    return folder.get("id")

def upload_to_drive(username, filename, filepath):
    folder_id = get_or_create_user_folder(username)
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(filepath, mimetype="image/jpeg")
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
    return uploaded_file.get("webViewLink")

def save_seller(user_id):
    sellers = {}
    if os.path.exists(SELLERS_FILE):
        with open(SELLERS_FILE, "r") as f:
            sellers = json.load(f)
    today = datetime.now().strftime('%Y-%m-%d')
    sellers[str(user_id)] = today
    with open(SELLERS_FILE, "w") as f:
        json.dump(sellers, f)

def get_inactive_sellers():
    today = datetime.now().strftime('%Y-%m-%d')
    inactive = []
    if os.path.exists(SELLERS_FILE):
        with open(SELLERS_FILE, "r") as f:
            sellers = json.load(f)
        for user_id, last_date in sellers.items():
            if last_date != today:
                inactive.append(int(user_id))
    return inactive

async def mute_user_in_groups(bot, user_id):
    for group_id in GROUP_IDS:
        try:
            await bot.restrict_chat_member(
                chat_id=group_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False)
            )
        except Exception as e:
            print(f"Failed to mute {user_id} in {group_id}: {e}")

async def unmute_user_in_groups(bot, user_id):
    for group_id in GROUP_IDS:
        try:
            await bot.restrict_chat_member(
                chat_id=group_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=True)
            )
        except Exception as e:
            print(f"Failed to unmute {user_id} in {group_id}: {e}")

async def runcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_USER_ID:
        return
    inactive = get_inactive_sellers()
    for user_id in inactive:
        await mute_user_in_groups(context.bot, user_id)
    await update.message.reply_text(f"Muted {len(inactive)} inactive sellers.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        
        """👋 Welcome! POP (Proof of Promo) is a screenshot showing you've shared our group links.
Use /submitpop to begin.

Then upload your screenshot."""
    )

async def submitpop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("🚫 Please DM me to submit your POP.")
        return
    context.chat_data["expecting_photo"] = True
    await update.message.reply_text("📸 Send your POP screenshot now.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return  # Ignore photos from groups

    if not context.chat_data.get("expecting_photo"):
        await update.message.reply_text("❗ Use /submitpop before sending screenshots.")
        return

    user = update.message.from_user
    username = user.username or f"user_{user.id}"
    file = await update.message.photo[-1].get_file()
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{username}_{timestamp}.jpg"
    filepath = os.path.join(POP_DIR, filename)
    await file.download_to_drive(filepath)

    context.chat_data["expecting_photo"] = False
    context.bot_data[f"pending_{user.id}"] = {
        "username": username,
        "user_id": user.id,
        "filename": filename,
        "filepath": filepath
    }

    await context.bot.send_photo(
        chat_id=ADMIN_USER_ID,
        photo=open(filepath, "rb"),
        caption=f"👀 POP from @{username}/approve_{user.id} or /reject_{user.id}",
        parse_mode="Markdown"
    )
    await update.message.reply_text("✅ POP submitted. Waiting for admin approval.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = re.match(r"/approve_(\d+)", update.message.text)
    if not match:
        return
    user_id = match.group(1)
    data = context.bot_data.get(f"pending_{user_id}")
    if not data:
        await update.message.reply_text("No pending submission.")
        return

    drive_link = upload_to_drive(data["username"], data["filename"], data["filepath"])
    sheet.append_row([
        data["username"],
        data["user_id"],
        datetime.now().strftime('%Y-%m-%d'),
        datetime.now().strftime('%H:%M:%S'),
        drive_link
    ])
    save_seller(data["user_id"])
    await unmute_user_in_groups(context.bot, data["user_id"])
    await context.bot.send_message(chat_id=data["user_id"], text="✅ Your POP was approved!")
    await update.message.reply_text(f"✅ Approved @{data['username']}")
    del context.bot_data[f"pending_{user_id}"]

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = re.match(r"/reject_(\d+)", update.message.text)
    if not match:
        return
    user_id = match.group(1)
    data = context.bot_data.get(f"pending_{user_id}")
    if not data:
        await update.message.reply_text("No pending submission.")
        return

    await context.bot.send_message(chat_id=data["user_id"], text="❌ Your POP was rejected.")
    await update.message.reply_text(f"🚫 Rejected @{data['username']}")
    del context.bot_data[f"pending_{user_id}"]

async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    title = update.effective_chat.title or "Private Chat"
    await update.message.reply_text(f"🆔 This group is *{title}*
Chat ID: `{chat_id}`", parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("submitpop", submitpop))
    app.add_handler(CommandHandler("getid", getid))
    app.add_handler(CommandHandler("runcheck", runcheck))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/approve_\d+$"), approve))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/reject_\d+$"), reject))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()

if __name__ == "__main__":
    main()
