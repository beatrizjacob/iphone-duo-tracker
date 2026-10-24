#!/usr/bin/env python3
"""Private local Telegram setup. No token appears in command arguments or files."""
import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
from checker import telegram


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True)
    args = parser.parse_args()
    if not shutil.which('gh'):
        raise SystemExit('GitHub command-line app is missing. Ask Codex to finish setup.')
    print('Telegram setup for ' + args.repo)
    print('Create your bot with @BotFather, then send /start in your own bot chat.')
    print('The token stays in memory and is uploaded only as a GitHub Actions secret.')
    token = getpass.getpass('Paste the Telegram bot token (hidden), then press Return: ').strip()
    if not token:
        raise SystemExit('No token entered; nothing changed.')
    identity = telegram('getMe', {}, token)
    print('Connected bot: @' + identity.get('username', '(username unavailable)'))
    chats = {}
    while not chats:
        updates = telegram('getUpdates', {'timeout': 0, 'allowed_updates': ['message']}, token)
        for update in updates:
            chat = update.get('message', {}).get('chat', {})
            if chat.get('type') == 'private':
                chats[chat['id']] = chat
        if not chats:
            input('No private messages found. Send /start to this bot in Telegram, then press Return here: ')
    print('\nChoose YOUR OWN private chat for the alerts:')
    choices = sorted(chats)
    for index, chat_id in enumerate(choices, start=1):
        chat = chats[chat_id]
        label = ' '.join(str(chat.get(key) or '') for key in ('first_name', 'last_name')).strip()
        print(f"  {index}. {label} @{chat.get('username') or '(no username)'}")
    answer = input('Your chat number [1]: ').strip() or '1'
    try:
        index = int(answer) - 1
        if index < 0: raise ValueError()
        chat_id = choices[index]
    except (ValueError, IndexError):
        raise SystemExit('Invalid selection; nothing changed.') from None
    for name, value in [('TELEGRAM_BOT_TOKEN', token), ('TELEGRAM_CHAT_ID', str(chat_id))]:
        result = subprocess.run(['gh', 'secret', 'set', name, '--repo', args.repo],
                                input=value, text=True, capture_output=True)
        if result.returncode:
            raise SystemExit(f'Could not save {name}. Ask Codex to check repository permissions.')
    telegram('sendMessage', {'chat_id': chat_id, 'text': 'iPhone stock tracker setup is connected. This is a setup test, not a stock alert.'}, token)
    # Receipt contains no token, chat ID, names, or message content.
    from pathlib import Path
    Path('.setup-complete.json').write_text(json.dumps({'repo': args.repo, 'secrets_saved': True, 'test_sent': True}))
    print('\nDone. Both GitHub secrets are saved and a Telegram setup message was sent.')
    print('Return to Codex and say: Telegram setup done.')

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, KeyboardInterrupt):
        raise SystemExit('Setup interrupted or Telegram unavailable. No token has been printed or saved locally.') from None
