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
from functools import wraps

openai.api_key = os.environ["OPENAI_API_KEY"]


BOT_TOKEN = os.environ['BOT_TOKEN']
GOOGLE_JSON = os.environ['GOOGLE_JSON']
SPREADSHEET_ID = "1rXCKlw581-NjN84nC3pgv7gAaPOqTcDgZYo19TUG5Xc"
POP_DIR = "pop_submissions"
DRIVE_FOLDER_ID = "1f63NmpGcktoNdEsy25OQsYvcfJeO5vpP"
ADMIN_USER_ID = 8505097754
ADMIN_USER_IDS = {ADMIN_USER_ID}  # add more IDs if needed

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

REFRESH_IDS = [
    -1001512076600,  # Start Hoes
    -1001867826270   # Wickedly Wild
]

REMINDER_GROUP_ID = -1001664882105


pop_links = """🔗 *Friday POP*

Sexy Dolls\nt.me/+fL7Ljzo8vXA1NmU0\n  
Content Hub\nt.me/+iguYEoczIl1jZmY0\n  
Seductive Sirens\nt.me/+JO_A6MHMVBRkZDE8\n  
The Sluts Store\nt.me/+HJYCm5oeTOA5MDE8\n  
My Hot Friends\nt.me/+isgT_YOk0vliNTY0\n  
CumSlut Paradise\nt.me/+aRldyzJPHzE3ZjZk\n  
"""
tuesday_links = """ 🆕️ *Tuesday POP* 

Fashion dolls\nt.me/+51I72rtICgMzMjNk\n
College chicks\nt.me/+VNmJZf6UfAUxY2U0\n
Content Palace\nt.me/+jIZ6y2WsOidiODE0\n
Silver Dolls\nt.me/+FzroE0DeVos3YTFk\n
Diamond Dolls\nt.me/+ZqAAaqss-6cwYmU0\n
"""

refresh_links = """✅️ Regular/buyers only groups (the groups below aren't pop groups please don't do pop with these links)\n 

👠 Wickedly Wild +5 buyers  +2 monthly Refresh 
 https://t.me/+IfdNFBq3cZs5MzQx\n

🌟 Star Hoes +5 buyers +2 monthly Refresh 
https://t.me/+Mk3KCg1_wP44MTFh\n

😈 Buyers Paradise + 10 buyers 
https://t.me/+x5HoQ9Bud3FjMTNh\n

💋 Pleasure Palace +10 buyers 
https://t.me/+bOmZq5ODKslhMWFh
"""

if not os.path.exists(POP_DIR):
    os.makedirs(POP_DIR)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_JSON)
sheets_creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(sheets_creds)
spreadsheet = client.open_by_key(SPREADSHEET_ID)
sheet = spreadsheet.sheet1  # For POP Submissions
refresh_sheet = spreadsheet.worksheet("Refresh_Groups")
tuesday_sheet = spreadsheet.worksheet("Tuesday_Pop")
tracked_sheet = spreadsheet.worksheet("tracked")
ScheduledPosts = spreadsheet.worksheet("ScheduledPosts")
# For logging bot
drive_creds = service_account.Credentials.from_service_account_info(creds_dict)
drive_service = build("drive", "v3", credentials=drive_creds)



def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS

