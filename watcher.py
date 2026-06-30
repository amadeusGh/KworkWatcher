import argparse
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from api.kwork import KworkClient, KworkOrder
from api.telegram import TelegramClient
from config import load_runtime_config
from state_store import StateStore


LOGGER = logging.getLogger("kwork_watcher")


@dataclass
class RuntimeSettings:
    token: str
    chat_id: int
    categories: List[int]
    interval: int
    bootstrap_mode: str
    dry_run: bool
    once: bool
    state_file: str
    max_state_orders: int
    log_level: str
    config_path: Optional[str]


class WatcherService:
    def __init__(self, settings: RuntimeSettings):
        self.settings = settings
        self.kwork_client = KworkClient()
        self.telegram_client = TelegramClient(settings.token)
        self.state_store = StateStore(settings.state_file, settings.max_state_orders)

    def run(self):
        try:
            self.state_store.load()
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

        self._bootstrap_if_needed()

        while True:
            self.run_cycle()
            if self.settings.once:
                LOGGER.info("Single-run mode enabled, exiting after one cycle.")
                return

            LOGGER.info("Sleeping for %s seconds before the next check.", self.settings.interval)
            time.sleep(self.settings.interval)

    def _bootstrap_if_needed(self):
        if self.state_store.has_orders():
            LOGGER.info(
                "Loaded %s known orders from state file %s.",
                self.state_store.count(),
                self.settings.state_file,
            )
            return

        LOGGER.info(
            "State file is empty. First-run bootstrap mode: %s.",
            self.settings.bootstrap_mode,
        )

        if self.settings.bootstrap_mode == "send":
            return

        bootstrapped = 0
        cycle_started_at = time.time()
        for index, category_id in enumerate(self.settings.categories):
            try:
                orders = self.kwork_client.get_new_orders(category_id)
            except Exception as exc:
                LOGGER.exception("Bootstrap failed for category %s: %s", category_id, exc)
                continue
            LOGGER.info(
                "Bootstrap category %s: fetched %s orders, marking them as known without sending.",
                category_id,
                len(orders),
            )
            for order in orders:
                if not self.settings.dry_run:
                    self.state_store.mark_known(order, "bootstrap", cycle_started_at)
                bootstrapped += 1

            if index < len(self.settings.categories) - 1:
                time.sleep(2.5)

        if self.settings.dry_run:
            LOGGER.info(
                "Dry-run bootstrap completed. %s orders would be written to state, but no changes were saved.",
                bootstrapped,
            )
            return

        self.state_store.save()
        LOGGER.info("Bootstrap completed. Marked %s orders as known.", bootstrapped)

    def run_cycle(self):
        cycle_started_at = time.time()
        fetched_orders: List[KworkOrder] = []

        for index, category_id in enumerate(self.settings.categories):
            try:
                orders = self.kwork_client.get_new_orders(category_id)
            except Exception as exc:
                LOGGER.exception("Failed to fetch category %s: %s", category_id, exc)
                continue
            new_orders = [order for order in orders if not self.state_store.is_known(order.id)]
            fetched_orders.extend(new_orders)
            LOGGER.info(
                "Category %s: fetched %s orders, %s new, %s already known.",
                category_id,
                len(orders),
                len(new_orders),
                len(orders) - len(new_orders),
            )

            if index < len(self.settings.categories) - 1:
                time.sleep(2.5)

        unique_new_orders = self._deduplicate_orders(fetched_orders)
        LOGGER.info("Cycle summary: %s new unique orders queued for processing.", len(unique_new_orders))

        attempted_count = 0
        sent_count = 0
        failed_count = 0
        for index, order in enumerate(unique_new_orders):
            sent = self._process_order(order, cycle_started_at)
            attempted_count += 1
            if sent:
                sent_count += 1
            elif not self.settings.dry_run:
                failed_count += 1

            if index < len(unique_new_orders) - 1:
                time.sleep(1)

        if self.settings.dry_run:
            LOGGER.info(
                "Dry-run cycle completed. %s notifications would be sent, state file was not modified.",
                attempted_count,
            )
            return

        self.state_store.save()
        LOGGER.info(
            "Cycle completed. Attempted %s notifications, sent %s, failed %s, state now contains %s known orders.",
            attempted_count,
            sent_count,
            failed_count,
            self.state_store.count(),
        )

    def _process_order(self, order: KworkOrder, timestamp: float):
        message = self.kwork_client.format_order_message(order)

        if self.settings.dry_run:
            LOGGER.info(
                "DRY RUN: would send order %s | %s | %s | %s",
                order.id,
                order.name,
                order.display_price(),
                order.url,
            )
            return True

        try:
            self.telegram_client.send_message(self.settings.chat_id, message)
            self.state_store.mark_known(order, "sent", timestamp)
            LOGGER.info("Sent notification for order %s.", order.id)
            return True
        except Exception as exc:
            LOGGER.exception("Failed to send order %s to Telegram: %s", order.id, exc)
            return False

    @staticmethod
    def _deduplicate_orders(orders: List[KworkOrder]) -> List[KworkOrder]:
        unique_orders: List[KworkOrder] = []
        seen_ids = set()
        for order in orders:
            if order.id in seen_ids:
                continue
            seen_ids.add(order.id)
            unique_orders.append(order)
        return unique_orders


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Monitor Kwork orders and send Telegram notifications."
    )
    parser.add_argument("--config", dest="config_path", help="Path to a JSON config file.")
    parser.add_argument(
        "--token",
        "--telegram_token",
        dest="token",
        type=str,
        help="Telegram bot token.",
    )
    parser.add_argument(
        "--chat_id",
        "--telegram_chat_id",
        dest="chat_id",
        type=int,
        help="Telegram chat ID.",
    )
    parser.add_argument(
        "--categories",
        "--category_ids",
        dest="categories",
        type=int,
        nargs="+",
        help="List of Kwork category IDs to watch.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        help="Delay between checks in seconds.",
    )
    parser.add_argument(
        "--bootstrap-mode",
        choices=("send", "skip"),
        help="What to do on the first run when the state is empty: send current page orders or mark them as known.",
    )
    parser.add_argument(
        "--state-file",
        help="Path to the JSON file that stores already seen order IDs.",
    )
    parser.add_argument(
        "--max-state-orders",
        type=int,
        help="Maximum number of order records to retain in the state file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be sent without sending messages or updating state.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run only one polling cycle and exit.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        help="Logging verbosity.",
    )
    return parser


