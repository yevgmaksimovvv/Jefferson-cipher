from dataclasses import dataclass


@dataclass(frozen=True)
class Disk:
    id: int
    sequence: str


@dataclass(frozen=True)
class DiskSet:
    disks: tuple[Disk, ...]
    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class CipherKey:
    disk_order: tuple[int, ...]
    offset: int


@dataclass(frozen=True)
class CipherStep:
    block_index: int
    char_index: int
    disk_id: int
    input_char: str
    output_char: str
    input_position: int
    output_position: int
    offset: int
    mode: str


@dataclass(frozen=True)
class CipherResult:
    text: str
    normalized_text: str
    trace: tuple[CipherStep, ...]