def require_admin(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        user = getattr(update, "effective_user", None)
        if not user or not is_admin(user.id):
            # Silently ignore non-admins (or send a message if you prefer)
            # await update.message.reply_text("⛔ Not authorized.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


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
    




WELCOME_TEXT = (
    """✨ Welcome to the Silk & Sin Network ✨\n

No drama. No nonsense. No scammers. No time wasters Only elegance, safety, and serious money. 💼💋\n

This is your private stage where verified, high spending buyers meet confident, professional models.\n
Our bot handles POPs, promotions, and keeps the flow smooth, so you can focus on what you do best.\n

Silk & Sin isn’t just a network…\n
It’s your VIP lounge for success. 💎\n\n"""

    "Choose one to continue:"
)

Welcome_MSG_URL = "https://imgur.com/a/MV79r1I"

def role_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Verify For the network", callback_data="role:new"),
         InlineKeyboardButton("POP Submission", callback_data="role:exp")],
        [InlineKeyboardButton("🤖 Buy a Bot", callback_data="buybot")]
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only interact in private chat
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        tracked_sheet.append_row([
            str(user.id),
            user.username or "",
            f"{user.first_name or ''} {user.last_name or ''}".strip(),
            now
        ])
    except Exception as e:
        print(f"Error logging to tracked sheet: {e}")

    # Send image first
   
    # Send welcome text + buttons
    await update.message.reply_markdown(
        WELCOME_TEXT,
        reply_markup=role_keyboard()
    )
async def handle_role_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Record role on the user
    role = "exp" if query.data == "role:exp" else "new"
    context.user_data["role"] = role

    # Back button keyboard
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data="go_back")]
    ])

    if role == "exp":
        # Experienced → send links; no waiting for verification
        await query.edit_message_text(
            "Great! Here are your POP links 👇",
            reply_markup=keyboard   # 👈 attach here
        )
        # Send links as plain text so underscores in URLs don't break Markdown
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=pop_links,
            disable_web_page_preview=True,
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=tuesday_links,
            disable_web_page_preview=True,
        )
        return

    # New → ask for a live circle verification and wait for it
    context.chat_data["awaiting_live_circle"] = True
    await query.edit_message_text(
        "🆕 **New model verification**\n\n"
        "Please send a *live circle video* (tap the mic and switch to cam) saying:\n"
        "“Hi Silk and Sin bot, today’s date showing full face.”\n\n"
        "Once I receive it, I’ll pass it to an admin for approval.",
        parse_mode="Markdown",
        reply_markup=keyboard   # 👈 also attach here
    )
    

async def handle_buybot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    message = (
        "💼 **Custom Bot Pricing** 💼\n\n"
        "Here’s what you can get:\n\n"
        "🔹 **Basic Bot** – $100\n"
        " • Accept verifications\n"
        " • POP submission approve/reject\n"
        " • POP submission logging\n"
        " • Auto muting\n\n"
        "🔹 **Standard Bot** – $200\n"
        " • Google Sheets logging\n"
        " • Auto-mute for missed POPs\n"
        " • Auto Unmute after approval\n" 
        " • Reminders system\n"
        " • Monthly refresh logging,muting,unmuting\n\n"
        "🔹 **Premium Bot** – $400\n"
        " • Everything in Standard\n"
        " • Auto-posting ads (text, photo, video)\n"
        " • Google Drive integration\n"
        " • Vip Games\n"
        " • Dashboard (stats, charts)\n"
        " • Priority support\n\n"
        "🚀 Save time, grow your network, and stay scam-free with automation.\n\n"
        "👉 DM @sexydolladmin to order your bot today."
    )

    # Add Back button here
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back", callback_data="go_back")]
    ])

    await query.edit_message_text(message, parse_mode="Markdown", reply_markup=keyboard)
    
async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        text=WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=role_keyboard()
    )

async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    if not context.chat_data.get("awaiting_live_circle"):
        return

    vn = update.message.video_note
    if not vn:
        return

    context.chat_data["awaiting_live_circle"] = False
    user = update.effective_user

    file = await vn.get_file()
    path = await file.download_to_drive()

    caption = (
        f"🆕 Live circle verification from @{user.username or user.id}\n"
        f"User ID: `{user.id}`\n\n"
        f"Admin: approve with `/approve_new_{user.id}` or reject with `/reject_new_{user.id}`"
    )

    try:
        # Send as normal video so admin sees caption
        with open(path, "rb") as f:
            await context.bot.send_video(
                chat_id=ADMIN_USER_ID,
                video=f,
                caption=caption,
                parse_mode="Markdown"
            )
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

    # Mark as pending
    context.bot_data.setdefault("pending_new", set()).add(user.id)

    # Step 1 done ✅ – now ask for adult link
    context.chat_data["awaiting_adult_link"] = True
    await update.message.reply_text(
        "✅ Thanks for sending your live circle verification!\n\n"
        "📎 Please send your *verified adult profile link* (e.g., OnlyFans, Fansly, etc). (dont send any pictures, text only)",
        parse_mode="Markdown"
    )
