from arclet.entari import plugin_config
from arclet.entari.config import model_field, BasicConfModel
from sentry_sdk.integrations import Integration
from sentry_sdk.integrations.loguru import LoguruIntegration


class Config(BasicConfModel):
    dsn: str | None = None
    environment: str = "prod"
    integrations: list[Integration] = model_field(
        default_factory=lambda: [LoguruIntegration()]
    )

    __required__ = ["dsn"]


config = plugin_config(Config)
