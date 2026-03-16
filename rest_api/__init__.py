from typing import Callable, Awaitable, Any
from fastapi.security import APIKeyHeader
from fastapi import FastAPI, Depends, HTTPException, APIRouter
from mcdreforged.api.all import (
    PluginServerInterface,
    SimpleCommandBuilder,
    CommandSource,
    ServerInterface,
)
from rest_api.config import APIConfig

psi = ServerInterface.psi()
builder = SimpleCommandBuilder()
config: APIConfig | None = None
app = FastAPI()
fastapi_mcdr = None
auth_header = APIKeyHeader(name="Authorization", auto_error=False)
webhooks_router = APIRouter(prefix="/webhooks")
WebhookHandler = Callable[[dict], Awaitable[Any]]


class ConfigError(RuntimeError):
    pass


def on_load(s: PluginServerInterface, _):
    global fastapi_mcdr, config, psi
    fastapi_mcdr = s.get_plugin_instance("fastapi_mcdr")
    config = s.load_config_simple(file_name="config.yml", target_class=APIConfig)  # ty: ignore[invalid-assignment]
    psi = s
    if fastapi_mcdr is not None and fastapi_mcdr.is_ready():
        app.include_router(webhooks_router)
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


def register_webhook_listener(
    path: str,
    handler: WebhookHandler,
    summary: str | None = None,
    require_auth: bool = False,
):
    if not path.startswith("/"):
        path = "/" + path
    if not require_auth:
        webhooks_router.post(path, summary=summary)(handler)
    else:
        webhooks_router.post(
            path, summary=summary, dependencies=[Depends(verify_token)]
        )(handler)


def webhook(path: str, summary: str | None = None, require_auth: bool = False):
    def decorator(func: WebhookHandler):
        register_webhook_listener(path, func, summary, require_auth)
        return func

    return decorator


@app.get("/greet", summary="Debug greet")
async def debug_greet():
    """Get a greeting message."""
    return "Hello, world!"


@app.get("/status", summary="Check status", dependencies=[Depends(verify_token)])
async def check_status():
    """Check API status, will be ok if fine."""
    return "ok"


@app.get(
    "/is_server_running",
    summary="Is server running",
    dependencies=[Depends(verify_token)],
)
async def query_is_server_running():
    """Return if the server is running."""
    return psi.is_server_running()


@app.get(
    "/is_server_startup",
    summary="Is server startup",
    dependencies=[Depends(verify_token)],
)
async def query_is_server_startup():
    """Return if the server has started up."""
    return psi.is_server_startup()