# (optional) also accept normal video as fallback if the user can’t send a circle video
async def handle_video_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    if not context.chat_data.get("awaiting_live_circle"):
        return
    vid = update.message.video
    if not vid:
        return
    context.chat_data["awaiting_live_circle"] = False

    user = update.effective_user
    caption = (
        f"🆕 *Fallback video* verification from @{user.username or user.id}\n"
        f"User ID: {user.id}"
    )

    file = await vid.get_file()
    path = await file.download_to_drive()
    try:
        with open(path, "rb") as f:
            await context.bot.send_video(chat_id=ADMIN_USER_ID, video=f, caption=caption, parse_mode="Markdown")
    finally:
        import os
        try: os.remove(path)
        except Exception: pass

    await update.message.reply_text("✅ Thanks! I sent your video to an admin for review.")
    
    
async def handle_adult_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.chat_data.get("awaiting_adult_link"):
        return

    link = update.message.text.strip()
    user = update.effective_user

    context.chat_data["awaiting_adult_link"] = False

    # Forward link to admin
    await context.bot.send_message(
        chat_id=ADMIN_USER_ID,
        text=f"🔗 Verified adult link from @{user.username or user.id} (ID: `{user.id}`):\n{link}",
        parse_mode="Markdown"
    )

    await update.message.reply_text("🧾 Thanks! Your adult link was sent to the admin along with your live circle video.")

def _admin_only(user_id: int) -> bool:
    return user_id == ADMIN_USER_ID

async def approve_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin gate
    if not _admin_only(update.effective_user.id):
        return

    match = re.match(r"^/approve_new_(\d+)$", update.message.text.strip())
    if not match:
        await update.message.reply_text("Usage: /approve_new_<user_id>")
        return

    target_id = int(match.group(1))
    pending = context.bot_data.setdefault("pending_new", set())

    if target_id not in pending:
        await update.message.reply_text("ℹ️ That user isn’t marked as pending, sending links anyway…")

    try:
        # Send welcome message
        await context.bot.send_message(
            chat_id=target_id,
            text=(
                  "✅ *You’re verified!*\n\n"
                  "💎 Welcome to the Silk & Sin Network 💎\n"
                  "Join the model chat:\n"
                  "👉 https://t.me/+Mw5-xF7ZvMw3MDkx\n\n"
                  "📌 Below are your POP links. Please promote these links where you can attract buyers, "
                  "and then send the screenshot to this bot using /submitpop.\n\n"
                  "📖 *POP Rules:*\n"
                  "1️⃣ Links must be *clearly visible* in the screenshot (no hiding, blurring, or cropping).\n"
                  "2️⃣ Submit on time (Friday & Tuesday deadlines apply).\n"
                  "3️⃣ No editing, cropping, or reusing old POPs.\n"
                  "4️⃣ Keep POP links in your preview channel for *at least 12 hours*.\n"
                  "5️⃣ Failure to submit on time may result in muting or removal.\n"
                  "6️⃣ Always promote links in quality spaces where buyers are active."
                
        ),
           parse_mode="Markdown",
           disable_web_page_preview=True
        )

        # Send POP links
        await context.bot.send_message(
            chat_id=target_id,
            text=pop_links,
            parse_mode="HTML",
            disable_web_page_preview=True
        )

        # Send Tuesday links
        await context.bot.send_message(
            chat_id=target_id,
            text=tuesday_links,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        await context.bot.send_message(
            chat_id=target_id,
            text=refresh_links,
            parse_mode="HTML",
            disable_web_page_preview=True
        )
        
        pending.discard(target_id)
        await update.message.reply_text(f"✅ Approved and sent links to {target_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Couldn’t DM {target_id}: {e}")



async def reject_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Admin gate
    if not _admin_only(update.effective_user.id):
        return

    match = re.match(r"^/reject_new_(\d+)$", update.message.text.strip())
    if not match:
        await update.message.reply_text("Usage: /reject_new_<user_id>")
        return

    target_id = int(match.group(1))
    pending = context.bot_data.setdefault("pending_new", set())

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text="❌ Your verification request was *rejected*.\n\nPlease contact @sexydolladmin if you think this was a mistake.",
            parse_mode="Markdown"
        )
        pending.discard(target_id)
        await update.message.reply_text(f"❌ Rejected and notified {target_id}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Couldn’t DM {target_id}: {e}")
        
