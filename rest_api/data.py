from mcdreforged.api.all import Serializable


class BaseResult(Serializable):
    is_success: bool


class TextResult(BaseResult):
    detail: str | int | float | bool


class JSONResult(BaseResult):
    data: dict | list
