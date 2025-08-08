import telegram
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
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
from datetime import datetime, timedelta
import openai
from telegram.constants import ParseMode
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

openai.api_key = os.environ["OPENAI_API_KEY"]


BOT_TOKEN = os.environ['BOT_TOKEN']
GOOGLE_JSON = os.environ['GOOGLE_JSON']
SHEET_NAME = "POP Submissions"
POP_DIR = "pop_submissions"
DRIVE_FOLDER_ID = "1f63NmpGcktoNdEsy25OQsYvcfJeO5vpP"
ADMIN_USER_ID = 6276794389

GROUP_IDS = [
    -1001906279445,  # The Sluts Store
    -1001623432634,  # Content Hub
    -1001821941202,  # Sexy Baddies
    -1001923306291,  # CumSluts Paradise
    -1001709491100,  # Seductive Sirens
]

TUESDAY_GROUP_IDS = [
    -1002014635705,
    -1002040745178,
    -1002034514107,
    -1002131278970,
    -1002076400364
]

REMINDER_GROUP_ID = -1001664882105


pop_links = """🔗 *Friday POP*

Sexy Baddies\nt.me/+tGBn9q_6Z-9jMTAx\n  
Content Hub\nt.me/+F_BNXoMjPPhmNGEx\n  
Seductive Sirens\nt.me/+nvm1zwZz7FA1MTdh\n  
The Sluts Store\nt.me/+pkxiRKn2ZvcyMjI8\n  
My Hot Friends\nt.me/+A47SCYOy2_MzOTcx\n  
CumSlut Paradise\nt.me/+y5TaJPgVGvI1NzQ0\n  
"""
tuesday_links = """ 🆕️ *Tuesday POP* 

Fashion dolls\nt.me/+d_NP9s67LjViYTAx\n
College chicks\nt.me/+x3Lq01jlY_k3OWNh\n
Content Palace\nt.me/+11zyCb_Ei-9mNjMx\n
Natural Melons\nt.me/+Iu-R20OXD2NmMjNh\n
Kitty Wet\nt.me/+H8aVpb7S33NiZmNh\n
"""
if not os.path.exists(POP_DIR):
    os.makedirs(POP_DIR)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_JSON)
sheets_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(sheets_creds)
spreadsheet = client.open(SHEET_NAME)
sheet = spreadsheet.sheet1  # For POP Submissions
refresh_sheet = spreadsheet.worksheet("Refresh_Groups")
tuesday_sheet = spreadsheet.worksheet("Tuesday_Pop")
drive_creds = service_account.Credentials.from_service_account_info(creds_dict)
drive_service = build("drive", "v3", credentials=drive_creds)

REFRESH_IDS = [-1001512076600, -1001706140667, -1001867826270]  # your 3 refresh groups





def get_or_create_user_folder(username):
    if not username:
        return DRIVE_FOLDER_ID

    query = f"name = '{username}' and mimeType = 'application/vnd.google-apps.folder' and '{DRIVE_FOLDER_ID}' in parents"
    response = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)',
        supportsAllDrives=True,  # ✅ Add this
        includeItemsFromAllDrives=True  # ✅ And this
    ).execute()

    files = response.get("files", [])
    if files:
        return files[0]["id"]

    file_metadata = {
        "name": username,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [DRIVE_FOLDER_ID]
    }
    folder = drive_service.files().create(
        body=file_metadata,
        fields="id",
        supportsAllDrives=True  # ✅ Add this
    ).execute()

    return folder.get("id")

def upload_to_drive(username, filename, filepath):
    folder_id = get_or_create_user_folder(username or "unknown")
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(filepath, mimetype="image/jpeg")
    
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink",
        supportsAllDrives=True   # ✅ Required for shared drives
    ).execute()
    
    return uploaded_file.get("webViewLink")
    

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "👋 Hello! Welcome to the Pop Bot of Silk and Sin Network.\n\n"
        "This bot is the new way of submitting POP – simple, automated, and efficient.\n\n" 
        "🚀 If you want a custom bot like this built for your group or business, contact @sexydolladmin\n\n"
        "📌 *What is POP?*\n"
        "POP (Proof of Promo) is a screenshot or recording you take after promoting our group links "
        "on your own channel or another platform. It helps keep our traffic strong!\n\n"
        "🛠 To submit your weekly POP:\n\n"
        "1. Tap /submitpop\n"
        "2. Select which pop you're submitting\n"
        "3. Send your POP to this bot\n"
        "4. wait for admin approval\n"
        "5. if your pop is rejected, please send again\n\n"
        "POP is due on every Friday\n\n"
        "📎 Below are the group links you need to promote 👇"
        
    )
    await update.message.reply_markdown(welcome_msg)
          
    
    await update.message.reply_text(pop_links, parse_mode="HTML", disable_web_page_preview=True)
    await update.message.reply_text(tuesday_links, parse_mode="HTML", disable_web_page_preview=True)
          

