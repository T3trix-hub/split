"""
Проверка подлинности initData, которую мини-апп присылает на бэкенд.
Без этого шага любой человек может подделать запрос и назваться другим пользователем.
Алгоритм из официальной документации Telegram:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
"""
import hashlib
import hmac
import json
import os
from urllib.parse import parse_qsl

BOT_TOKEN = os.environ["BOT_TOKEN"]


def validate_init_data(init_data: str) -> dict:
    """
    Возвращает распарсенные данные пользователя, если подпись верна.
    Бросает ValueError, если initData подделана или устарела.
    """
    parsed = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("hash отсутствует в initData")

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )
    secret_key = hmac.new(
        key=b"WebAppData", msg=BOT_TOKEN.encode(), digestmod=hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(
        key=secret_key, msg=data_check_string.encode(), digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Неверная подпись initData — запрос не от Telegram")

    user_raw = parsed.get("user")
    return json.loads(user_raw) if user_raw else {}

