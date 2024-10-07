
# Bubilda

My personal bot on discord


## Deployment

To deploy this project run

```bash
  git clone https://github.com/savelychercov/bubilda-bot
  cd bubilda-bot

  python -m venv venv

  On Windows:
    venv\Scripts\activate

  On macOS and Linux:
    source venv/bin/activate

  pip install -r requirements.txt
```

Add and open the .env file and add the following keys, replacing <your_value> with your actual tokens:
```text
DISCORD_TOKEN=<your_value>   # Main discord api token. Required!
DEBUG_DISCORD_TOKEN=<your_value>  # Token for debug bot for test server
OPENAI_TOKEN=<your_value>  # Token for GPTCog, get from openai
PEXELS_TOKEN=<your_value>  # Token for search images, get from pexels
TENOR_TOKEN=<your_value>  # Token for search gifs, get from tenor
TELEGRAM_TOKEN=<your_value>  # Token for send logs to Telegram
TELEGRAM_USER_ID=<your_telegram_id>  # Your user id in Telegram
```