async def submitpop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Friday POP", callback_data='pop_friday')],
        [InlineKeyboardButton("Tuesday POP", callback_data='pop_tuesday')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Which POP are you submitting?", reply_markup=reply_markup)


async def handle_pop_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pop_day = 'friday' if query.data == 'pop_friday' else 'tuesday'
    context.user_data['pop_day'] = pop_day
    context.chat_data["expecting_photo"] = True  # ✅ This line is needed

    await query.edit_message_text(f"Great! Now please send your {pop_day.capitalize()} POP screenshot.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only allow photos in private chat
    if update.effective_chat.type != "private":
        return

    # Check if user is expected to send a photo
    if not context.chat_data.get("expecting_photo"):
        await update.message.reply_text("❗ Please tap /submitpop before sending your POP.")
        return

    # Reset flag
    context.chat_data["expecting_photo"] = False

    user = update.message.from_user
    username = user.username or f"user_{user.id}"
    photo = update.message.photo[-1]
    file = await photo.get_file()

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{username}_{timestamp}.jpg"
    filepath = os.path.join(POP_DIR, filename)
    await file.download_to_drive(filepath)

    # Get which POP day this is for
    pop_day = context.user_data.get("pop_day", "friday")
    key = f"pending_{user.id}_{pop_day}"

    # Save pending submission
    context.bot_data[key] = {
        "username": username,
        "user_id": user.id,
        "filename": filename,
        "filepath": filepath,
        "timestamp": timestamp,
        "pop_day": pop_day
    }

    # Notify admin with correct approve/reject format
    await context.bot.send_photo(
        chat_id=ADMIN_USER_ID,
        photo=open(filepath, "rb"),
        caption=(
            f"👀 *{pop_day.capitalize()} POP Submission from @{username}*\n\n"
            f"✅ Approve: /approve_{user.id}_{pop_day}\n"
            f"❌ Reject: /reject_{user.id}_{pop_day}"
        ),
        parse_mode="Markdown"
    )

    # Confirm to user
    await update.message.reply_text(f"📤 {pop_day.capitalize()} POP submitted! Waiting for admin approval.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    if not context.chat_data.get("expecting_photo"):
        await update.message.reply_text("❗ Please tap /submitpop before sending your screen recording.")
        return

    context.chat_data["expecting_photo"] = False

    user = update.message.from_user
    username = user.username or f"user_{user.id}"
    video = update.message.video
    file = await video.get_file()
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{username}_{timestamp}.mp4"
    filepath = os.path.join(POP_DIR, filename)
    await file.download_to_drive(filepath)

    pop_day = context.user_data.get("pop_day", "friday")

    # Save for approval
    context.bot_data[f"pending_{user.id}"] = {
        "username": username,
        "user_id": user.id,
        "filename": filename,
        "filepath": filepath,
        "timestamp": timestamp,
        "pop_day": pop_day
    }

    await context.bot.send_video(
        chat_id=ADMIN_USER_ID,
        video=open(filepath, "rb"),
        caption=(
            f"👀 *{pop_day.capitalize()} POP Submission from @{username}*\n\n"
            f"Approve this video?\n"
            f"Reply with /approve_{user.id} or /reject_{user.id}"
        ),
        parse_mode="Markdown"
    )

    await update.message.reply_text("📤 Screen recording POP submitted! Waiting for admin approval.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        command = update.message.text.strip()
        match = re.match(r"/approve_(\d+)_(friday|tuesday)", command)
        if not match:
            await update.message.reply_text("❌ Invalid approve command format.")
            return

        user_id = match.group(1)
        pop_day = match.group(2)
        key = f"pending_{user_id}_{pop_day}"
        data = context.bot_data.get(key)

        if not data:
            await update.message.reply_text(f"❌ No pending submission found for user {user_id} ({pop_day}).")
            return

        # Upload to Drive
        drive_link = upload_to_drive(data["username"], data["filename"], data["filepath"])
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d')
        time_str = now.strftime('%H:%M:%S')

        # Log to correct sheet
        if pop_day == "tuesday":
            tuesday_sheet.append_row([
                data["username"],
                str(data["user_id"]),
                date_str,
                time_str,
                drive_link
            ])
            unmute_groups = TUESDAY_GROUP_IDS
        else:
            sheet.append_row([
                data["username"],
                str(data["user_id"]),
                date_str,
                time_str,
                drive_link
            ])
            unmute_groups = GROUP_IDS

        # Unmute the user
        for group_id in unmute_groups:
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

        # Notify
        await context.bot.send_message(chat_id=int(user_id), text=f"✅ Your {data['pop_day'].capitalize()} POP has been approved and logged.")
        await context.bot.send_message(chat_id=int(user_id), text="✅ You have been unmuted in the relevant promo groups. Thanks for submitting your POP!")
        await update.message.reply_text(f"✅ Approved and uploaded for @{data['username']}.")
        del context.bot_data[key]

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    match = re.match(r"/reject(\d+)(friday|tuesday)", update.message.text.strip())
    if not match:
        await update.message.reply_text("❌ Invalid reject command format.")
        return

    user_id = int(match.group(1))
    pop_day = match.group(2)

    key = f"pending_{user_id}_{pop_day}"
    pending_data = context.bot_data.get(key)

    if not pending_data:
        await update.message.reply_text(f"❌ No pending submission found for user {user_id} ({pop_day}).")
        return

    try:
        # Notify user of rejection
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ Your {pop_day.capitalize()} POP submission was rejected by the admin. Please send it again."
        )
        await update.message.reply_text(f"🚫 {pop_day.capitalize()} POP rejected and user notified.")

        # Delete the rejected image from Drive (optional)
        filepath = pending_data.get("filepath")
        if filepath:
            os.remove(filepath)

        # Remove pending data
        del context.bot_data[key]

    except Exception as e:
        await update.message.reply_text(f"❌ Error rejecting POP: {e}")
        
async def getid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    title = update.effective_chat.title
    await update.message.reply_text(f"🆔 This group is *{title}*\nChat ID: `{chat_id}`", parse_mode="Markdown")

def get_last_friday():
    today = datetime.today()
    offset = (today.weekday() - 4) % 7  # Friday is weekday 4
    last_friday = today - timedelta(days=offset)
    return datetime.combine(last_friday.date(), datetime.min.time())


def get_all_submitted_user_ids(sheet):
    records = sheet.get_all_records()
    submitted_ids = set()

    start_of_week = get_last_friday()

    for row in records:
        try:
            date_str = row["Date"]
            time_str = row["Time"]
            timestamp = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")

            if timestamp >= start_of_week:
                submitted_ids.add(str(row["User ID"]))
        except Exception as e:
            print(f"Skipping row due to error: {e}")

    return submitted_ids



def get_tracked_user_ids(sheet):
    records = sheet.get_all_records()
    return {str(row["User ID"]) for row in records if "User ID" in row}

async def runcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return

    submitted_ids = get_all_submitted_user_ids(sheet)
    tracked_users = get_tracked_user_ids(sheet)

    
    for user_id in tracked_users:
        if user_id not in submitted_ids:
            try:
              for group_id in GROUP_IDS:
                await context.bot.restrict_chat_member(
                        group_id,
                        int(user_id),
                        permissions=ChatPermissions(can_send_messages=False)
                    )
              await context.bot.send_message(
                    chat_id=user_id,
                    text="🔇 New POP week started! You’ve been muted in Friday pop groups. Please send your pop to get unmuted!"
                    )
            except Exception as e:
                    print(f"❌ Error muting {user_id} in {group_id}: {e}")

    await update.message.reply_text("✅ Runcheck complete. Users who didn’t submit POP since last Friday have been muted.")

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        REMINDER_GROUP_ID,
        "⏰ Don’t forget to submit your POP screenshot before Friday to avoid getting muted!"
    )

async def send_pop_reminder(context: ContextTypes.DEFAULT_TYPE):
   
    submitted_ids =  get_all_submitted_user_ids(sheet)
    tracked_users = get_tracked_user_ids(sheet)

    for user_id in tracked_users:
        if user_id not in submitted_ids:
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=(
                        "📌 *Reminder*: You haven't submitted your POP for this week!\n\n"
                        "Please promote the groups and send your screenshot using:\n"
                        "`/submitpop`\n\n"
                        "💬 If you face any issues, DM [@sexydolladmin](https://t.me/sexydolladmin)\n\n"
                    
                    ),
                    parse_mode='Markdown',
                )
                # Second message: Group links
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=pop_links,  # Assuming this is a string of links
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"⚠️ Failed to remind user {user_id}: {e}")
                

