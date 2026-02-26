from arclet.entari.plugin import load_plugins

from . import apis as apis
from . import configs as configs
from .log import logger as logger
from . import listeners as listeners
from .version import __version__ as __version__

load_plugins("miraita/providers")
load_plugins("miraita/plugins")
