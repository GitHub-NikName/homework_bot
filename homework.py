import os
import sys
import time
import logging
import requests

from dotenv import load_dotenv
from telegram import Bot
from telegram.error import TelegramError

from exeptions import EndpointNotAvailable, HomeworkNotFound, NoHomeworkName,\
    UnknownHomeworkStatus, MissingEnvironmentVariable


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


def check_tokens(bot):
    """Если нет обязательных переменных окружения вызывает исключение."""
    env = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')
    try:
        for i in env:
            if i not in globals():
                raise MissingEnvironmentVariable(i)
    except MissingEnvironmentVariable as e:
        logger.critical(e)
        if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            send_message(bot, str(e))
        raise


def send_message(bot, message):
    """Отправляет сообщение в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение "{message}"')
    except TelegramError as e:
        logger.error(e)


def get_api_answer(timestamp):
    """Возвращает json, если доступен."""
    try:
        params = {'from_date': timestamp}
        res = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if res.status_code != 200:
            raise EndpointNotAvailable(ENDPOINT, res)
        return res.json()
    except requests.RequestException:
        logging.error('No response')


def check_response(response):
    """На входе json."""
    if not isinstance(response, dict):
        raise TypeError
    if not isinstance(response.get('homeworks'), list):
        raise TypeError
    if not response.get('homeworks'):
        raise HomeworkNotFound


def parse_status(homework):
    """На входе json последней работы, формирует строку сообщения."""
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
    # status = ('Последний статус: ', 'Статус изменился: ')[bool(last_message)]

    bot = Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - 1673332499  # 10.01.2023

    check_tokens(bot)

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
