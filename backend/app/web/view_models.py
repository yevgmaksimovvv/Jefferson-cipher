from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class NavLinkView:
    label: str
    href: str
    active: bool = False


@dataclass(slots=True)
class AlertView:
    kind: str
    message: str


@dataclass(slots=True)
class DiskSetOptionView:
    id: int
    name: str
    slug: str
    badge: str
    selected: bool = False


@dataclass(slots=True)
class CipherFormView:
    mode: str = "encrypt"
    text: str = ""
    disk_set_id: int = 0
    disk_order: str = ""
    offset: int = 0
    include_trace: bool = True


@dataclass(slots=True)
class CipherTraceStepView:
    block_index: int
    char_index: int
    disk_id: int
    input_char: str
    output_char: str
    input_position: int
    output_position: int
    offset: int
    mode: str


@dataclass(slots=True)
class CipherResultView:
    text: str
    normalized_text: str
    trace: list[CipherTraceStepView] = field(default_factory=list)
