import re

with open("bot.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace user_data_store = {}
content = re.sub(
    r"user_data_store\s*=\s*\{\}",
    "from db import user_data_store, admins, save_db",
    content
)

# Update ADMIN_ID checks to allow any admin in admins or ADMIN_ID
# Function to replace `chat_id != ADMIN_ID` with `chat_id != ADMIN_ID and str(chat_id) not in admins`
content = content.replace("if chat_id != ADMIN_ID:", "if chat_id != ADMIN_ID and str(chat_id) not in admins:")
content = content.replace("if chat_id == ADMIN_ID:", "if chat_id == ADMIN_ID or str(chat_id) in admins:")

# Save db periodically in background_monitor
monitor_str = "async def background_monitor(context: ContextTypes.DEFAULT_TYPE):"
new_monitor_str = "async def background_monitor(context: ContextTypes.DEFAULT_TYPE):\n    save_db()"
if monitor_str in content and new_monitor_str not in content:
    content = content.replace(monitor_str, new_monitor_str)

with open("bot.py", "w", encoding="utf-8") as f:
    f.write(content)

print("bot.py updated.")
