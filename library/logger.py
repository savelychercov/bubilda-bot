import requests
import traceback
import config


TG_KEY = config.telegram_apikey
if TG_KEY is None:
    print("Telegram API key is not set in the .env file, logs will not be sent to Telegram.")
ID_LOGS = config.telegram_user_id
name = "Testing Bubilda" if config.testing else "Bubilda"


def escape_markdown(text):
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


def log(text, markdown: bool = True):
    url = f"https://api.telegram.org/bot{TG_KEY}/sendMessage"
    text = f"From {name}:\n\n"+str(text)
    text = escape_markdown(text)
    if ID_LOGS is None:
        print("\n\nThis message was not sent to Telegram because the ID_LOGS is not set in the .env file")
        return
    params = {
        "chat_id": ID_LOGS,
        "text": text,
    }
    if markdown: params["parse_mode"] = "MarkdownV2"
    print(text)
    resp = requests.post(url, params=params)
    if resp.status_code != 200:
        print(resp.text)
        log(f"Traceback:\n{text}", markdown=False)


def err(error: Exception, additional_text: str = ""):
    traceback_str = ''.join(
        traceback.format_exception(type(error), error, error.__traceback__))
    text = f"""{additional_text}\n```python
{traceback_str}
```"""
    log(text)
    config.last_traceback = traceback_str
