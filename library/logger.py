import httpx
import requests
import traceback
import config
import types
import re


TG_KEY = config.telegram_apikey
if TG_KEY is None:
    print("Telegram API key is not set in the .env file, logs will not be sent to Telegram.")
ID_LOGS = config.telegram_user_id
name = "Testing Bubilda" if config.testing else "Bubilda"


class LogAllErrors:
    def __init__(self, additional_text: str = "", except_errors: types.UnionType | Exception = None):
        self.additional_text = additional_text
        self.except_errors: types.UnionType | Exception = except_errors

    def __enter__(self):
        return self

    def __exit__(self, exc_type: type, exc_value: Exception, tb: traceback):
        if exc_type is not None:
            if self.except_errors is not None:
                if isinstance(self.except_errors, types.UnionType):
                    if exc_type in self.except_errors.__args__:
                        return True
                elif issubclass(self.except_errors, Exception):
                    if exc_type is self.except_errors:
                        return True
            err(exc_value, self.additional_text)
            return True
        else:
            return True


def escape_markdown(text):
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


def slice_text(text: str, length: int = 1990) -> list[str]:
    if not text:
        return [""]

    if len(text) <= length:
        return [text]

    # Разбиваем текст на блоки Markdown и на обычный текст
    blocks = re.split(r'(```.*?```)', text, flags=re.DOTALL)

    result = []
    for block in blocks:
        if block.startswith("```") and block.endswith("```"):  # Это Markdown блок
            content = block[3:-3]  # Убираем ```

            # Разбиваем содержимое Markdown блока на части
            slices = [f"```{content[i:i + length]}```" for i in range(0, len(content), length)]
            result.extend(slices)
        else:
            # Разбиваем обычный текст на части
            result.extend([block[i:i + length] for i in range(0, len(block), length)])

    return result


def log(text, markdown: bool = True) -> None:
    url = f"https://api.telegram.org/bot{TG_KEY}/sendMessage"
    text = f"From {name}:\n\n"+str(text)
    text = escape_markdown(text)
    if ID_LOGS is None:
        print("\n\nThis message was not sent to Telegram because the ID_LOGS is not set in the .env file")
        return

    for text_part in slice_text(text):
        params = {
            "chat_id": ID_LOGS,
            "text": text_part,
        }
        if markdown: params["parse_mode"] = "MarkdownV2"
        print(text_part)
        resp = requests.post(url, params=params)

        if resp.status_code != 200:
            with open("log.txt", "a") as f:
                f.write(f"{resp.status_code}: {resp.text}\n\n{text_part}\n\n")
            # raise Exception(f"Error sending message to Telegram:\n{resp.status_code} {resp.text}")


def err(error: Exception, additional_text: str = ""):
    traceback_str = ''.join(
        traceback.format_exception(type(error), error, error.__traceback__))
    text = f"""{additional_text}\n```python{traceback_str}```"""
    log(text)
    config.last_traceback = traceback_str
