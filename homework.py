# import datetime
import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot: telegram.Bot, message: str) -> None:
    """Посылает сообщение в telegram, в случае ошибки и успеха логирует."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except telegram.error.TelegramError:
        logger.error(f'Бот не смог отправить сообщение "{message}"')
    else:
        logger.info(f'Бот отправил сообщение "{message}"')


def get_api_answer(current_timestamp: int) -> dict:
    """Запрашивает endpoint, в случае ошибки бросает EndPointException."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code == HTTPStatus.NOT_FOUND:
        raise exceptions.EndPointException(
            'Сбой в работе программы: Эндпоинт'
            '  https://practicum.yandex.ru/api/user_api/homework_statuses/'
            f' недоступен. Код ответа API: {response.status_code}'
        )
    if response.status_code != HTTPStatus.OK:
        raise exceptions.EndPointException(
            'Сбой в работе программы:'
            f' Что-то пошло не так. Код ответа API: {response.status_code}'
        )
    return response.json()


def check_response(response: requests.Response) -> list:
    """Проверяет ответ на типы и наличие ключей."""
    if not isinstance(response, dict):
        raise TypeError('Ответ не является словарём')
    if 'current_date' not in response:
        raise KeyError('Отсутствует ключ "current_date"')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks"')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Ключ "homeworks" не список')
    return response['homeworks']


def parse_status(homework: dict) -> str:
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает подготовленную для
    отправки в Telegram строку, содержащую один из вердиктов словаря
    HOMEWORK_STATUSES.
    """
    homework_name = homework['homework_name'] or None
    homework_status = homework['status'] or None
    if homework_status not in HOMEWORK_STATUSES:
        raise KeyError(
            'Недопустимый статус: {homework_status}'
        )

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """
    Проверяет доступность переменных окружения, которые необходимы программе.
    Если отсутствует хотя бы одна переменная окружения —
    функция должна вернуть False, иначе — True.
    """
    response = True
    if PRACTICUM_TOKEN is None:
        logger.critical(
            'Отсутствует обязательная переменная окружения:'
            'PRACTICUM_TOKEN. Программа принудительно остановлена.'
        )
        response = False
    if TELEGRAM_TOKEN is None:
        logger.critical(
            'Отсутствует обязательная переменная окружения:'
            'TELEGRAM_TOKEN. Программа принудительно остановлена.'
        )
        response = False
    if TELEGRAM_CHAT_ID is None:
        logger.critical(
            'Отсутствует обязательная переменная окружения:'
            'TELEGRAM_CHAT_ID. Программа принудительно остановлена.'
        )
        response = False
    return response


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        return

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    # shift = datetime.timedelta(days=30)
    # date_time = datetime.datetime.now() - shift
    # current_timestamp = int(date_time.strftime("%s"))
    message, last_message = '', ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response['current_date']
            homework = check_response(response)
            if len(homework) < 1:
                logger.debug('Статус не обновился.')
            else:
                message = parse_status(homework[0])
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)
        finally:
            if message != last_message:
                send_message(bot, message)
            last_message = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
