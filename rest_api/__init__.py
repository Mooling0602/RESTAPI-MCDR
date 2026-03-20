from typing import Any, Awaitable, Callable

from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException
from fastapi.security import APIKeyHeader
from mcdreforged.api.all import (
    CommandSource,
    PluginServerInterface,
    RColor,
    RText,
    ServerInterface,
    SimpleCommandBuilder,
)

try:
    import moolings_rcon_api as rcon_api
except (ImportError, ModuleNotFoundError):
    rcon_api = None  # ty: ignore[invalid-assignment]
from rest_api.config import APIConfig
from rest_api.data import TextResult

psi = ServerInterface.psi()
builder = SimpleCommandBuilder()
_config: APIConfig = APIConfig()
app = FastAPI()
fastapi_mcdr = None
auth_header = APIKeyHeader(name="Authorization", auto_error=False)
webhooks_router = APIRouter(prefix="/webhooks")
WebhookHandler = Callable[[dict], Awaitable[Any]]


class ConfigError(RuntimeError):
    pass


def on_load(s: PluginServerInterface, _):
    global fastapi_mcdr, _config, psi, rcon_api
    fastapi_mcdr = s.get_plugin_instance("fastapi_mcdr")
    _config = s.load_config_simple(file_name="config.yml", target_class=APIConfig)  # ty: ignore[invalid-assignment]
    psi = s
    # noinspection SpellCheckingInspection
    rcon_api = s.get_plugin_instance("moolings_rcon_api")  # ty: ignore[invalid-assignment]
    if fastapi_mcdr is not None and fastapi_mcdr.is_ready():
        app.include_router(webhooks_router)
        mount_app(s)
        s.register_event_listener(fastapi_mcdr.COLLECT_EVENT, mount_app)
        builder.register(s)
        s.logger.info("RESTAPI loaded.")
        if hasattr(fastapi_mcdr, "__uvicorn_server"):
            __uvicorn_server = fastapi_mcdr.__uvicorn_server
            if hasattr(__uvicorn_server, "config"):
                _port = __uvicorn_server.config.port
                _host = __uvicorn_server.config.host
                docs_url = (
                    RText(f"http://{_host}:{_port}/rest_api/docs")
                    .set_color(RColor.green)
                    .to_colored_text()
                )
                s.logger.info("For RESTAPI docs, see: " + docs_url)
    else:
        s.logger.warning("Failed to init RESTAPI.")


@builder.command("!!rest_api token")
def get_token(src: CommandSource):
    if not src.is_console:
        src.reply(
            "You can only get token in console! Please execute this command again in MCDR console."
        )
        return
    if _config is None:
        src.reply("Failed to get token, is config right?")
        return
    if _config.api_token == APIConfig().api_token:
        src.reply(
            f"Token is the default value, please change it in: {psi.get_data_folder()}/config.yml"
        )
        src.reply("Current token: ")
    src.reply(_config.api_token)


def mount_app(s: PluginServerInterface):
    id_ = s.get_self_metadata().id
    if fastapi_mcdr is not None:
        fastapi_mcdr.mount(id_, app)


def verify_token(token: str | None = Depends(auth_header)):
    if _config is None:
        raise ConfigError("Failed to load config!")
    if token != _config.api_token:
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
    "/query/is_server_running",
    summary="Is server running",
    dependencies=[Depends(verify_token)],
)
async def query_is_server_running():
    """Return if the server is running."""
    return psi.is_server_running()


@app.get(
    "/query/is_server_startup",
    summary="Is server startup",
    dependencies=[Depends(verify_token)],
)
async def query_is_server_startup():
    """Return if the server has started up."""
    return psi.is_server_startup()


@app.get(
    "/query/is_rcon_running",
    summary="Is rcon running",
    dependencies=[Depends(verify_token)],
)
async def query_is_rcon_running():
    # noinspection SpellCheckingInspection
    """Return if MCDR’s rcon is running"""
    return psi.is_rcon_running()


@app.get(
    "/query/server/pid",
    summary="Query server PID",
    dependencies=[Depends(verify_token)],
)
async def query_server_pid():
    """Return the pid of the server process.

    **Note**: the process with this pid is a bash process, which is the parent process of real server process you might be interested in.
    """
    return psi.get_server_pid()


@app.get(
    "/query/server/pid_all",
    summary="Query server all PIDs",
    dependencies=[Depends(verify_token)],
)
async def query_server_pid_all():
    """Return a list of pid of all processes in the server's process group."""
    return psi.get_server_pid_all()


@app.get(
    "/query/server/info",
    summary="Query server informations",
    dependencies=[Depends(verify_token)],
)
async def query_server_info():
    """Return a `ServerInformation` object indicating the information of the current server, interred from the output of the server.

    It's field(s) might be `None` if the server is offline, or the related information has not been parsed.
    """
    return psi.get_server_information()


@app.get(
    "/query/server/ver",
    summary="Query server version",
    dependencies=[Depends(verify_token)],
)
async def query_server_ver():
    """Return the version string of the Minecraft server.

    Might be `None` if the server is offline, or the related information has not been parsed.
    """
    return psi.get_server_information().version


