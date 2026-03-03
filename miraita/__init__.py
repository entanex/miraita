from arclet.entari.plugin import load_plugins

from . import apis as apis
from . import configs as configs
from .patch import patch_metadata
from .log import logger as logger
from . import listeners as listeners
from .version import __version__ as __version__

patch_metadata()
load_plugins("miraita/providers")
load_plugins("miraita/plugins")
