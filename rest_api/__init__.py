from fastapi import FastAPI
from mcdreforged.api.all import PluginServerInterface

app = FastAPI()
fastapi_mcdr = None


def on_load(s: PluginServerInterface, _):
    global fastapi_mcdr
    fastapi_mcdr = s.get_plugin_instance("fastapi_mcdr")
    if fastapi_mcdr is not None and fastapi_mcdr.is_ready():
        mount_app(s)
        s.register_event_listener(fastapi_mcdr.COLLECT_EVENT, mount_app)
        s.logger.info("RESTAPI loaded.")
    else:
        s.logger.warning("Failed to init RESTAPI.")


def mount_app(s: PluginServerInterface):
    id_ = s.get_self_metadata().id
    if fastapi_mcdr is not None:
        fastapi_mcdr.mount(id_, app)


@app.get("/greet", summary="Debug: greet")
async def debug_greet():
    """Get a greeting message."""
    return "Hello, world!"
