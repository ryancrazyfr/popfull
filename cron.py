import os
import requests

BOT_TOKEN = os.environ['BOT_TOKEN']
ADMIN_ID = "6276794389"  # Your ID

# Trigger the /runcheck command as if you sent it
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
requests.post(url, data={"chat_id": ADMIN_ID, "text": "/runcheck"})
