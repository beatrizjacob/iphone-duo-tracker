"""Find your private chat ID locally without putting a token in shell history."""
import getpass
from checker import telegram

token = getpass.getpass('Bot token (hidden): ')
updates = telegram('getUpdates', {'timeout': 0, 'allowed_updates': ['message']}, token)
chats = {m['message']['chat']['id'] for m in updates if m.get('message', {}).get('chat', {}).get('type') == 'private'}
if not chats:
    print('Open your bot in Telegram, send /start, then run this helper again.')
else:
    print('Private chat IDs (choose your own):', ', '.join(str(x) for x in sorted(chats)))
    print('Add your own ID as TELEGRAM_CHAT_ID in GitHub Actions secrets.')
