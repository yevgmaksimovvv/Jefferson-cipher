from dataclasses import dataclass


@dataclass(frozen=True)
class Disk:
    """Представляет один физический диск шифратора."""

    id: int
    sequence: str


@dataclass(frozen=True)
class DiskSet:
    """Набор дисков и используемый алфавит."""

    disks: tuple[Disk, ...]
    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


@dataclass(frozen=True)
class CipherKey:
    """Ключ шифрования: порядок дисков и сдвиг."""

    disk_order: tuple[int, ...]
    offset: int


@dataclass(frozen=True)
class CipherStep:
    """Один шаг процесса шифрования/дешифрования (для одного символа)."""

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
    """Результат операции: текст и детальный след (trace) преобразования."""

    text: str
    normalized_text: str
    trace: tuple[CipherStep, ...]
