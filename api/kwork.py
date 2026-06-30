from dataclasses import dataclass
from html import escape

import requests


class KworkClient:
    """Fetch and format Kwork orders."""

    def __init__(self):
        self.base_url = "https://kwork.ru"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "KworkWatcher/1.0 (+https://github.com/)",
                "Accept": "application/json, text/plain, */*",
            }
        )

    def get_new_orders(self, category_id):
        orders = []
        url = f"{self.base_url}/projects"
        payload = {"fc": category_id, "view": 0, "page": 1}
        try:
            response = self.session.post(url, data=payload, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Failed to fetch Kwork category {category_id}: {exc}") from exc

        try:
            result = response.json()
        except ValueError as exc:
            raise RuntimeError(f"Kwork returned a non-JSON response for category {category_id}.") from exc

        wants = ((result.get("data") or {}).get("wants"))
        if not isinstance(wants, list):
            raise RuntimeError(f"Kwork response for category {category_id} does not contain a valid order list.")

        for order_data in wants:
            if not isinstance(order_data, dict):
                continue
            order_id = order_data.get("id")
            if order_id is None:
                continue
            try:
                normalized_order_id = int(order_id)
            except (TypeError, ValueError):
                continue
            orders.append(
                KworkOrder(
                    id=normalized_order_id,
                    name=order_data.get("name", "Untitled order"),
                    category=self._get_category_name(order_data, category_id),
                    price=KworkOrder.parse_price(order_data.get("priceLimit")),
                    description=order_data.get("description", ""),
                    url=f"{self.base_url}/projects/{normalized_order_id}",
                    price_limit=KworkOrder.parse_price(order_data.get("possiblePriceLimit")),
                )
            )

        return orders

    def _get_category_name(self, order_data, category_id):
        category = order_data.get("categoryName")
        if category:
            return category

        parent_category = order_data.get("parentCategoryName")
        attrs = order_data.get("attrs") or {}
        attr_category = attrs.get("categoryName")
        parts = [part for part in (parent_category, attr_category) if part]
        if parts:
            return " / ".join(parts)
        return f"Category {category_id}"

    def format_order_message(self, order):
        message = "<b>Новый заказ на Kwork</b>\n\n"
        message += f"<b>Название:</b> {escape(order.name)}\n"
        message += f"<b>Бюджет:</b> {escape(order.display_price())}"
        if order.price_limit and order.price_limit != order.price:
            message += f" (до {order.price_limit} руб.)"
        message += f"\n<b>Категория:</b> {escape(order.category)}\n\n"
        message += "<b>Описание:</b>\n"
        message += f"<i>{escape(order.short_description())}</i>\n\n"
        message += f'<a href="{escape(order.url)}">Открыть заказ на Kwork</a>'
        return message


@dataclass
class KworkOrder:
    id: int
    name: str
    category: str
    price: int
    description: str
    url: str
    price_limit: int = None

    @staticmethod
    def parse_price(value):
        if value in (None, ""):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    def display_price(self):
        if self.price is None:
            return "Не указан"
        return f"{self.price} руб."

    def short_description(self, limit: int = 700):
        cleaned = " ".join((self.description or "").split())
        if not cleaned:
            return "Описание не указано."
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1].rstrip() + "…"