async def list_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # optional helper: /pending_new
    uid = update.effective_user.id
    if not _admin_only(uid):
        return
    pending = context.bot_data.get("pending_new", set())
    if not pending:
        await update.message.reply_text("🟩 No pending new‑model verifications.")
        return
    await update.message.reply_text("🟨 Pending user IDs:\n" + "\n".join(map(str, sorted(pending))))
    
#POP + Refresh Selection
async def submitpop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Friday POP", callback_data='pop_friday')],
        [InlineKeyboardButton("Tuesday POP", callback_data='pop_tuesday')],
        [InlineKeyboardButton("Monthly Refresh", callback_data='monthly_refresh')]  # ✅ new button
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Which one are you submitting?", reply_markup=reply_markup)


# Handle button presses
async def handle_pop_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "monthly_refresh":
        # ✅ trigger refresh flow
        await query.edit_message_text("Please type 'added' if you’ve completed the monthly refresh.")
        context.chat_data["awaiting_refresh"] = True
        return

    # Otherwise POP handling
    pop_day = 'friday' if query.data == 'pop_friday' else 'tuesday'
    context.user_data['pop_day'] = pop_day
    context.chat_data["expecting_photo"] = True

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
            f"✅ Approve: /approve__{user.id}__{pop_day}\n"
            f"❌ Reject: /reject__{user.id}__{pop_day}"
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
        # drive_link = upload_to_drive(data["username"], data["filename"], data["filepath"])
        # now = datetime.now()
        # date_str = now.strftime('%Y-%m-%d')
        # time_str = now.strftime('%H:%M:%S')

        # Log to correct sheet
        if pop_day == "tuesday":
            tuesday_sheet.append_row([
                data["username"],
                str(data["user_id"]),
                date_str,
                time_str,
                #drive_link
            ])
            unmute_groups = TUESDAY_GROUP_IDS
        else:
            sheet.append_row([
                data["username"],
                str(data["user_id"]),
                date_str,
                time_str,
                #drive_link
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

        # Check if they were "new"
        role = context.bot_data.get("user_roles", {}).get(int(user_id))
        if role == "new":
            extra_note = "\n\n📌 Please request to join the groups through the same links."
        else:
            extra_note = ""

        # Notify
        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"✅ Your {data['pop_day'].capitalize()} POP has been approved and logged."
                 f"\n✅ You have been unmuted in the relevant promo groups. Thanks for submitting your POP!"
                 f"{extra_note}"
        )
        await update.message.reply_text(f"✅ Approved and uploaded for @{data['username']}.")
        del context.bot_data[key]

    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return

    match = re.match(r"/reject_(\d+)_(friday|tuesday)", update.message.text.strip())
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


async def mute_non_submitters_friday(context: ContextTypes.DEFAULT_TYPE):
    try:
        submitted_ids = get_all_submitted_user_ids(sheet)
        tracked_users = get_tracked_user_ids(sheet)

        muted = 0
        errors = 0

        for user_id in tracked_users:
            if user_id not in submitted_ids:
                # Mute in all Friday groups
                for group_id in GROUP_IDS:
                    try:
                        await context.bot.restrict_chat_member(
                            chat_id=group_id,
                            user_id=int(user_id),
                            permissions=ChatPermissions(
                                can_send_messages=False,
                                can_send_media_messages=False,
                                can_send_other_messages=False,
                                can_add_web_page_previews=False,
                            ),
                        )
                    except Exception as e:
                        errors += 1
                        print(f"❌ Error muting {user_id} in {group_id}: {e}")

                # Send ONE message after muting across all groups
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="🔕 You've been muted in Friday pop groups. Please send your POP to this bot to get unmuted.",
                    )
                    muted += 1
                except Exception as e:
                    print(f"❌ Error sending mute DM to {user_id}: {e}")

        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"📊 Friday runcheck: muted {muted} user(s). Errors: {errors}."
        )

    except Exception as e:
        # Bubble up any unexpected failures to admin
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"❌ Friday runcheck failed: {e}"
                            )
