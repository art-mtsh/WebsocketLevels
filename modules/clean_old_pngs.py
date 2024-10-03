import os
import glob
import telebot
import threading

PERSONAL_TELEGRAM_TOKEN = os.getenv('PERSONAL_TELEGRAM_TOKEN')
personal_bot = telebot.TeleBot(PERSONAL_TELEGRAM_TOKEN)
personal_id = int(os.getenv('PERSONAL_ID'))

def clean_old_files(directory, prefix, extension='.png'):
    pattern = os.path.join(directory, f"{prefix}*{extension}")
    files_to_remove = glob.glob(pattern)
    for file_path in files_to_remove:
        try:
            os.remove(file_path)
        except Exception as e:
            personal_message = f"⚙️ Failed to remove file {file_path}: {e}"
            personal_bot.send_message(chat_id=personal_id, text=personal_message)
            print(personal_message)

    tr = len([thread.name for thread in threading.enumerate() if thread.is_alive()])
    personal_message = (f"⚙️ ({tr} threads) {len(files_to_remove)} images ({prefix}) successfully removed.")
    print(personal_message)