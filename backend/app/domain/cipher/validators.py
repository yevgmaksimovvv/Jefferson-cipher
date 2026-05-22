from app.domain.cipher.exceptions import (
    DuplicateDiskNumberError,
    InvalidAlphabetError,
    InvalidConfigurationError,
    InvalidDiskPermutationError,
    MissingDiskNumberError,
)
from app.domain.cipher.models import CipherKey, Disk, DiskSet

_MVP_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def validate_alphabet(alphabet: str) -> None:
    if not isinstance(alphabet, str) or not alphabet:
        raise InvalidAlphabetError
    if alphabet != _MVP_ALPHABET:
        raise InvalidAlphabetError
    if len(set(alphabet)) != len(alphabet):
        raise InvalidAlphabetError


def validate_disk(disk: Disk, alphabet: str) -> None:
    validate_alphabet(alphabet)
    if not isinstance(disk.sequence, str):
        raise InvalidDiskPermutationError
    if len(disk.sequence) != len(alphabet):
        raise InvalidDiskPermutationError
    if set(disk.sequence) != set(alphabet):
        raise InvalidDiskPermutationError


def validate_disk_set(disk_set: DiskSet) -> None:
    validate_alphabet(disk_set.alphabet)
    if not disk_set.disks:
        raise InvalidConfigurationError

    seen_ids: set[int] = set()
    for disk in disk_set.disks:
        if disk.id in seen_ids:
            raise DuplicateDiskNumberError
        seen_ids.add(disk.id)

    for disk in disk_set.disks:
        validate_disk(disk, disk_set.alphabet)


def validate_key(key: CipherKey, disk_set: DiskSet) -> None:
    if not key.disk_order:
        raise InvalidConfigurationError
    if isinstance(key.offset, bool) or not isinstance(key.offset, int):
        raise InvalidConfigurationError

    disk_ids = {disk.id for disk in disk_set.disks}
    seen_ids: set[int] = set()
    for disk_id in key.disk_order:
        if disk_id in seen_ids:
            raise DuplicateDiskNumberError
        seen_ids.add(disk_id)
        if disk_id not in disk_ids:
            raise MissingDiskNumberError