def configure_logging(log_level: str):
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def validate_settings(raw_settings: Dict[str, object]) -> RuntimeSettings:
    missing_fields = []
    token = raw_settings.get("token")
    if not token:
        missing_fields.append("token")

    chat_id = raw_settings.get("chat_id")
    if chat_id is None:
        missing_fields.append("chat_id")

    categories = raw_settings.get("categories")
    if not categories:
        missing_fields.append("categories")

    if missing_fields:
        raise SystemExit(
            "Missing required settings: " + ", ".join(missing_fields)
        )

    interval = int(raw_settings.get("interval", 300))
    if interval <= 0:
        raise SystemExit("Interval must be a positive integer.")

    bootstrap_mode = str(raw_settings.get("bootstrap_mode", "send"))
    if bootstrap_mode not in {"send", "skip"}:
        raise SystemExit("Bootstrap mode must be either 'send' or 'skip'.")

    max_state_orders = int(raw_settings.get("max_state_orders", 5000))
    if max_state_orders <= 0:
        raise SystemExit("max_state_orders must be a positive integer.")

    log_level = str(raw_settings.get("log_level", "INFO")).upper()
    if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR"}:
        raise SystemExit("log_level must be one of: DEBUG, INFO, WARNING, ERROR.")

    return RuntimeSettings(
        token=str(token),
        chat_id=int(chat_id),
        categories=[int(item) for item in categories],
        interval=interval,
        bootstrap_mode=bootstrap_mode,
        dry_run=bool(raw_settings.get("dry_run", False)),
        once=bool(raw_settings.get("once", False)),
        state_file=str(raw_settings.get("state_file", "sent_orders.json")),
        max_state_orders=max_state_orders,
        log_level=log_level,
        config_path=raw_settings.get("config_path"),
    )


def main():
    parser = build_parser()
    args = parser.parse_args()
    raw_settings = load_runtime_config(args)
    settings = validate_settings(raw_settings)
    configure_logging(settings.log_level)

    LOGGER.info("Starting Kwork watcher.")
    LOGGER.info(
        "Settings: categories=%s, interval=%ss, bootstrap=%s, dry_run=%s, once=%s, state=%s, config=%s",
        settings.categories,
        settings.interval,
        settings.bootstrap_mode,
        settings.dry_run,
        settings.once,
        settings.state_file,
        settings.config_path or "none",
    )

    watcher = WatcherService(settings)
    watcher.run()


if __name__ == "__main__":
    main()
