import requests
import traceback
import config


TG_KEY = config.telegram_apikey
ID_LOGS = "1424216183"
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
    params = {
        "chat_id": ID_LOGS,
        "text": text,
    }
    if markdown: params["parse_mode"] = "MarkdownV2"
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
    print(text)
    log(text)
    config.last_traceback = traceback_str
