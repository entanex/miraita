from arclet.entari import BasicConfModel, plugin_config


class Config(BasicConfModel):
    execute: str = "help"
    """要调用的指令"""
    allow_arguments: bool = False
    """是否将「@机器人」后的消息元素作为指令参数解析"""


config = plugin_config(Config)
