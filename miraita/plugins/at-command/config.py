from arclet.entari import BasicConfModel, plugin_config


class Config(BasicConfModel):
    execute: str = "help"
    """要调用的指令"""


config = plugin_config(Config)
