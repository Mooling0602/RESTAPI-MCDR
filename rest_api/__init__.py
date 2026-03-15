from fastapi.security import APIKeyHeader
from fastapi import FastAPI, Depends, HTTPException
from mcdreforged.api.all import (
    PluginServerInterface,
    SimpleCommandBuilder,
    CommandSource,
)
from rest_api.config import APIConfig

builder = SimpleCommandBuilder()
config: APIConfig | None = None
app = FastAPI()
fastapi_mcdr = None
auth_header = APIKeyHeader(name="Authorization", auto_error=False)


class ConfigError(RuntimeError):
    pass


def on_load(s: PluginServerInterface, _):
    global fastapi_mcdr, config
    fastapi_mcdr = s.get_plugin_instance("fastapi_mcdr")
    config = s.load_config_simple(file_name="config.yml", target_class=APIConfig)  # ty: ignore[invalid-assignment]
    if fastapi_mcdr is not None and fastapi_mcdr.is_ready():
        mount_app(s)
        s.register_event_listener(fastapi_mcdr.COLLECT_EVENT, mount_app)
        builder.register(s)
        s.logger.info("RESTAPI loaded.")
    else:
        s.logger.warning("Failed to init RESTAPI.")


@builder.command("!!rest_api token")
def get_token(src: CommandSource):
    if not src.is_console:
        src.reply(
            "You can only get token in console! Please execute this command again in MCDR console."
        )
        return
    if config is None:
        src.reply("Failed to get token, is config right?")
        return
    src.reply(config.api_token)


def mount_app(s: PluginServerInterface):
    id_ = s.get_self_metadata().id
    if fastapi_mcdr is not None:
        fastapi_mcdr.mount(id_, app)


def verify_token(token: str | None = Depends(auth_header)):
    if config is None:
        raise ConfigError("Failed to load config!")
    if token != config.api_token:
        raise HTTPException(401, "Invalid token.")
    return token


@app.get("/greet", summary="Debug: greet")
async def debug_greet():
    """Get a greeting message."""
    return "Hello, world!"


@app.get("/status", summary="Check status.", dependencies=[Depends(verify_token)])
async def check_status():
    """Check API status, will be ok if fine."""
    return "ok"