async def runcheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    await mute_non_submitters_friday(context)
    await update.message.reply_text("✅ Friday runcheck executed.")

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
                        "Please promote the groups using the links down below and send your pop to this bot to start posting again.\n\n"
                    
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
    
def get_last_tuesday():
    # Monday=0, Tuesday=1, ... Sunday=6
    today = datetime.today()
    offset = (today.weekday() - 1) % 7   # 1 == Tuesday
    last_tuesday = today - timedelta(days=offset)
    return datetime.combine(last_tuesday.date(), datetime.min.time())

def get_all_submitted_user_ids_tuesday(tuesday_sheet):
    records = tuesday_sheet.get_all_records()
    submitted_ids = set()

    start_of_cycle = get_last_tuesday()

    for row in records:
        try:
            date_str = row["Date"]
            time_str = row["Time"]
            ts = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            if ts >= start_of_cycle:
                submitted_ids.add(str(row["User ID"]))
        except Exception as e:
            print(f"Skipping row (Tuesday) due to error: {e}")

    return submitted_ids
    
def get_tracked_user_tuesday_ids(tuesday_sheet):
    records = tuesday_sheet.get_all_records()
    return {str(row["User ID"]) for row in records if "User ID" in row}
    
async def mute_non_submitters_tuesday(context: ContextTypes.DEFAULT_TYPE):
    try:
        submitted_ids = get_all_submitted_user_ids_tuesday(tuesday_sheet)
        tracked_users = get_tracked_user_tuesday_ids(tuesday_sheet)

        muted, errors = 0, 0
        for user_id in tracked_users:
            if user_id not in submitted_ids:
                # Mute in all Tuesday groups
                for group_id in TUESDAY_GROUP_IDS:
                    try:
                        await context.bot.restrict_chat_member(
                            chat_id=group_id,
                            user_id=int(user_id),
                            permissions=ChatPermissions(
                                can_send_messages=False,
                                can_send_media_messages=False,
                                can_send_other_messages=False,
                                can_add_web_page_previews=False
                            )
                        )
                    except Exception as e:
                        errors += 1
                        print(f"❌ Error muting {user_id} in {group_id}: {e}")

                # Send one message AFTER muting in all groups
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="🔇 You’ve been muted in Tuesday POP groups. Please send your POP to get unmuted!"
                    )
                    muted += 1
                except Exception as e:
                    print(f"❌ Error sending mute message to {user_id}: {e}")

        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"🔇 Tuesday runcheck: muted {muted} user(s). Errors: {errors}."
        )

    except Exception as e:
        print(f"Tuesday mute task failed: {e}")
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"⚠️ Tuesday mute task failed: {e}"
        )
