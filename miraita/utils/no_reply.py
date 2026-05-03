from dataclasses import dataclass

from satori.element import Element, register_element


@dataclass
class NoReply(Element): ...


register_element(NoReply)
