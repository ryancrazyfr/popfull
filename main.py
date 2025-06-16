import telegram
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)
from telegram import Update, ChatPermissions
import os
import json
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import re
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


BOT_TOKEN = os.environ['BOT_TOKEN']
GOOGLE_JSON = os.environ['GOOGLE_JSON']
SHEET_NAME = "POP Submissions"
POP_DIR = "pop_submissions"
DRIVE_FOLDER_ID = "1GvJdGDW7ZZPTyhbxNW-W9P1J94unyGvp"
ADMIN_USER_ID = 6276794389

GROUP_IDS = [
    -1001906279445,  # The Sluts Store
    -1001623432634,  # Content Hub
    -1001821941202,  # Sexy Baddies
    -1001923306291,  # CumSluts Paradise
    -1001709491100,  # Seductive Sirens
]

REMINDER_GROUP_ID = -1001664882105

if not os.path.exists(POP_DIR):
    os.makedirs(POP_DIR)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_JSON)
sheets_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(sheets_creds)
sheet = client.open(SHEET_NAME).sheet1
drive_creds = service_account.Credentials.from_service_account_info(creds_dict)
drive_service = build("drive", "v3", credentials=drive_creds)

# Store approved users each week
def get_all_submitted_user_ids():
    records = sheet.get_all_records()
    return {str(row['User ID']) for row in records if 'User ID' in row}

def get_or_create_user_folder(username):
    if not username:
        return DRIVE_FOLDER_ID
    query = f"name = '{username}' and mimeType = 'application/vnd.google-apps.folder' and '{DRIVE_FOLDER_ID}' in parents"
    response = drive_service.files().list(q=query, spaces='drive', fields="files(id, name)").execute()
    files = response.get("files", [])
    if files:
        return files[0]["id"]
    file_metadata = {"name": username, "mimeType": "application/vnd.google-apps.folder", "parents": [DRIVE_FOLDER_ID]}
    folder = drive_service.files().create(body=file_metadata, fields="id").execute()
    return folder.get("id")

def upload_to_drive(username, filename, filepath):
    folder_id = get_or_create_user_folder(username or "unknown")
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(filepath, mimetype="image/jpeg")
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields="id, webViewLink").execute()
    return uploaded_file.get("webViewLink")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "👋 Welcome to the POP Bot!\n\n"
        "📌 *What is POP?*\n"
        "POP (Proof of Promo) is a screenshot you take after promoting our group links "
        "on your own channel or another platform. It helps keep our traffic strong!\n\n"
        "🛠 To submit your weekly POP:\n"
        "1. Tap /submitpop\n"
        "2. Upload your screenshot\n\n"
        "📎 Below are the group links you need to promote 👇"
    )
    await update.message.reply_markdown(welcome_msg)

    pop_links = """🔗 *Do your POP here:*

- [Sexy Baddies](https://t.me/+tGBn9q_6Z-9jMTAx)
- [Content Hub](https://t.me/+F_BNXoMjPPhmNGEx)
- [Seductive Sirens](https://t.me/+nvm1zwZz7FA1MTdh)
- [The Sluts Store](https://t.me/+pkxiRKn2ZvcyMjI8)
- [My Hot Friends](https://t.me/+A47SCYOy2_MzOTcx)
- [CumSlut Paradise](https://t.me/+y5TaJPgVGvI1NzQ0)
"""
    await update.message.reply_markdown(pop_links)

