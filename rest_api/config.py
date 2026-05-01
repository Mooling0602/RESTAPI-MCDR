from mcdreforged.api.all import Serializable


class APIConfig(Serializable):
    # noinspection SpellCheckingInspection
    greet_message: str = "Hello, world!"  # used for api ping without any auth
    api_token: str = "token_changethis"
    allow_modify_mcdr: bool = False