async def runcheck2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    await mute_non_submitters_tuesday(context)
    await update.message.reply_text("✅ Tuesday runcheck executed.")

async def send_tuesday_pop_reminder(context: ContextTypes.DEFAULT_TYPE):
   
    submitted_ids =  get_all_submitted_user_ids_tuesday(tuesday_sheet)
    tracked_users = get_tracked_user_tuesday_ids(tuesday_sheet)

    for user_id in tracked_users:
        if user_id not in submitted_ids:
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=(
                        "📌 *Reminder*: You haven't submitted your POP for this week!\n\n"
                        "Please promote the groups and send your pop to this bot and get unmuted asap.Please use the links down below.\n\n"
                    
                    ),
                    parse_mode='Markdown',
                )
                # Second message: Group links
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=tuesday_links,  # Assuming this is a string of links
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"⚠️ Failed to remind user {user_id}: {e}")
    
    

async def ask_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # If bot is waiting for a special input, skip auto-answer
    if context.chat_data.get("awaiting_adult_link") \
       or context.chat_data.get("awaiting_live_circle") \
       or context.chat_data.get("expecting_photo") \
       or context.chat_data.get("awaiting_refresh"):
        return

    question = update.message.text.strip()

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the official assistant of the Silk & Sin Network. "
                        "Answer ONLY questions about POP (Proof of Promotion), Silk & Sin rules, "
                        "and how to remain unmuted.\n\n"
                        "POP Process:\n"
                        "- Use /submitpop to submit POP.\n"
                        "- Initial POP unlocks you until the next cycle.\n"
                        "- After that, you must submit weekly POP.\n"
                        "- Missing POP → muted until next valid submission.\n\n"
                        "POP Rules:\n"
                        "1. Links must be clearly visible in the screenshot.\n"
                        "2. Submit on time (Friday & Tuesday deadlines).\n"
                        "3. No reusing old POPs.\n"
                        "4. Keep links in preview channel for 12+ hours.\n"
                        "5. Promote where genuine buyers are active.\n\n"
                        "Silk & Sin:\n"
                        "- No drama, scam-free, high-spending verified buyers.\n"
                        "- Safe environment for models.\n"
                        "- Automated fairness with POP enforcement."
                    ),
                },
                {"role": "user", "content": question},
            ],
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
                        can_add_web_page_previews=True,
                        can_invite_users=True
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
                telegram_ids.add(str(row["User_ID"]))   # ✅ use telegram_ids not user_ids
        except Exception as e:
            print(f"⚠️ Skipping row due to error: {e}, row: {row}")

    print(f"✅ Found {len(telegram_ids)} refresh users: {telegram_ids}")
    return telegram_ids
    

def get_all_tracked_user_ids(refresh_sheet):
    records = refresh_sheet.get_all_records()
    return {str(row["User_ID"]) for row in records if "User_ID" in row}

from telegram.error import Forbidden, BadRequest, TelegramError
from telegram import ChatPermissions 