async def test_pop_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_pop_reminder(context)
    await update.message.reply_text("✅ POP reminder sent manually.")

    
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
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a Telegram bot that helps users understand POP (Proof of Promotion), a process where content sellers prove that they promoted a group or channel by submitting a screenshot. Answer all questions based on this meaning of POP."},
                {"role": "user", "content": question}

            ]
        )
        answer = response.choices[0].message.content.strip()
        await update.message.reply_text(f"🧠 {answer}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

def get_duration_label(delta: timedelta) -> str:
    hours = delta.total_seconds() / 3600
    if hours == 24:
        return "24 Hours"
    elif hours == 72:
        return "3 Days"
    elif hours == 168:
        return "1 Week"
    elif hours >= 672:  # 28 days
        return "1 Month"
    else:
        return "Unknown"

def get_price(duration: str) -> int:
    prices = {
        "24 Hours": 35,
        "3 Days": 90,
        "1 Week": 250,
        "1 Month": 600
    }
    return prices.get(duration, 0)


async def vip_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args
        user_id = int(args[0])
        duration_str = args[1].lower()

        # Parse duration
        if duration_str.endswith("h"):
            delta = timedelta(hours=int(duration_str[:-1]))
        elif duration_str.endswith("d"):
            delta = timedelta(days=int(duration_str[:-1]))
        elif duration_str.endswith("w"):
            delta = timedelta(weeks=int(duration_str[:-1]))
        elif duration_str.endswith("m"):
            delta = timedelta(days=30 * int(duration_str[:-1]))
        else:
            await update.message.reply_text("❌ Invalid duration format. Use 24h, 3d, 1w, 1m.")
            return

        start_time = datetime.now()
        end_time = start_time + delta
        duration_label = get_duration_label(delta)
        price = get_price(duration_label)
        username = update.message.from_user.username or "unknown"

        # Add to Google Sheet (VIP_Users sheet)
        vip_sheet = spreadsheet.worksheet("VIP_Users")
        vip_sheet.append_row([
            str(user_id),
            username,
            start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "FALSE",
            duration_label,
            price
        ])

        
        
        

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")@bot.message_handler(commands=['vipadd'])


async def check_vip_expiry(app):
    bot = app.bot
    now = datetime.now()
    vip_sheet = spreadsheet.worksheet("VIP_Users")
    rows = vip_sheet.get_all_records()

    for i, row in enumerate(rows, start=2):  # Skip header row
        user_id = int(row["user_id"])
        end_time = datetime.strptime(row["end_time"], "%Y-%m-%d %H:%M:%S")
        reminder_sent = row["reminder_sent"].strip().upper() == "TRUE"

        time_diff = (end_time - now).total_seconds()

        if 0 < time_diff < 3600 and not reminder_sent:
            # Send reminder
            try:
                await bot.send_message(chat_id=user_id, text="⚠️ Your VIP access is about to expire in 1 hour! Renew to stay in the group.")
                vip_sheet.update_cell(i, 5, "TRUE")  # Update 'reminder_sent' to TRUE
            except:
                pass

        elif now > end_time:
            # Remove from VIP group
            try:
                await bot.ban_chat_member(1001898315101, user_id)
                await bot.unban_chat_member(1001898315101, user_id)
                await bot.send_message(chat_id=user_id, text="🚫 Your VIP subscription has expired. Please renew to rejoin.")
            except:
                pass




# -------- /refresh command --------
async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please type 'added' if you’ve completed the monthly refresh.")

# -------- Handle 'added' from user --------
async def handle_refresh_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != "private":
        return

    if update.message.text.strip().lower() != "added":
        return

    user = update.effective_user
    username = user.username or f"user_{user.id}"
    month = datetime.now().strftime('%B %Y')
    timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    context.bot_data[f"refresh_pending_{user.id}"] = {
        "User_id": user.id,
        "username": username,
        "month": month,
        "timestamp": timestamp,
    }

    await context.bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=f"⚠️ Refresh submission from @{username}\n"
             f"Approve with /approverefresh_{user.id} or reject with /rejectrefresh_{user.id}"
    )

    await update.message.reply_text("📤 Submission sent for admin approval.")

