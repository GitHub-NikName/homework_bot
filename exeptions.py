class CustumException(Exception):
    pass


class EndpointNotAvailable(CustumException):
    def __init__(self, url, res):
        status = res.status_code
        message = f'Эндпоинт {url} недоступен. Код ответа API: {status}'
        if status == 400:
            json = res.json()
            msg = f' code: {json["code"]} error: {json["error"]["error"]}'
        if status == 401:
            json = res.json()
            msg = f' code: {json["code"]} message: {json["message"]}'
        message += msg
        super().__init__(message)


class MessageNotSend(CustumException):
    def __init__(self):
        super().__init__('Ошибка отправки сообщения')


class MissingEnvironmentVariable(CustumException):
    def __init__(self, value):
        super().__init__(
            f'Отсутствует обязательная переменная окружения: "{value}". '
            f'Программа принудительно остановлена.')


class HomeworkNotFound(CustumException):
    def __init__(self):
        super().__init__('Нет домашки. Может timestamp увеличить?')


class UnknownHomeworkStatus(CustumException):
    def __init__(self):
        super().__init__('Домашку ещё не взяли в работу')


class NoHomeworkName(CustumException):
    def __init__(self):
        super().__init__('Нет ключа homework_name. А должен...')
