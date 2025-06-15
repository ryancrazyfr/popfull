import os
import re
import datetime
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === CONFIGURATION ===
BOT_TOKEN = "7854611527:AAHEP_ZsZ0cj3hOaPTiSz18hi9kYOotftDs"
ADMIN_USER_ID = 6276794389
CREDENTIALS_FILE = "telegrampopbot-15680edde189.json"
SHEET_NAME = "POP Submissions"
POP_DIR = "pop_submissions"

GROUP_CHAT_IDS = [
    -1001906279445,  # The Sluts Store
    -1001623432634,  # Content Hub
    -1001821941202,  # Sexy Baddies
    -1001923306291,  # CumSluts Paradise
    -1001709491100,  # Seductive Sirens
]

# === SETUP GOOGLE SHEETS ===
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# === UTILITIES ===
def log_submission(username, user_id, time_str, folder_url):
    sheet.append_row([username, str(user_id), time_str, folder_url])

def get_inactive_sellers():
    all_records = sheet.get_all_records()
    today = datetime.datetime.now().date()
    inactive = set()
    for record in all_records:
        try:
            dt = datetime.datetime.strptime(record['Timestamp'], "%Y-%m-%d %H:%M:%S")
            if (today - dt.date()).days >= 7:
                inactive.add(int(record['Telegram ID']))
        except:
            continue
    return list(inactive)

async def mute_user_in_groups(bot, user_id):
    for chat_id in GROUP_CHAT_IDS:
        try:
            await bot.restrict_chat_member(chat_id, user_id, permissions={"can_send_messages": False})
        except:
            pass

async def unmute_user_in_groups(bot, user_id):
    for chat_id in GROUP_CHAT_IDS:
        try:
            await bot.restrict_chat_member(chat_id, user_id, permissions={
                "can_send_messages": True,
                "can_send_media_messages": True,
                "can_send_polls": True,
                "can_send_other_messages": True,
                "can_add_web_page_previews": True,
                "can_change_info": False,
                "can_invite_users": True,
                "can_pin_messages": False
            })
        except:
            pass

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! POP (Proof of Promo) is a screenshot showing you've promoted in the listed groups.\n\n"
        "Use /submitpop to begin.\nThen upload your screenshot."
    )

async def poplinks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📣 Promote in these groups:\n"
        "• Sexy Baddies: https://t.me/+tGBn9q_6Z-9jMTAx\n"
        "• Content Hub: https://t.me/+F_BNXoMjPPhmNGEx\n"
        "• Seductive Sirens: https://t.me/+nvm1zwZz7FA1MTdh\n"
        "• The Sluts Store: https://t.me/+pkxiRKn2ZvcyMjI8\n"
        "• My Hot Friends: https://t.me/+A47SCYOy2_MzOTcx\n"
        "• CumSlut Paradise: https://t.me/+y5TaJPgVGvI1NzQ0"
    )

async def submitpop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['expecting_photo'] = True
    await update.message.reply_text("📸 Send your POP screenshot now.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('expecting_photo'):
        await update.message.reply_text("❗ Please tap /submitpop before sending a screenshot.")
        return

    user = update.message.from_user
    user_id = user.id
    username = user.username or user.first_name
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    folder_name = f"{username}_{user_id}"
    user_folder = os.path.join(POP_DIR, folder_name)
    os.makedirs(user_folder, exist_ok=True)

    photo_file = await update.message.photo[-1].get_file()
    filename = f"{timestamp.replace(':', '-')}.jpg"
    filepath = os.path.join(user_folder, filename)
    await photo_file.download_to_drive(filepath)

    context.bot_data[f"pending_{user_id}"] = {
        "username": username,
        "filepath": filepath,
        "timestamp": timestamp,
        "folder": user_folder
    }

    caption = f"👁️ POP from @{username}\n/approve_{user_id} or /reject_{user_id}"
    await context.bot.send_photo(
        chat_id=ADMIN_USER_ID,
        photo=open(filepath, "rb"),
        caption=caption,
        parse_mode="Markdown"
    )

    await update.message.reply_text("✅ POP submitted. Waiting for admin approval.")
    context.user_data['expecting_photo'] = False

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = re.match(r"/approve_(\d+)", update.message.text)
    if not match:
        return
    user_id = int(match.group(1))
    data = context.bot_data.get(f"pending_{user_id}")
    if not data:
        await update.message.reply_text("❌ No pending submission.")
        return

    log_submission(data['username'], user_id, data['timestamp'], f"Drive: {data['folder']}")
    await unmute_user_in_groups(context.bot, user_id)
    await update.message.reply_text("✅ Approved and unmuted.")
    del context.bot_data[f"pending_{user_id}"]

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match = re.match(r"/reject_(\d+)", update.message.text)
    if not match:
        return
    user_id = int(match.group(1))
    if context.bot_data.get(f"pending_{user_id}"):
        del context.bot_data[f"pending_{user_id}"]
    await update.message.reply_text("❌ Rejected.")

async def runcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_USER_ID:
        return
    inactive = get_inactive_sellers()
    for user_id in inactive:
        await mute_user_in_groups(context.bot, user_id)
    await update.message.reply_text(f"Muted {len(inactive)} inactive sellers.")

# === MAIN ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("submitpop", submitpop))
    app.add_handler(CommandHandler("poplinks", poplinks))
    app.add_handler(CommandHandler("runcheck", runcheck))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Regex(r"^/approve_\d+"), approve))
    app.add_handler(MessageHandler(filters.Regex(r"^/reject_\d+"), reject))
    app.run_polling()

if __name__ == "__main__":
    main()