# -------- Approve --------
async def approve_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text.split("_")[1])
        data = context.bot_data.get(f"refresh_pending_{user_id}")
        if not data:
            await update.message.reply_text("⚠️ No pending submission found.")
            return

        # Log to sheet
        refresh_sheet.append_row([
            str(data["User_id"]),
            f"@{data['username']}",
            data["month"],
            data["timestamp"]
        ])

        # ✅ Unmute the user in all refresh groups
        for group_id in REFRESH_IDS:
            try:
                await context.bot.restrict_chat_member(
                    chat_id=group_id,
                    user_id=user_id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
                print(f"✅ Unmuted {user_id} in group {group_id}")
            except Exception as e:
                print(f"⚠️ Failed to unmute {user_id} in {group_id}: {e}")

        # Notify
        await context.bot.send_message(chat_id=user_id, text="✅ Your Refresh submission has been approved.")
        await update.message.reply_text(f"✅ Approved and logged for @{data['username']}")
        del context.bot_data[f"refresh_pending_{user_id}"]

    except Exception as e:
        print(f"❌ Error in approve_refresh: {e}")
        await update.message.reply_text("❌ Error approving submission.")

# -------- Reject --------
async def reject_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text.split("_")[1])
        data = context.bot_data.get(f"refresh_pending_{user_id}")
        if not data:
            await update.message.reply_text("⚠️ No pending submission found.")
            return

        await context.bot.send_message(chat_id=user_id, text="❌ Your Refresh submission was rejected by the admin.")
        await update.message.reply_text(f"❌ Rejected submission from @{data['username']}")
        del context.bot_data[f"refresh_pending_{user_id}"]
    except:
        await update.message.reply_text("❌ Error rejecting submission.")

