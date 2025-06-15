# Telegram POP Bot

This bot tracks POP (Proof of Promo) screenshots, uploads to Google Drive, auto-mutes sellers who don't submit, and supports admin approval.

## Features
- Google Drive upload per user
- Telegram group auto mute/unmute
- Admin approval via /approve_/reject_
- Cron support

## Deploy on Render
1. Push to GitHub
2. Add Environment Variables:
   - `BOT_TOKEN`
   - `GOOGLE_JSON` (as one-line JSON)
3. Use `start.sh` as Start Command
4. Add a Background Worker with `cron.py` (optional) to auto run `/runcheck`

