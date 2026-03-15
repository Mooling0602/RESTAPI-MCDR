from mcdreforged.api.all import Serializable


class APIConfig(Serializable):
    api_token: str = "token_changethis"
    allow_modify_mcdr: bool = False
