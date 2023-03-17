import requests


class TelegramClient:
    """Class to handle interactions with the Telegram Bot API."""
    def __init__(self, token):
        self.token = token
        self.base_url = f'https://api.telegram.org/bot{self.token}'

    def send_message(self, chat_id, text):
        """Send a message to the specified Telegram chat ID."""
        url = f'{self.base_url}/sendMessage'
        params = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        response = requests.post(url, params=params)

        if response.status_code != 200:
            raise Exception(f'Telegram API returned status code {response.status_code}')

        result = response.json()
        if not result['ok']:
            raise Exception(f'Telegram API returned error message: {result["description"]}')