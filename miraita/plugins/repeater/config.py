from arclet.entari import BasicConfModel, plugin_config
from arclet.entari.config import model_field


class RepeatAction(BasicConfModel):
    min_times: int = 2
    """最少复读次数"""
    probability: float = 1
    """触发概率，取值范围 0-1"""
    content: str | None = None
    """仅在复读内容完全匹配时触发"""
    user_times: int = 0
    """当前用户最少参与复读次数，0 表示不限制"""
    repeated: bool | None = None
    """限制机器人是否已经复读过，null 表示不限制"""
    reply: str | None = None
    """回复，支持 {content}、{times}、{user_id}、{user_name}、{at_user} 模板"""


class Config(BasicConfModel):
    on_repeat: RepeatAction | list[RepeatAction] | None = model_field(
        default_factory=RepeatAction
    )
    """响应复读消息；设为 null 可禁用自动复读"""
    on_interrupt: RepeatAction | list[RepeatAction] | None = None
    """响应打断复读消息"""


config = plugin_config(Config)
