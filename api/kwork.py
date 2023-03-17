import requests


class KworkClient:
    """Class to handle interactions with the Kwork API."""
    def __init__(self):
        self.base_url = 'https://kwork.ru'

    def get_new_orders(self, category_id):
        """Retrieve new Kwork orders for the specified category."""
        orders = []
        url = f'{self.base_url}/projects'
        payload = {'fc': category_id, 'view': 0, 'page': 1}
        response = requests.post(url, data=payload)

        if response.status_code != 200:
            raise Exception(f'Kwork API returned status code {response.status_code}')

        result = response.json()
        for order_data in result['data']['wants']:
            order = KworkOrder(
                id=order_data['id'],
                name=order_data['name'],
                category=order_data['categoryName'],
                price=order_data.get('priceLimit'),
                description=order_data['description'],
                url=f'{self.base_url}/projects/{order_data["id"]}',
                price_limit=order_data.get('possiblePriceLimit'),
            )
            orders.append(order)

        return orders

    def filter_new_orders(self, orders, sent_order_ids):
        """Filter out orders that have already been sent based on their ID."""
        new_orders = []
        for order in orders:
            if order.id not in sent_order_ids:
                new_orders.append(order)
        return new_orders

    def format_order_message(self, order):
        """Format a Kwork order as a Telegram message."""
        message = f'<b>{order.name}</b>\n\n'
        message += f'<b>Price:</b> {order.price} rub'
        if order.price_limit and order.price_limit != order.price:
            message += f" (max {order.price_limit} rub)"
        message += f'\n<b>Category:</b> {order.category}\n\n'
        message += f'<b>Description:</b>\n<i>{order.description}</i>\n\n'
        message += f'<a href="{order.url}">View on Kwork.ru</a>'
        return message


class KworkOrder:
    """Class to represent a Kwork order."""
    def __init__(self, id, name, category, price, description, url, price_limit=None):
        self.id = id
        self.name = name
        self.category = category
        self.price = int(float(price))
        self.description = description
        self.url = url
        self.price_limit = int(float(price_limit))

    def __str__(self):
        return f'Order {self.id}: {self.name} ({self.category}) {self.price}rub'

    def __repr__(self):
        return f'KworkOrder(id={self.id}, name={self.name}, category={self.category}, price={self.price})'