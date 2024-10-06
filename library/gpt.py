import openai
import discord
import re
import transliterate
from config import openai_apikey
from discord import Attachment
from discord.ext import commands
from library.graphics import SearchContent
from library import logger

client = openai.OpenAI(api_key=openai_apikey)
regex_for_names = '^[a-zA-Z0-9_-]{1,64}$'
regex_for_urls = r"(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|www\.[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,}|www\.[a-zA-Z0-9]+\.[^\s]{2,})"
model = "gpt-4o-mini"
temperature = 0.4
image_remember_limit = 5

functions = [
    {
        "name": "send_gif",
        "description": "Sends a GIF for the given search query.",
        "parameters": {
            "type": "object",
            "properties": {
                "search_text": {
                    "type": "string",
                    "description": "Text to search for GIFs."
                }
            },
            "required": ["search_text"]
        }
    },
    {
        "name": "send_embed",
        "description": "Sends a Discord embed",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title of the embed."
                },
                "desc": {
                    "type": "string",
                    "description": "The description of the embed."
                },
                "color_hex": {
                    "type": "string",
                    "description": "Hex color (default is \"#ffffff\")",
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "send_table",
        "description": "Sends a table",
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table"
                },
                "titles": {
                    "type": "array",
                    "description": "List of table titles",
                    "items": {
                        "type": "string",
                        "description": "Заголовок столбца."
                    }
                },
                "rows": {
                    "type": "array",
                    "description": "List of table rows, where each row is a list of cells",
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "description": "Cell text"
                        }
                    }
                }
            },
            "required": ["table_name", "titles", "rows"]
        }
    }
]


def send_table(table_name: str, titles: list[str], rows: list[list[str]]):
    text = f"## {table_name}\n\n"
    for row in rows:
        for title, cell in zip(titles, row):
            text += f"**{title}**: {cell}\n"
        text += "\n"
    return text


def gen_answer_from_messages(author_name: str, message: str, history: list[dict] = None, tune_strings: str | list = ""):
    if not isinstance(tune_strings, str):
        tune_strings = ". ".join(tune_strings)
    if not history: history = []
    completion = client.chat.completions.create(
        model=model,  # "gpt-3.5-turbo",
        temperature=temperature,
        messages=[{"role": "system", "content": tune_strings}] + history + [
            {"role": "user", "name": author_name, "content": message}]
    )
    return completion.choices[0].message.content


def gen_answer_from_image(author_name: str, prompt: str, image_urls: list[str]):
    message = {
        "role": "user",
        "name": author_name,
        "content": [
            {"type": "text", "text": prompt},
        ]
    }
    for url in image_urls:
        message["content"].append(
            {"type": "image_url", "image_url": {"url": url, "detail": "low"}}
        )
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[message],
        max_tokens=2000,
    )
    return response.choices[0].message.content


def gen_answer_universal(full_context: list[dict]):
    completion = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=full_context,
        functions=functions
    )
    text = completion.choices[0].message.content
    gif_url = None
    embed = None
    try:
        if f := get_function_call(completion):
            args = get_args_from_response(completion)
            if f == "send_gif":
                gif_url = send_gif(**args)
            elif f == "send_embed":
                embed = send_embed(**args)
            elif f == "send_table":
                text = send_table(**args)
            '''elif f == "send_message_to_savely":
                send_message_to_savely(**args)
                text = "Сообщение отправлено savelychercov"'''
    except Exception as e:
        logger.err(e, "Eval function error in GPT")
        text = "EvalError"
    return text, gif_url, embed


def get_urls_from_attachments(attachments: list[Attachment]) -> list[str]:
    image_urls = [
        attachment.url for attachment in attachments if
        attachment.content_type.startswith('image/')
    ]
    if len(image_urls) > 2:
        image_urls = image_urls[:2]
    return image_urls


def get_full_context_window(tune_strings: list, messages: list[dict], request_message: discord.Message) -> list[dict]:
    tune_string = ". ".join(tune_strings)
    messages = [{"role": "system", "content": tune_string}] + messages + [pack_message(
        refine_name(request_message.author.name),
        request_message.content,
        get_urls_from_attachments(request_message.attachments))]
    return messages


