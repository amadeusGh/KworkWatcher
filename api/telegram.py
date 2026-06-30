import requests


class TelegramClient:
    """Class to handle interactions with the Telegram Bot API."""
    def __init__(self, token):
        self.token = token
        self.base_url = f'https://api.telegram.org/bot{self.token}'
        self.session = requests.Session()

    def send_message(self, chat_id, text):
        """Send a message to the specified Telegram chat ID."""
        url = f'{self.base_url}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True,
        }
        try:
            response = self.session.post(url, data=payload, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f'Telegram request failed: {exc}') from exc

        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError('Telegram returned a non-JSON response.') from exc
        if not result['ok']:
            raise RuntimeError(f'Telegram API error: {result["description"]}')
