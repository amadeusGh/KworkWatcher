# Kwork Watcher

Kwork Watcher is a lightweight Python polling service that monitors the Kwork projects feed and delivers notifications about newly discovered orders to a Telegram chat.

It is designed for a single-user or small-team workflow where reliability, predictable first-run behavior, and low operational overhead matter more than complex infrastructure.

## Features

- Polls the first page of Kwork project listings for one or more categories
- Sends formatted Telegram notifications for unseen orders
- Prevents duplicate notifications with a persistent local state file
- Supports safe first-run bootstrapping
- Supports one-off execution for testing and cron-style usage
- Supports dry-run mode for validation without sending messages
- Loads `config.json` automatically from the project root
- Migrates legacy `sent_orders.txt` state automatically

## How It Works

On every cycle the watcher:

1. Requests the first page of Kwork orders for each configured category
2. Extracts order IDs and normalizes the payload
3. Compares fetched IDs with the local state file
4. Sends Telegram notifications only for unseen orders
5. Stores successfully processed orders in `sent_orders.json`
6. Sleeps for the configured interval and repeats

This service does not subscribe to real-time events. It uses periodic polling.

## Project Structure

```text
.
├── api/
│   ├── kwork.py
│   └── telegram.py
├── config.json
├── config.py
├── state_store.py
└── watcher.py
```

- `watcher.py` orchestrates configuration loading, polling, bootstrap logic, logging, and notification delivery
- `api/kwork.py` fetches and formats Kwork orders
- `api/telegram.py` sends messages through the Telegram Bot API
- `config.py` loads configuration and applies CLI overrides
- `state_store.py` manages persisted order state and legacy migration

## Requirements

- Python 3.9+
- `requests`

Install dependencies:

```bash
pip install requests
```

## Configuration

The watcher loads `config.json` from the project root automatically. You can also pass a custom file with `--config`.

Example:

```json
{
  "token": "123456:example",
  "chat_id": 123456789,
  "categories": [171],
  "interval": 60,
  "bootstrap_mode": "skip",
  "state_file": "sent_orders.json",
  "max_state_orders": 5000,
  "log_level": "INFO",
  "dry_run": false,
  "once": false
}
```

### Configuration Reference

- `token`
  Telegram bot token.
- `chat_id`
  Destination Telegram chat ID.
- `categories`
  List of Kwork category IDs to monitor.
- `interval`
  Delay between polling cycles in seconds.
- `bootstrap_mode`
  First-run behavior when the state file is empty.
  Allowed values:
  - `send`: notify about the current first-page results immediately
  - `skip`: mark current first-page results as known and wait for future orders
- `state_file`
  Path to the JSON state file.
- `max_state_orders`
  Maximum number of stored order records.
- `log_level`
  One of `DEBUG`, `INFO`, `WARNING`, `ERROR`.
- `dry_run`
  If `true`, no Telegram messages are sent and state is not updated.
- `once`
  If `true`, execute a single cycle and exit.

## Usage

Run with the default `config.json`:

```bash
python3 watcher.py
```

Run a single cycle:

```bash
python3 watcher.py --once
```

Preview new orders without sending messages:

```bash
python3 watcher.py --dry-run --once
```

Use an explicit configuration file:

```bash
python3 watcher.py --config /path/to/config.json
```

Override individual settings from the command line:

```bash
python3 watcher.py --interval 30 --bootstrap-mode send --once
```

Legacy CLI aliases are still supported:

- `--telegram_token` for `--token`
- `--telegram_chat_id` for `--chat_id`
- `--category_ids` for `--categories`

## First-Run Behavior

If `sent_orders.json` does not exist or is empty, the watcher uses `bootstrap_mode`:

- `send`
  The current first-page results are treated as new and are eligible for immediate delivery.
- `skip`
  The current first-page results are written to state without delivery, so only future orders trigger notifications.

For a production first start, `skip` is usually the safer option because it avoids flooding the chat with old listings.

## State Management

By default the service stores processed orders in `sent_orders.json`.

Each stored record contains:

- order ID
- title
- category
- price
- URL
- status
- tracking timestamp

State writes are atomic to reduce the risk of corruption during unexpected interruptions.

If a legacy `sent_orders.txt` file is present and the JSON state file is missing, the watcher migrates the old IDs automatically.

## Telegram Message Format

Notifications are sent in Russian and include:

- order title
- budget
- category
- shortened description
- direct Kwork link

The message body is HTML-escaped before delivery.

## Operational Notes

- The watcher only polls the first Kwork results page for each category
- Network errors are logged and do not terminate the process automatically
- Failed Telegram deliveries are not marked as sent, so the same order can be retried on the next cycle
- Invalid or corrupted configuration and state files fail fast with explicit error messages

## Finding Required IDs

### Telegram chat ID

1. Send a message to your bot or add it to a group
2. Open:

```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```

3. Find the `chat.id` field in the response

### Kwork category ID

1. Open `https://kwork.ru/projects`
2. Select a category in the sidebar
3. Read the `fc` query parameter from the URL

Example:

```text
https://kwork.ru/projects?fc=171
```

## Limitations

- This project relies on the structure of Kwork web responses rather than a public official API contract
- Only the first page of category results is monitored
- Long outages may cause some orders to scroll out of the first page before they are seen

## Troubleshooting

If no messages are sent:

- verify that the bot token is valid
- verify that `chat_id` is correct
- confirm that the bot has permission to write to the target chat
- check whether `bootstrap_mode` is set to `skip`
- run `python3 watcher.py --dry-run --once` and inspect the logs

If the watcher exits immediately:

- validate `config.json`
- verify that required fields are present: `token`, `chat_id`, `categories`
- check file permissions for the state file path

## License

No license file is included in this repository. Add one if you plan to distribute or reuse the project publicly.