def pack_message(author_name: str, text: str, image_urls: list[str], role: str = "user") -> dict:
    """
    message = {
        "role": role,
        "name": name,
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": url, "detail": "low"}}
        ]
    }
    """
    message = {
        "role": role,
        "name": author_name,
        "content": []
    }
    if text:
        message["content"].append(
            {"type": "text", "text": text}
        )
    if image_urls:
        for url in image_urls:
            message["content"].append(
                {"type": "image_url", "image_url": {"url": url, "detail": "low"}}
            )
    return message


def refine_name(name: str) -> str:
    if not re.match(regex_for_names, name):
        transliterated_name = transliterate.translit(name, "ru", reversed=True)
        name = re.sub(r'[^a-zA-Z0-9_\-]', "", transliterated_name)
    if name == "":
        name = "NoName"
    if len(name) > 60:
        name = name[:60]
    return name


def refine_embed(embed: discord.Embed) -> str:
    strs = []
    if embed.title: strs.append(f"title=\"{embed.title}\"")
    if embed.description: strs.append(f"description=\"{embed.description}\"")
    for i, field in enumerate(embed.fields):
        strs.append(f"\n{field.name}\n{field.value}")
    c: discord.Color = embed.colour
    if c: strs.append(f"color=discord.Color(int(\"{c.value:06X}\", 16))")
    if not strs: return "discord.Embed()"
    return "discord.Embed("+",".join(strs)+")"


def send_gif(search_text: str):
    return SearchContent.get_gif(search_text)


def send_embed(title: str, desc: str = None, color_hex: str = "#ffffff"):
    try:
        emb = discord.Embed(
            title=title,
            description=desc,
            color=discord.Color.from_str(color_hex)
        )
        return emb
    except ValueError:
        return None
    except Exception as e:
        logger.err(e, "Ошибка создания эмбеда с GPT")
        return None


def send_message_to_savely(text: str):
    try:
        print(text)
        logger.log(f"Message from BubildaGPT:\n{text}", markdown=False)
    except Exception as e:
        logger.err(e, "Ошибка отправки сообщения savelychercov")
    """
        {
            "name": "send_message_to_savely",
            "description": "Sends a message to Savely",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text of the message"
                    }
                },
                "required": ["message"]
            }
        }
    """


async def get_last_messages(
        bot: commands.Bot,
        channel: discord.TextChannel,
        request_message: discord.Message,
        count: int) -> list[dict]:
    messages = []
    messages_count = 0
    async for msg in channel.history(limit=count):
        messages_count += 1
        urls = None
        if (msg == request_message
                or msg.content.strip() == ""
                or re.match(regex_for_urls, msg.content)):  # no content in message text
            if msg.embeds and msg.author.bot:  # if has embeds
                content = ", ".join([refine_embed(emb) for emb in msg.embeds])
            elif [attachment.url for attachment in msg.attachments if attachment.content_type.startswith('image/')] \
                    and messages_count < image_remember_limit:  # if message has attachments and remember limit
                content = ""
                pass
            else:
                continue  # skip message
        else:
            content = msg.content
        if msg.author.id == bot.user.id:
            name = "assistant"
        else:
            name = refine_name(msg.author.name)
        if messages_count < image_remember_limit:
            urls = get_urls_from_attachments(msg.attachments)

        messages.insert(0, pack_message(name, content, urls, role="user"))
    return messages


def get_args_from_response(resp: openai.ChatCompletion) -> dict:
    if resp.choices[0].message.function_call.arguments:
        return eval(resp.choices[0].message.function_call.arguments)
    else:
        return None


def get_function_call(resp: openai.ChatCompletion) -> str:
    if resp.choices[0].message.function_call:
        return resp.choices[0].message.function_call.name
    else:
        return None


if __name__ == "__main__":
    emb = discord.Embed(
        title="Test title",
        description="Test desc",
        color=discord.Color.orange()
    )
    print(refine_embed(emb))
    print(eval(refine_embed(emb)))
