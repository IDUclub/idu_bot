import json
import ssl
from datetime import datetime
from json import JSONDecodeError

import requests
from loguru import logger
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.states import StatesGroup, State
from telebot.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand

from src.dependencies import elastic_client, llm_service, model


bot = AsyncTeleBot(elastic_client.config.get("TG_TOKEN"), parse_mode=None)
cnt = 0


users_settings = {}


freq_limit_amount_per_second = 4


commands = [
    BotCommand('start', 'Запустить бота'),
    BotCommand('menu', 'Открыть главное меню'),
]

async def show_categories(message):

    markup = InlineKeyboardMarkup(row_width=1)

    for index in list(elastic_client.index_mapper.values()):
        en_index = elastic_client.reverse_index_mapper.get(index)
        result = elastic_client.client.search(index=en_index, body={"query": {"match_all": {}}})
        if result.body["hits"]["total"]["value"] == 0:
            index_title = index + "\u274c"
        else:
            index_title = index + "\u2705"
        markup.add(
        InlineKeyboardButton(
            index_title,
            callback_data=index,
        )
    )
    markup.add(InlineKeyboardButton("← Назад", callback_data="back_main"))
    await bot.edit_message_text(
        "Выберите стадию:",
        chat_id=message.chat.id,
        message_id=message.message_id,
        reply_markup=markup
    )

async def choose_index(chat_id, index_name: str):

    if (elastic_index:=elastic_client.reverse_index_mapper.get(index_name)) is None:
        await bot.send_message(chat_id, "Такой стадии не существует")
    elastic_res = elastic_client.client.search(index=elastic_index)
    if elastic_res.body["hits"]["total"]["value"] == 0:
        await bot.send_message(chat_id, f"Стадия {index_name} не содержит документов и не доступна в этот момент")
        return
    users_settings[chat_id] = elastic_index
    await bot.send_message(chat_id, f'В качестве стадии выбрана "{elastic_client.index_mapper.get(elastic_index)}"')


@bot.message_handler(commands=['menu'])
async def show_menu(message):
    # Создаем клавиатуру меню
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton("Стадии", callback_data="phase"),
    )

    # Отправляем сообщение с меню
    await bot.send_message(
        message.chat.id,
        "📱 *Главное меню*",
        parse_mode="Markdown",
        reply_markup=markup
    )


@bot.message_handler(commands=["start"])
async def send_welcome(message):
    await bot.set_my_commands(commands)
    await bot.reply_to(
        message,
        """Привет! Я ассистент ИДУ ИТМО! Вы можете задать мне любой вопрос по документам.""",
    )

    markup = InlineKeyboardMarkup(row_width=2)

    index_button = InlineKeyboardButton("Выбрать стадию", callback_data="phase")
    markup.add(index_button)
    await bot.send_message(
        message.chat.id,
        "Выберите действие:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: True)
async def callback_query(call):
    if call.data == "phase":
        await show_categories(call.message)
    elif call.data == "main":
        await show_menu(call.message)
    elif call.data in list(elastic_client.index_mapper.values()):
        await choose_index(call.message.chat.id, call.data)
    elif call.data == "back_main":
        await send_welcome(call.message)


@bot.message_handler(func=lambda m: True)
async def echo(message: Message):
    global cnt
    cnt += 1
    print(
        f"{datetime.now().strftime('%d.%m %H:%M')} from {message.from_user.username} accepted: {message.text}"
    )
    if (index_name:=users_settings.get(message.chat.id)) is None:
        await bot.reply_to(message, "Вы не выбрали стадию, сначала выберите стадию")
        return
    try:
        embedding = model.embed(message.text)
    except Exception as e:
        await bot.reply_to(message, "cant connect to backend server")
        return
    print(message.text, embedding)
    try:
        elastic_response = await elastic_client.search(embedding, index_name)
    except ConnectionError as e:
        cnt -= 1
        print(e.__str__())
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
        logger.info(text)
        if error_msg != "":
            text += f"\n\nОшибки во время ответа: \n{error_msg}"
        await bot.send_message(
            chat_id=elastic_client.config.get("CHAT_LOG_ID"),
            text=text,
            disable_notification=True,
        )
    cnt -= 1
