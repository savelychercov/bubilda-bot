
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
DISCORD_TOKEN=<your_value>   # Required!
DEBUG_DISCORD_TOKEN=<your_value>
OPENAI_TOKEN=<your_value>
PEXELS_TOKEN=<your_value>
TENOR_TOKEN=<your_value>
TELEGRAM_TOKEN=<your_value>
```
