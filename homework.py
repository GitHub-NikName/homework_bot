import os
import sys
import time
import logging
import requests
import telegram

from dotenv import load_dotenv
from telegram.error import TelegramError

from exeptions import EndpointNotAvailable, HomeworkNotFound, NoHomeworkName,\
    UnknownHomeworkStatus


load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка обязательных переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN))


def send_message(bot, message):
    """Отправляет сообщение в телеграм."""
    logger.debug('Отправка сообщения')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение "{message}"')
    except TelegramError as e:
        logger.error(e)


def get_api_answer(timestamp):
    """Возвращает json, если доступен."""
    logger.debug('Получение ответа с сервера')
    try:
        params = {'from_date': timestamp}
        res = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if res.status_code != 200:
            raise EndpointNotAvailable(ENDPOINT, res)
        return res.json()
    except requests.RequestException:
        logger.error('No response')


def check_response(response: dict):
    """Проверка корректности ответа."""
    logger.debug('Проверка ответа')
    if not isinstance(response, dict):
        raise TypeError
    # С моржом проверки не проходят при отправке. Версия питона 3.7
    missed_keys = {'homeworks', 'current_date'}
    if missed_keys - response.keys():
        logger.error(f'В ответе API нет ожидаемых ключей: {missed_keys}')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError
    if not response.get('homeworks'):  # Проверка, что список не пустой.
        raise HomeworkNotFound


def parse_status(homework):
    """На входе json последней работы, формирует строку сообщения."""
    logger.debug('формирование строки сообщения')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise UnknownHomeworkStatus
    if not homework.get('homework_name'):
        raise NoHomeworkName
    verdict = HOMEWORK_VERDICTS[status]
    homework_name = homework['homework_name']
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    last_message = ''
    last_error_message = ''

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 1673332499  # 10.01.2023

    if not check_tokens():
        logger.critical('Отсутствует обязательная переменная окружения')
        sys.exit('Принудительное завершение')

    while True:
        try:
            res = get_api_answer(timestamp)
            check_response(res)
            homework = res.get('homeworks')[0]
            message = parse_status(homework)
            if message != last_message:
                send_message(bot, message)
                last_message = message
        except Exception as e:
            error_message = f'Сбой в работе программы: {e}'
            logger.error(error_message)
            if error_message != last_error_message:
                send_message(bot, error_message)
                last_error_message = error_message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
