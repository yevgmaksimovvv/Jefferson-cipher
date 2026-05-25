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
    badge_label: str
    selected: bool = False


@dataclass(slots=True)
class DiskSetCardView:
    id: int
    name: str
    slug: str
    badge: str
    badge_label: str
    disks_count: int
    alphabet: str
    is_owned: bool = False


@dataclass(slots=True)
class DiskSetFormView:
    name: str = ""
    slug: str = ""
    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    disks: str = ""


@dataclass(slots=True)
class CipherFormView:
    mode: str = "encrypt"
    text: str = ""
    disk_set_id: int = 0
    disk_order: str = ""
    offset: int = 0
    explanation_open: bool = False


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
class CipherDiskInfoView:
    id: int
    sequence: str


@dataclass(slots=True)
class CipherResultView:
    text: str
    mode: str = ""
    disk_set_name: str = ""
    disk_order: list[int] = field(default_factory=list)
    offset: int = 0
    disks: list[CipherDiskInfoView] = field(default_factory=list)
    trace: list[CipherTraceStepView] = field(default_factory=list)
