from arclet.entari import BasicConfModel, plugin_config
from arclet.entari.config import model_field


type_map = {
    "动画": "a",
    "漫画": "b",
    "游戏": "c",
    "文学": "d",
    "原创": "e",
    "网络": "f",
    "其他": "g",
    "影视": "h",
    "诗词": "i",
    "网易云": "j",
    "哲学": "k",
    "抖机灵": "l",
}


class Config(BasicConfModel):
    type: list[str] = model_field(
        default_factory=lambda: [
            "动画",
            "漫画",
            "游戏",
            "文学",
            "原创",
            "网络",
            "影视",
            "诗词",
            "哲学",
            "网易云",
            "抖机灵",
            "其他",
        ]
    )

    def get_type_codes(self) -> list[str]:
        return [type_map[t] for t in self.type if t in type_map]


config = plugin_config(Config)