# -------- Reminder on 25th --------
async def send_refresh_reminders(app):
    user_ids = set()
    records = refresh_sheet.get_all_records()
    current_month = datetime.now().strftime('%B %Y')
    for row in records:
        if row['Month'] == current_month:
            user_ids.add(int(row['User_id']))

    for user_id in user_ids:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="🔔 Don't forget to do your monthly refresh before the 1st!"
            )
        except:
            pass



def get_refresh_user_ids(refresh_sheet):
    now = datetime.now()

    # Start: 25th of this month
    start = datetime(now.year, now.month, 25)

    # End: 1st of next month
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1)
    else:
        end = datetime(now.year, now.month + 1, 1)

    print(f"🕒 Checking refresh submissions from {start} to {end}")

    records = refresh_sheet.get_all_records()
    telegram_ids = set()

    for row in records:
        try:
            ts_str = row.get("timestamp", "").strip()
            if not ts_str:
                continue

            # Parse timestamp with AM/PM format
            timestamp = datetime.strptime(ts_str, "%Y-%m-%d %I:%M %p")

            if start <= timestamp < end:
                user_ids.add(str(row["User_ID"]))
        except Exception as e:
            print(f"⚠️ Skipping row due to error: {e}, row: {row}")

    print(f"✅ Found {len(telegram_ids)} refresh users: {telegram_ids}")
    return telegram_ids

def get_all_tracked_user_ids(refresh_sheet):
    records = refresh_sheet.get_all_records()
    return {str(row["User_ID"]) for row in records if "User_ID" in row}

from telegram.error import Forbidden, BadRequest, TelegramError
from telegram import ChatPermissions