@app.get(
    "/query/server/ip",
    summary="Query server IP",
    dependencies=[Depends(verify_token)],
)
async def query_server_ip():
    """Return the IP address of the Minecraft server.

    Might be `None` if the server is offline, or the related information has not been parsed.
    """
    return psi.get_server_information().ip


@app.get(
    "/query/server/port",
    summary="Query server port",
    dependencies=[Depends(verify_token)],
)
async def query_server_port():
    """Return the port number of the Minecraft server.

    Might be `None` if the server is offline, or the related information has not been parsed.
    """
    return psi.get_server_information().port


@app.get(
    "/query/plugin/list",
    summary="Get MCDR plugin list",
    dependencies=[Depends(verify_token)],
)
async def query_plugin_list():
    """Return a list containing all loaded plugin id like `["my_plugin", "another_plugin"]`."""
    return psi.get_plugin_list()


@app.get(
    "/query/plugin/list_unloaded",
    summary="Get MCDR unloaded plugin list",
    dependencies=[Depends(verify_token)],
)
async def query_plugin_list_unloaded():
    """Return a list containing all unloaded plugin file path like `["plugins/MyPlugin.mcdr"]`."""
    return psi.get_unloaded_plugin_list()


@app.get(
    "/query/plugin/list_disabled",
    summary="Get MCDR disabled plugin list",
    dependencies=[Depends(verify_token)],
)
async def query_plugin_list_disabled():
    """Return a list containing all disabled plugin file path like `["plugins/MyPlugin.mcdr"]`."""
    return psi.get_disabled_plugin_list()


@app.get(
    "/query/plugin/type",
    summary="Query plugin type",
    dependencies=[Depends(verify_token)],
)
async def query_plugin_type(plugin_id: str):
    """Return the type of the specified plugin, or None if failed to query."""
    return psi.get_plugin_type(plugin_id)


@app.get(
    "/query/plugin/meta",
    summary="Query plugin metadata",
    dependencies=[Depends(verify_token)],
)
async def query_plugin_meta(plugin_id: str):
    """Return the metadata of the specified plugin, or `None` if the plugin doesn't exist."""
    return psi.get_plugin_metadata(plugin_id)


@app.get(
    "/query/plugin/file_path",
    summary="Query plugin file path",
    dependencies=[Depends(verify_token)],
)
async def query_plugin_file_path(plugin_id: str):
    """Return the file path of the specified plugin, or `None` if the plugin doesn't exist."""
    return psi.get_plugin_file_path(plugin_id)


@app.get(
    "/query/mcdr/language",
    summary="Query MCDR language",
    dependencies=[Depends(verify_token)],
)
async def query_mcdr_language():
    """Return the current language MCDR is using."""
    return psi.get_mcdr_language()


@app.post("/rcon", summary="Query rcon result", dependencies=[Depends(verify_token)])
async def query_rcon(data: dict = Body(..., examples=[{"command": "list"}])):
    """Send command to the server through rcon connection, and get the result of the execution."""
    try:
        command: str | None = data.get("command", None)
        if not command:
            return TextResult(
                is_success=False, detail="Error: failed to parse query command."
            )
        if rcon_api:
            result = await rcon_api.rcon_get(psi, command)
        result = psi.rcon_query(command)
        if not isinstance(result, str):
            result = None
        return TextResult(is_success=True, detail=result)
    except Exception as e:
        return TextResult(is_success=True, detail=f"Error: {str(e)}")


@app.post("/logger", summary="Log message", dependencies=[Depends(verify_token)])
async def api_logger(msg: str = Body(...)):
    """Log a message to MCDR console."""
    try:
        psi.logger.info(f"[/logger] {msg}")
        return TextResult(is_success=True, detail="Message logged.")
    except Exception as e:
        return TextResult(is_success=False, detail=f"Error: {str(e)}")


@app.post(
    "/server/broadcast",
    summary="Broadcast message to MCDR, server",
    dependencies=[Depends(verify_token)],
)
@app.post(
    "/logger_all",
    summary="Log message all (alias of /server/broadcast)",
    dependencies=[Depends(verify_token)],
)
async def api_logger_all(msg: str = Body(...)):
    """Broadcast the message in game and to the console.

    If the server is not running, send the message to console only.
    """
    try:
        psi.broadcast(f"[RESTAPI] [/logger] {msg}")
        return TextResult(
            is_success=True, detail="Message logged to console and server."
        )
    except Exception as e:
        return TextResult(is_success=False, detail=f"Error: {str(e)}")


@app.post(
    "/server/say",
    summary="Broadcast message to server",
    dependencies=[Depends(verify_token)],
)
async def api_server_say(msg: str = Body(...)):
    """Use command like `/tellraw @a` to broadcast the message in game."""
    try:
        psi.say(f"[RESTAPI] {msg}")
        return TextResult(is_success=True, detail="Message is sent to server.")
    except Exception as e:
        return TextResult(is_success=False, detail=f"Error: {str(e)}")
