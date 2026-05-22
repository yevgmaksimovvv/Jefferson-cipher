from app.domain.cipher.exceptions import EmptyTextError
from app.domain.cipher.models import CipherKey, CipherResult, CipherStep, DiskSet
from app.domain.cipher.validators import validate_disk_set, validate_key

_MVP_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalize_text(text: str) -> str:
    normalized = "".join(char for char in text.upper() if char in _MVP_ALPHABET)
    if not normalized:
        raise EmptyTextError
    return normalized


def encrypt(text: str, disk_set: DiskSet, key: CipherKey) -> CipherResult:
    return _transform(text, disk_set, key, mode="encrypt")


def decrypt(text: str, disk_set: DiskSet, key: CipherKey) -> CipherResult:
    return _transform(text, disk_set, key, mode="decrypt")


def _transform(text: str, disk_set: DiskSet, key: CipherKey, mode: str) -> CipherResult:
    validate_disk_set(disk_set)
    validate_key(key, disk_set)
    normalized_text = normalize_text(text)

    alphabet_len = len(disk_set.alphabet)
    normalized_offset = key.offset % alphabet_len
    block_size = len(key.disk_order)
    disks_by_id = {disk.id: disk for disk in disk_set.disks}

    output_chars: list[str] = []
    trace: list[CipherStep] = []

    for index, input_char in enumerate(normalized_text):
        block_index = index // block_size
        char_index = index % block_size
        disk_id = key.disk_order[char_index]
        disk = disks_by_id[disk_id]
        input_position = disk.sequence.index(input_char)
        if mode == "encrypt":
            output_position = (input_position + normalized_offset) % alphabet_len
        else:
            output_position = (input_position - normalized_offset) % alphabet_len
        output_char = disk.sequence[output_position]
        output_chars.append(output_char)
        trace.append(
            CipherStep(
                block_index=block_index,
                char_index=char_index,
                disk_id=disk_id,
                input_char=input_char,
                output_char=output_char,
                input_position=input_position,
                output_position=output_position,
                offset=normalized_offset,
                mode=mode,
            )
        )

    return CipherResult(
        text="".join(output_chars),
        normalized_text=normalized_text,
        trace=tuple(trace),
    )
