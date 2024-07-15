import json
from typing import Any

from nicegui import app, ui
from otf_api.api import Otf
from otf_api.auth import OtfUser


class LocalStorage:
    @staticmethod
    def _local_storage_set(key: str, value: Any) -> str:
        return f'localStorage.setItem("{key}", {json.dumps(value)})'

    @staticmethod
    def _local_storage_get(key: str) -> str:
        return f'localStorage.getItem("{key}")'

    @staticmethod
    def set_item(key: str, value: Any) -> None:
        ui.run_javascript(LocalStorage._local_storage_set(key, value))

    @staticmethod
    async def get_item(key: str) -> Any:
        val = await ui.run_javascript(LocalStorage._local_storage_get(key))
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return val

    @staticmethod
    async def get_all_items() -> dict[str, Any]:
        return await ui.run_javascript("localStorage")

    @staticmethod
    def clear() -> None:
        ui.run_javascript("localStorage.clear()")


def add_user_to_storage(user: OtfUser) -> None:
    app.storage.user["tokens"] = user.get_tokens()
    # app.storage.user["device_key"] = user.device_key
    LocalStorage.set_item("device_key", user.device_key)
    app.storage.tab["user"] = user


def add_otf_to_storage(otf: Otf) -> None:
    app.storage.tab["otf"] = otf
    LocalStorage.set_item("device_key", otf.user.device_key)
    app.storage.user["otf_hydration_dict"] = otf.get_hydration_dict()


def clear_all_storage() -> None:
    app.storage.user.clear()
    app.storage.tab.clear()
    LocalStorage.clear()