async def submitpop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["expecting_photo"] = True
    await update.message.reply_text("Please send your POP screenshot now.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ignore photos from groups
    if update.effective_chat.type != "private":
        return

    # Only respond if expecting a photo
    if not context.chat_data.get("expecting_photo"):
        await update.message.reply_text("❗ Please tap /submitpop before sending your screenshot.")
        return

    # Reset state
    context.chat_data["expecting_photo"] = False


    user = update.message.from_user
    username = user.username or f"user_{user.id}"
    photo = update.message.photo[-1]
    file = await photo.get_file()
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{username}_{timestamp}.jpg"
    filepath = os.path.join(POP_DIR, filename)
    await file.download_to_drive(filepath)

    context.bot_data[f"pending_{user.id}"] = {
        "username": username,
        "user_id": user.id,
        "filename": filename,
        "filepath": filepath,
        "timestamp": timestamp
    }

    await context.bot.send_photo(
        chat_id=ADMIN_USER_ID,
        photo=open(filepath, "rb"),
        caption=f"👀 *POP Submission from @{username}*\n\nApprove this screenshot?\nReply with /approve_{user.id} or /reject_{user.id}",
        parse_mode="Markdown"
    )

    await update.message.reply_text("📤 POP submitted! Waiting for admin approval.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        command = update.message.text.strip()
        match = re.match(r"/approve_(\d+)", command)
        if not match:
            await update.message.reply_text("❌ Invalid approve command format.")
            return

        user_id = match.group(1)
        data = context.bot_data.get(f"pending_{user_id}")

        if not data:
            await update.message.reply_text(f"❌ No pending submission found for user {user_id}.")
            return

        drive_link = upload_to_drive(data["username"], data["filename"], data["filepath"])
        sheet.append_row([
            data["username"],
            str(data["user_id"]),
            datetime.now().strftime('%Y-%m-%d'),
            datetime.now().strftime('%H:%M:%S'),
            drive_link
        ])

        for group_id in GROUP_IDS:
            try:
                await context.bot.restrict_chat_member(
                    group_id,
                    int(user_id),
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
            except Exception as e:
                print(f"Error unmuting user in group {group_id}: {e}")

        await context.bot.send_message(chat_id=data["user_id"], text="✅ Your POP has been approved and logged.")
        await context.bot.send_message(chat_id=data["user_id"], text="✅ You have been unmuted in all promo groups. Thanks for submitting your POP!")
        await update.message.reply_text(f"✅ Approved and uploaded for @{data['username']}.")
        del context.bot_data[f"pending_{user_id}"]
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        command = update.message.text.strip()
        match = re.match(r"/reject_(\d+)", command)
        if not match:
            await update.message.reply_text("❌ Invalid reject command format.")
            return

        user_id = match.group(1)
        data = context.bot_data.get(f"pending_{user_id}")

        if not data:
            await update.message.reply_text(f"❌ No pending submission found for user {user_id}.")
            return

        await context.bot.send_message(chat_id=data["user_id"], text="❌ Your POP has been rejected by admin.")
        await update.message.reply_text(f"🚫 Rejected submission from @{data['username']}.")
        del context.bot_data[f"pending_{user_id}"]
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    title = update.effective_chat.title
    await update.message.reply_text(f"🆔 This group is *{title}*\nChat ID: `{chat_id}`", parse_mode="Markdown")

async def runcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    submitted_ids = get_all_submitted_user_ids()

    for group_id in GROUP_IDS:
        try:
            members = await context.bot.get_chat_administrators(group_id)
            for admin in members:
                user_id = admin.user.id
                if str(user_id) not in submitted_ids:
                    try:
                        await context.bot.restrict_chat_member(
                            group_id,
                            user_id,
                            permissions=ChatPermissions(can_send_messages=False)
                        )
                        await context.bot.send_message(chat_id=user_id, text="🚫 You have been muted in the promo group for not submitting POP by Friday.")
                    except Exception as e:
                        print(f"Error muting user {user_id} in group {group_id}: {e}")
        except Exception as e:
            print(f"Error getting admins for group {group_id}: {e}")

    await update.message.reply_text("✅ Runcheck complete. Users who didn’t submit POP have been muted.")

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        REMINDER_GROUP_ID,
        "⏰ Don’t forget to submit your POP screenshot before Friday to avoid getting muted!"
    )
scheduler = AsyncIOScheduler()
async def on_startup(app):
    scheduler.add_job(send_reminder, CronTrigger(day_of_week='tue,thu', hour=10, minute=0), args=[app])
    scheduler.start()
    print("Scheduler started")
    
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ You’re not authorized to run this command.")
        return

    if not context.args:
        await update.message.reply_text("❗ Usage: /muteuser @username")
        return

    username = context.args[0].lstrip('@')

    for group_id in GROUP_IDS:
        try:
            members = await context.bot.get_chat_administrators(group_id)
            member = next(
                (m.user for m in members if m.user.username == username), None
            )

            if not member:
                chat_members = await context.bot.get_chat_members_count(group_id)
                for i in range(chat_members):  # fallback scan
                    try:
                        user = await context.bot.get_chat_member(group_id, i)
                        if user.user.username == username:
                            member = user.user
                            break
                    except:
                        continue

            if member:
                await context.bot.restrict_chat_member(
                    group_id,
                    member.id,
                    permissions=ChatPermissions(can_send_messages=False)
                )
                await update.message.reply_text(f"🔇 @{username} has been muted in group {group_id}")
            else:
                await update.message.reply_text(f"⚠️ @{username} not found in group {group_id}")

        except Exception as e:
            await update.message.reply_text(f"❌ Error muting @{username} in {group_id}: {e}")

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❓ Please ask a question after the command. Example:\n/ask What is POP?")
        return

    question = " ".join(context.args)

    # Prompt restriction
    if "pop" not in question.lower():
        await update.message.reply_text("❌ I only answer questions about POP. Please rephrase.")
        return

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a Telegram bot assistant that explains POP (Proof of Promotion) rules and process clearly."},
                {"role": "user", "content": question}
            ]
        )
        answer = response.choices[0].message.content.strip()
        await update.message.reply_text(f"🧠 {answer}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("submitpop", submitpop))
    app.add_handler(CommandHandler("getid", getid))
    app.add_handler(CommandHandler("runcheck", runcheck))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/approve_\d+$"), approve))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/reject_\d+$"), reject))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CommandHandler("muteuser", mute_user))
    app.add_handler(CommandHandler("ask", ask))


    
    app.run_polling()

if __name__ == "__main__":
    main()
