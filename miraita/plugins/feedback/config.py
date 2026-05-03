from arclet.entari import BasicConfModel, plugin_config


class Config(BasicConfModel):
    broadcast_delay: float = 0
    """向多个反馈接收频道发送时的间隔，单位为秒"""


config = plugin_config(Config)
