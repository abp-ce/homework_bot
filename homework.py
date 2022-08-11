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


VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


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
    logger.debug('Запрос к эндпоинту.')
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.ConnectionError as error:
        raise exceptions.EndPointException('Сбой в работе программы: ' + error)
    if response.status_code != HTTPStatus.OK:
        raise exceptions.EndPointException(
            'Эндпоинт'
            '  https://practicum.yandex.ru/api/user_api/homework_statuses/'
            f' недоступен. Параметры запроса: {params}. Код ответа API:'
            f' {response.status_code}. Текст ответа: {response.text}'
        )
    return response.json()


def check_response(response: requests.Response) -> list:
    """Проверяет ответ на типы и наличие ключей."""
    logger.debug('Проверка ответа на запрос к эндпоинту.')
    if not isinstance(response, dict):
        raise TypeError('Ответ не является словарём')
    if 'current_date' not in response or 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "current_date" или "homeworks"')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Ключ "homeworks" не список')
    return response['homeworks']


def parse_status(homework: dict) -> str:
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    В качестве параметра функция получает только один элемент из списка
    домашних работ. В случае успеха, функция возвращает подготовленную для
    отправки в Telegram строку, содержащую один из вердиктов словаря
    VERDICTS.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not homework_name:
        raise KeyError(
            'Значение homework_name пустое или отсутствует.'
        )
    if homework_status not in VERDICTS:
        raise KeyError(
            'Недопустимый статус: {homework_status}'
        )

    verdict = VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """
    Проверяет доступность переменных окружения, которые необходимы программе.
    Если отсутствует хотя бы одна переменная окружения —
    функция должна вернуть False, иначе — True.
    """
    response = True
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        response = False
    return response


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        error = (
            'Отсутствует одна или более из обязательных переменных окружения:'
            ' PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID.'
            ' Программа принудительно остановлена.'
        )
        logger.critical(error)
        sys.exit(error)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
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
    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(funcName)s %(lineno)d %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    main()
