from arclet.entari import BasicConfModel, plugin_config


class Config(BasicConfModel):
    coin: int | tuple[int, int] = (50, 100)
    exp: int | tuple[int, int] = 100
    favor: int | tuple[int, int] = (10, 20)


config = plugin_config(Config)