# Mute but still allow adding members
MUTED_PERMISSIONS = ChatPermissions(
    can_send_messages=False,
    can_send_media_messages=False,
    can_send_polls=False,
    can_send_other_messages=False,
    can_add_web_page_previews=False,
    can_invite_users=True   # ✅ allow adding buyers
)
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
                        print(f"⚠️ Failed to fetch member status for user {telegram_id} in group {group_id}: {e}")
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
                        permissions=MUTED_PERMISSIONS
                    )
                    print(f"✅ Muted {telegram_id} in {group_title}")

                    # Notify the user
                    try:
                        await context.bot.send_message(
                            chat_id=int(telegram_id),
                            text=(
                                f"🔇 You’ve been muted in *{group_title}* for not doing the monthly refresh!\n\n"
                                "📌 Please add buyers and submit your refresh to this bot once done.\n"
                                "Use the command /submitpop ✅"
                            ),
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
    scheduler.add_job(send_pop_reminder,CronTrigger(day_of_week="sun,mon", hour=20, minute=0),args=[app],timezone="UTC")
    scheduler.add_job(send_tuesday_pop_reminder,CronTrigger(day_of_week="wed,sat", hour=20, minute=0),args=[app],timezone="UTC")
    scheduler.add_job(send_refresh_reminders, CronTrigger(day=25, hour=8), args=[app])
    scheduler.add_job(check_vip_expiry, CronTrigger(minute="*/30"), args=[app])
    scheduler.add_job(mute_non_refresh_submitters, CronTrigger(day=1, hour=0, minute=0), args =[app])  # Midnight on 1st
    # Example: 00:05 on Wednesday (i.e., right after Tuesday ends)
    scheduler.add_job(mute_non_submitters_tuesday, CronTrigger(day_of_week='mon', hour=23, minute=59),args=[app])
    scheduler.add_job(mute_non_submitters_friday, CronTrigger(day_of_week='thu', hour=23, minute=59),args=[app])
    scheduler.start()
    print("Scheduler started")


async def friday_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(pop_links, parse_mode="HTML", disable_web_page_preview=True)

async def tuesdaypop_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(tuesday_links, parse_mode="HTML", disable_web_page_preview=True)


def main():

 async def post_init(app):  
   await on_startup(app)  

 app = ApplicationBuilder().token(BOT_TOKEN).post_init(on_startup).build()  
 app.add_handler(CommandHandler("start", start))

# Inline button handlers (role choice, back, buybot, etc.)
 app.add_handler(CallbackQueryHandler(handle_role_choice, pattern="^role:"))
 app.add_handler(CallbackQueryHandler(handle_buybot, pattern="^buybot$"))
 app.add_handler(CallbackQueryHandler(handle_back, pattern="^go_back$"))
 app.add_handler(CallbackQueryHandler(handle_pop_selection, pattern='^pop_'))
 app.add_handler(CallbackQueryHandler(handle_pop_selection, pattern="^(pop_|monthly_refresh)"))
    

# Core commands
 app.add_handler(CommandHandler("pending_new", list_pending))
 app.add_handler(CommandHandler("broadcast", broadcast))
 app.add_handler(CommandHandler("submitpop", submitpop))
 app.add_handler(CommandHandler("getid", getid))
 app.add_handler(CommandHandler("friday", friday_links))
 app.add_handler(CommandHandler("tuesday", tuesdaypop_links))
 app.add_handler(CommandHandler("runcheck", runcheck))
 app.add_handler(CommandHandler("runcheck2", runcheck2))
 app.add_handler(CommandHandler("runfresh", run_fresh_command))
 app.add_handler(CommandHandler("testreminder", test_pop_reminder))
 app.add_handler(CommandHandler("vip_add", vip_add))
 app.add_handler(CommandHandler("refresh", refresh_command))   # ✅ moved higher

# Approval/reject handlers
 app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/approve_\d+_(friday|tuesday)"), approve))
 app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/reject_\d+_(friday|tuesday)"), reject))
 app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/approve_new_\d+$"), approve_new))
 app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/reject_new_\d+$"), reject_new))
 app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/approverefresh_\d+$"), approve_refresh))
 app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^/rejectrefresh_\d+$"), reject_refresh))

# POP "added" handler
 app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"(?i)^added$") & filters.ChatType.PRIVATE, handle_refresh_added), group=0)

# Media handlers
 app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
 app.add_handler(MessageHandler(filters.VIDEO, handle_video))
 app.add_handler(MessageHandler(filters.VIDEO_NOTE & filters.ChatType.PRIVATE, handle_video_note))
 app.add_handler(MessageHandler(filters.VIDEO & filters.ChatType.PRIVATE, handle_video_fallback))

# Adult link handler (must be after others)
 app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_adult_link))

  
 app.run_polling()

if __name__ == "__main__":
   main()

