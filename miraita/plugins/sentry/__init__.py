import sentry_sdk

from arclet.entari import metadata

from .config import config, Config

metadata(
    name="Sentry",
    author=[{"name": "Komorebi", "email": "mute231010@gmail.com"}],
    description="Sentry 监控",
    classifier=["工具"],
    config=Config,
)


sentry_sdk.init(**config.__dict__)
