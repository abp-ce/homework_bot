# homework_bot
- раз в 10 минут опрашивает API сервиса Практикум.Домашка и проверяут статус отправленной на ревью домашней работы,
- при обновлении статуса анализирует ответ API и отправляет мне соответствующее уведомление в Telegram,
- логирует свою работу и сообщает мне о важных проблемах сообщением в Telegram.
#
### Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/abp-ce/homework_bot.git
```

```
cd homework_bot
```

Cоздать и активировать виртуальное окружение:

```
python3 -m venv venv
```

```
source venv/bin/activate
```

```
python -m pip install --upgrade pip
```

Установить зависимости из файла requirements.txt:

```
pip install -r requirements.txt
```

Запустить проект:

```
python manage.py runserver
```

### Стек:
- python-telegram-bot 13.7