async def mute_non_refresh_submitters(context):
    tracked_users = get_all_tracked_user_ids(refresh_sheet)
    submitted_users = get_refresh_user_ids(refresh_sheet)

    for telegram_id in tracked_users:
        if telegram_id not in submitted_users:
            for group_id in REFRESH_IDS:
                try:
                    # Check if user is in the group
                    try:
                        member = await context.bot.get_chat_member(group_id, int(telegram_id))
                        if member.status in ['left', 'kicked']:
                            print(f"⚠️ User {telegram_id} not in group {group_id} (status: {member.status})")
                            continue  # Skip to next group
                    except (Forbidden, BadRequest, TelegramError) as e:
                        print(f"⚠️ Failed to fetch member status for user {user_id} in group {group_id}: {e}")
                        continue  # Skip to next group

                    # Get group title
                    try:
                        group = await context.bot.get_chat(group_id)
                        group_title = group.title
                    except Exception as e:
                        print(f"⚠️ Failed to get group title for {group_id}: {e}")
                        group_title = "a group"

                    # Mute the user
                    await context.bot.restrict_chat_member(
                        chat_id=group_id,
                        user_id=int(telegram_id),
                        permissions=ChatPermissions(can_send_messages=False)
                    )
                    print(f"✅ Muted {telegram_id} in {group_title}")

                    # Notify the user
                    try:
                        await context.bot.send_message(
                            chat_id=int(telegram_id),
                            text=f"🔇 You’ve been muted in *{group_title}* for not doing the monthly refresh!",
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        print(f"⚠️ Couldn’t notify user {telegram_id}: {e}")

                except Exception as e:
                    print(f"❌ Unexpected error while processing user {telegram_id} in group {group_id}: {e}")


async def run_fresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #print("run_fresh_command triggered")
    #print(f"User ID: {update.effective_user.id}")
    
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("⛔ Not authorized.")
        return

    try:
        await mute_non_refresh_submitters(context)
        await update.message.reply_text("✅ Refresh mute check executed.")
    except Exception as e:
        print(f"Error in runfresh: {e}")
        await update.message.reply_text("❌ Something went wrong.")
        

  
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tracked_users = get_tracked_user_ids(sheet)

    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return

    # Get full text after the command (everything after "/broadcast")
    message_text = update.message.text.partition(' ')[2].strip()

    if not message_text:
        await update.message.reply_text("Please provide a message to send.\nUsage: /broadcast Your message here")
        return

    # Replace \n with <br> to maintain line spacing with HTML
    message_to_send = message_text

    success, failed = 0, 0

    for user_id in tracked_users:
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=message_to_send,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            success += 1
        except Exception as e:
            failed += 1
            print(f"❌ Failed to send to {user_id}: {e}")

    await update.message.reply_text(f"✅ Sent to {success} users.\n❌ Failed for {failed} users.")


scheduler = AsyncIOScheduler()

async def on_startup(app):
    scheduler.add_job(send_reminder, CronTrigger(day_of_week='tue,thu', hour=10, minute=0), args=[app])
    scheduler.add_job(send_pop_reminder,CronTrigger(day_of_week="mon,tue,wed,thu,fri", hour=8, minute=0),args=[app],timezone="UTC")
    scheduler.add_job(send_refresh_reminders, CronTrigger(day=25, hour=8), args=[app])
    scheduler.add_job(check_vip_expiry, CronTrigger(minute="*/30"), args=[app])
    scheduler.add_job(mute_non_refresh_submitters, CronTrigger(day=1, hour=0, minute=0), args =[app])  # Midnight on 1st
    scheduler.add_job(runcheck, CronTrigger(day_of_week='fri', hour=12, minute=0), args =[app])
    scheduler.start()
    print("Scheduler started")


async def friday_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(pop_links, parse_mode="Markdown", disable_web_page_preview=True)

async def tuesdaypop_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(tuesday_links, parse_mode="Markdown", disable_web_page_preview=True)
    
def main():
    
    async def post_init(app):
        await on_startup(app)

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("submitpop", submitpop))
    app.add_handler(CallbackQueryHandler(handle_pop_selection, pattern='^pop_'))
    app.add_handler(CommandHandler("getid", getid))
    app.add_handler(CommandHandler("friday", friday_links))
    app.add_handler(CommandHandler("tuesday", tuesdaypop_links))
    app.add_handler(CommandHandler("runcheck", runcheck))
    app.add_handler(CommandHandler("runfresh", run_fresh_command))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/approve_\d+_(friday|tuesday)"), approve))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/reject_\d+_(friday|tuesday)"), reject))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("testreminder", test_pop_reminder))
    app.add_handler(CommandHandler("vip_add", vip_add))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))


    app.add_handler(CommandHandler("refresh", refresh_command))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/approverefresh_\d+$"), approve_refresh))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/rejectrefresh_\d+$"), reject_refresh))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_refresh_added))
    
    
    app.run_polling()

if __name__ == "__main__":
    main()
