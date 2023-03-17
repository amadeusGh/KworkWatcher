# KworkWatcher
Kwork Exchange Watcher is a Python script that allows you to receive notifications in your Telegram messenger about new orders on the Kwork exchange.

### Algorithm of Work

1. Get the list of orders from the Kwork exchange website for the specified categories.
2. Filter out the orders that have already been sent in previous notifications.
3. Send new order notifications to your Telegram chat using your Telegram bot.
4. Save the IDs of the sent orders to avoid sending duplicate notifications.
5. Sleep for the specified interval before repeating the process.

### How to Launch

To launch the script, you need to run the following command in the terminal:

`python3 watcher.py --telegram_token <TELEGRAM_BOT_TOKEN> --telegram_chat_id <TELEGRAM_CHAT_ID> --category_ids <CATEGORY_ID_1> <CATEGORY_ID_2> ... --interval <SECONDS_BETWEEN_CHECKS>`

where TELEGRAM_BOT_TOKEN is the token of your Telegram bot, TELEGRAM_CHAT_ID is the chat ID of the user or group where you want to receive notifications, <CATEGORY_ID_1> <CATEGORY_ID_2> ... are the IDs of the categories you want to track, and <SECONDS_BETWEEN_CHECKS> is the interval between checks for new orders. The interval argument is optional and defaults to 300 seconds.

Use the help command to see how to use the script. Just run the script with the --help argument to print out the description of the application and all the available arguments.

You can get your Telegram chat ID by adding your bot to a group or sending a message to your bot and then going to the following URL in your browser, replacing BOT_TOKEN with your bot's token: https://api.telegram.org/botBOT_TOKEN/getUpdates. Look for the chat object in the response, which will contain the id of the chat.

To get the category id, follow these steps:
1. Go to https://kwork.ru/projects.
2. Choose the desired category in the left sidebar.
3. The category id can be found in the URL as the value of the GET-parameter "fc"
   (for example, https://kwork.ru/projects?fc=171).

***

PS: In the future, this script can be improved by adding additional functionality, such as the ability to filter orders by budget or keywords, to make it even more customizable for the user.
