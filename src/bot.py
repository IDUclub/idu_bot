import json
import ssl
from datetime import datetime
from json import JSONDecodeError

import requests
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.types import Message

from src.dependencies import elastic_client, llm_service, model

bot = AsyncTeleBot(elastic_client.config.get("TG_TOKEN"), parse_mode=None)
cnt = 0

freq_limit_amount_per_second = 4


@bot.message_handler(commands=["start"])
async def send_welcome(message):
    await bot.reply_to(
        message,
        """Привет! Я ассистент ИДУ ИТМО! Вы можете задать мне любой вопрос по документам.""",
    )


@bot.message_handler(func=lambda m: True)
async def echo(message: Message):
    global cnt
    cnt += 1
    print(
        f"{datetime.now().strftime('%d.%m %H:%M')} from {message.from_user.username} accepted: {message.text}"
    )

    try:
        embedding = model.embed(message.text)
    except Exception as e:
        await bot.reply_to(message, "cant connect to backend server")
        return
    print(message.text, embedding)
    try:
        elastic_response = await elastic_client.search(embedding)
    except ConnectionError as e:
        cnt -= 1
        await bot.reply_to(message, "cant connect to document store")
        return
    context = ";".join(
        [resp["_source"]["body"].rstrip() for resp in elastic_response["hits"]["hits"]]
    )
    headers, data = await llm_service.generate_request_data(message.text, context)
    response_message: Message | None = None
    next_message = ""
    last_response_timestamp = datetime.now().timestamp() * 1000

    errors = {}

    client_cert = elastic_client.config.get("CLIENT_CERT")
    ca_cert = "onti-ca.crt"
    client_key = "DECFILE"

    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain(certfile=client_cert, keyfile=client_key)
    ssl_context.load_verify_locations(cafile=ca_cert)
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    url = f"{llm_service.url}/api/generate"

    try:
        with requests.post(
            url,
            headers=headers,
            data=json.dumps(data),
            cert=(client_cert, client_key),
            verify=ca_cert,
            stream=True,
        ) as response:
            if response.status_code == 200:

                for chunk in response.iter_content(chunk_size=512 * 1024):
                    chunk = json.loads(chunk)
                    if not chunk["done"]:
                        generated_chunk_message = chunk["response"]
                        if not response_message:
                            response_message = await bot.reply_to(
                                message, generated_chunk_message
                            )
                            next_message += response_message.text
                        elif response_message and (
                            len(generated_chunk_message) < 1
                            or generated_chunk_message in [" ", "\n"]
                        ):
                            next_message += generated_chunk_message
                        elif response_message:
                            next_message += generated_chunk_message
                            cur_response_timestamp = datetime.now().timestamp() * 1000
                            cur_response_freq = (
                                1000 / freq_limit_amount_per_second * max(1, cnt)
                            )
                            if (
                                cur_response_timestamp - last_response_timestamp
                                > cur_response_freq
                            ):
                                print(f"{cur_response_freq}ms")
                                try:
                                    response_message = await bot.edit_message_text(
                                        next_message,
                                        chat_id=response_message.chat.id,
                                        message_id=response_message.message_id,
                                    )
                                except ApiTelegramException as e:
                                    if e.error_code not in errors:
                                        errors[e.error_code] = {
                                            "cnt": 0,
                                            "descriptions": set(),
                                        }
                                    errors[e.error_code]["cnt"] += 1
                                    errors[e.error_code]["descriptions"].add(
                                        e.description
                                    )
                                    continue
                                last_response_timestamp = cur_response_timestamp
                try:
                    await bot.edit_message_text(
                        next_message,
                        chat_id=response_message.chat.id,
                        message_id=response_message.message_id,
                    )
                except ApiTelegramException as e:
                    if e.error_code not in errors:
                        errors[e.error_code] = {"cnt": 0, "descriptions": set()}
                    errors[e.error_code]["cnt"] += 1
                    errors[e.error_code]["descriptions"].add(e.description)
            else:
                print("Ошибка запроса:", response.status_code, response.text)
    except JSONDecodeError as e:
        print(chunk)
        print(e)
    except Exception as e:
        print(type(e), e)
        await bot.reply_to(message, "cant connect to llm")
        cnt -= 1
        return
    if next_message != "":
        error_msg = ""
        for k, v in errors.items():
            error_msg += (
                f" - {k}: количество {v['cnt']}, описания: {list(v['descriptions'])}\n"
            )
        text = f"Сообщение от {message.chat.username}: {message.text}\n\nОтвет: {next_message}"
        if error_msg != "":
            text += f"\n\nОшибки во время ответа: \n{error_msg}"
        await bot.send_message(
            chat_id=elastic_client.config.get("CHAT_LOG_ID"),
            text=text,
            disable_notification=True,
        )
    cnt -= 1
