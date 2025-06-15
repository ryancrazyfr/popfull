import telegram
import os
import json
import re
import logging
from datetime import datetime, timedelta
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIGURATION ===
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID"))  # Your Telegram user ID
GROUP_IDS = [
    -1001906279445,  # The Sluts Store
    -1001623432634,  # Content Hub
    -1001821941202,  # Sexy Baddies
    -1001923306291,  # CumSluts Paradise
    -1001709491100,  # Seductive Sirens
]

# === GOOGLE SHEETS/DRIVE SETUP ===
SHEET_NAME = "POP Submissions"
POP_DIR = "pop_submissions"
GOOGLE_JSON = os.environ["GOOGLE_JSON"]

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# === STATE ===
user_state = {}
pending_approval = {}

# === LOGGING ===
logging.basicConfig(level=logging.INFO)

# === COMMANDS ===

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

    poplinks = """🔗 *Do your POP here:*

- [Sexy Baddies](https://t.me/+tGBn9q_6Z-9jMTAx)
- [Content Hub](https://t.me/+F_BNXoMjPPhmNGEx)
- [Seductive Sirens](https://t.me/+nvm1zwZz7FA1MTdh)
- [The Sluts Store](https://t.me/+pkxiRKn2ZvcyMjI8)
- [My Hot Friends](https://t.me/+A47SCYOy2_MzOTcx)
- [CumSlut Paradise](https://t.me/+y5TaJPgVGvI1NzQ0)
"""
    await update.message.reply_markdown(poplinks)

async def submitpop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("❌ Please DM me to submit your POP.")
        return
    user_state[update.effective_user.id] = "awaiting_photo"
    await update.message.reply_text("📸 Send your POP screenshot now.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"id{user_id}"
    if user_state.get(user_id) != "awaiting_photo":
        await update.message.reply_text("⚠️ Please use /submitpop before sending your screenshot.")
        return

    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    filename = f"{username}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"

    # Create user folder if needed
    folder_path = os.path.join(POP_DIR, username)
    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, filename)
    await file.download_to_drive(filepath)

    # Log to Google Sheet
    sheet.append_row([str(user_id), username, filename, str(datetime.now())])

    # Notify admin
    caption = (
        f"👁 POP from @{username}\n"
        f"/approve_{user_id} or /reject_{user_id}"
    )
    await context.bot.send_photo(chat_id=ADMIN_USER_ID, photo=open(filepath, "rb"), caption=caption)

    pending_approval[user_id] = True
    user_state.pop(user_id)
    await update.message.reply_text("✅ POP submitted. Waiting for admin approval.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = re.match(r"/approve_(\d+)", update.message.text)
    if not match:
        return
    user_id = int(match.group(1))
    if pending_approval.get(user_id):
        pending_approval.pop(user_id)
        await unmute_user_in_groups(context.bot, user_id)
        await update.message.reply_text(f"✅ Approved user {user_id}")
        await context.bot.send_message(chat_id=user_id, text="✅ Your POP was approved!")
    else:
        await update.message.reply_text("No pending submission.")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = re.match(r"/reject_(\d+)", update.message.text)
    if not match:
        return
    user_id = int(match.group(1))
    if pending_approval.get(user_id):
        pending_approval.pop(user_id)
        await update.message.reply_text(f"❌ Rejected user {user_id}")
        await context.bot.send_message(chat_id=user_id, text="❌ Your POP was rejected.")
    else:
        await update.message.reply_text("No pending submission.")

# === UTILITIES ===

def get_inactive_sellers():
    records = sheet.get_all_records()
    submitted_ids = {int(row["user_id"]) for row in records}
    known_ids = set(user_state.keys()) | set(pending_approval.keys())
    return list(known_ids - submitted_ids)

async def mute_user_in_groups(bot, user_id):
    for group_id in GROUP_IDS:
        try:
            await bot.restrict_chat_member(
                group_id, user_id,
                permissions=telegram.ChatPermissions(can_send_messages=False)
            )
        except Exception as e:
            logging.warning(f"Failed to mute in {group_id}: {e}")

async def unmute_user_in_groups(bot, user_id):
    for group_id in GROUP_IDS:
        try:
            await bot.restrict_chat_member(
                group_id, user_id,
                permissions=telegram.ChatPermissions(can_send_messages=True)
            )
        except Exception as e:
            logging.warning(f"Failed to unmute in {group_id}: {e}")

async def runcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_USER_ID:
        return
    inactive = get_inactive_sellers()
    for user_id in inactive:
        await mute_user_in_groups(context.bot, user_id)
    await update.message.reply_text(f"Muted {len(inactive)} inactive sellers.")

# === MAIN ===

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("submitpop", submitpop))
    app.add_handler(CommandHandler("runcheck", runcheck))
    app.add_handler(MessageHandler(filters.Regex(r"^/approve_\d+$"), approve))
    app.add_handler(MessageHandler(filters.Regex(r"^/reject_\d+$"), reject))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("🤖 Bot is running.")
    app.run_polling()
