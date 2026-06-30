import json
import os
import tempfile
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Dict


class StateStore:
    def __init__(self, path: str, max_orders: int = 5000):
        self.path = path
        self.max_orders = max_orders
        self.orders: "OrderedDict[str, Dict[str, str]]" = OrderedDict()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as file:
                    payload = json.load(file)
            except json.JSONDecodeError as exc:
                raise ValueError(f"State file is not valid JSON: {self.path}") from exc

            if not isinstance(payload, dict):
                raise ValueError(f"State file must contain a JSON object: {self.path}")
            loaded_orders = payload.get("orders", {})
            if not isinstance(loaded_orders, dict):
                raise ValueError(f"State file has an invalid 'orders' section: {self.path}")
            normalized_orders = []
            for order_id, metadata in loaded_orders.items():
                if not isinstance(metadata, dict):
                    continue
                normalized_orders.append((str(order_id), metadata))

            self.orders = OrderedDict(
                sorted(normalized_orders, key=lambda item: item[1].get("tracked_at", ""))
            )
            return

        self._migrate_from_legacy_text()

    def save(self):
        self._prune()
        payload = {
            "version": 1,
            "orders": self.orders,
        }
        directory = os.path.dirname(self.path) or "."
        os.makedirs(directory, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
            temp_path = file.name
        os.replace(temp_path, self.path)

    def has_orders(self) -> bool:
        return bool(self.orders)

    def count(self) -> int:
        return len(self.orders)

    def is_known(self, order_id: int) -> bool:
        return str(order_id) in self.orders

    def mark_known(self, order, status: str, timestamp: float):
        self.orders[str(order.id)] = {
            "id": order.id,
            "name": order.name,
            "category": order.category,
            "price": order.price,
            "url": order.url,
            "status": status,
            "tracked_at": _isoformat(timestamp),
        }
        self.orders.move_to_end(str(order.id))
        self._prune()

    def _prune(self):
        while len(self.orders) > self.max_orders:
            self.orders.popitem(last=False)

    def _migrate_from_legacy_text(self):
        legacy_path = "sent_orders.txt"
        if not os.path.exists(legacy_path):
            return

        with open(legacy_path, "r", encoding="utf-8") as file:
            lines = [line.strip() for line in file if line.strip()]

        timestamp = _isoformat()
        for raw_id in lines[-self.max_orders:]:
            try:
                order_id = int(raw_id)
            except ValueError:
                continue
            self.orders[str(order_id)] = {
                "id": order_id,
                "name": "Migrated legacy order",
                "category": "Unknown",
                "price": None,
                "url": "",
                "status": "migrated",
                "tracked_at": timestamp,
            }


def _isoformat(timestamp: float = None) -> str:
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp is not None else datetime.now(timezone.utc)
    return dt.isoformat()
