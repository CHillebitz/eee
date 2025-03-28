Automatically stalks ETH platforms so you don’t have to.

This Python script logs into various ETH Zürich platforms, checks for new exercises or assignments, and sends you a Telegram message if something fresh pops up. Perfect for when you’re procrastinating but still want to look productive.

Features

Analysis I: Crawls Metaphor for the latest exercise sheet.

Code Expert: Logs in via edu-ID and extracts new tasks using Selenium magic.

Moodle Timeline: Peeks into your timeline and snitches on new deadlines.

PP Moodle Course: Checks the Parallel Programming course for hidden assignments.


Requirements

Python 3.8+

Chromium + Chromedriver (installed via apt)

A Telegram bot and chat ID

A working .env file (see below)
.env Example

Create a .env file in the same directory as the script with:

TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

MOODLE_USERNAME=your_ethz_username
MOODLE_PASSWORD=your_ethz_password

CODE_EXPERT_USERNAME=your_switch_edu_id
CODE_EXPERT_PASSWORD=your_password

> Yes, your passwords are in plain text. No, I don’t judge.



Running It

Just run it manually:

python3 main_combined.py

Or add it to your crontab.
