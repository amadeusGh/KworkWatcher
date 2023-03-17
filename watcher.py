import time
import argparse

from api.kwork import KworkClient, KworkOrder
from api.telegram import TelegramClient


def get_sent_order_ids():
    """Read in sent order IDs and only keep the last 1000."""
    try:
        with open('sent_orders.txt', 'r') as f:
            lines = f.readlines()
            if len(lines) > 1000:
                lines = lines[-1000:]
            lines_stripped = [line.strip() for line in lines]
            ids = map(int, lines_stripped)
            return set(ids)
    except FileNotFoundError:
        return set()


def main(args):
    # Set up the Kwork and Telegram API clients
    kwork_client = KworkClient()
    telegram_client = TelegramClient(args.token)

    sent_order_ids = get_sent_order_ids()

    while True:
        # Get new orders from Kwork for each specified category
        new_orders = []
        for i, category_id in enumerate(args.categories):
            orders = kwork_client.get_new_orders(category_id)
            new_orders += kwork_client.filter_new_orders(orders, sent_order_ids)

            # Add a pause after each category parse, except for the last one
            if i < len(args.categories) - 1:
                time.sleep(2.5)

        # Send notifications for new orders to Telegram
        for i, order in enumerate(new_orders):
            try:   
                message = kwork_client.format_order_message(order)
                telegram_client.send_message(args.chat_id, message)
                sent_order_ids.add(order.id)
                print(f'Sent notification for order {order.id}')
            except Exception as e:
                print(f'Error occurred while sending Telegram message: {e}')

            # Add a pause after each message, except for the last one
            if i < len(new_orders) - 1:
                time.sleep(1)

        # Write the updated set of sent order IDs back to the file
        with open('sent_orders.txt', 'w') as f:
            f.write('\n'.join(map(str, sent_order_ids)))

        # Wait for the specified interval before checking for new orders again
        print(f'Sleeping for {args.interval} seconds before checking for new orders.')
        time.sleep(args.interval)


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='This is a script for monitoring new orders on kwork.ru and sending notifications to Telegram.')
    parser.add_argument('--token', type=str, required=True, help='Telegram bot token')
    parser.add_argument('--chat_id', type=int, required=True, help='Telegram chat ID')
    parser.add_argument('--categories', type=int, nargs='+', required=True, help='List of kwork categories IDs')
    parser.add_argument('--interval', type=int, help='Interval between each check in seconds', default=300)
    args = parser.parse_args()

    main(args)