import pytest
from app.domain.cipher import (
    CipherKey,
    Disk,
    DiskSet,
    DuplicateDiskNumberError,
    EmptyTextError,
    InvalidAlphabetError,
    InvalidConfigurationError,
    InvalidDiskPermutationError,
    MissingDiskNumberError,
    normalize_text,
    validate_alphabet,
    validate_disk,
    validate_disk_set,
    validate_key,
)


def _disk_set() -> DiskSet:
    return DiskSet(
        disks=(
            Disk(id=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            Disk(id=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
        )
    )


def _key(
    disk_order: tuple[int, ...] = (1, 2),
    offset: int = 2,
) -> CipherKey:
    return CipherKey(disk_order=disk_order, offset=offset)


def test_invalid_alphabet_raises_invalid_alphabet_error() -> None:
    with pytest.raises(InvalidAlphabetError):
        validate_alphabet("ABCDE")


def test_disk_with_invalid_letters_raises_invalid_disk_permutation_error() -> None:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    with pytest.raises(InvalidDiskPermutationError):
        validate_disk(Disk(id=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXY"), alphabet)
    with pytest.raises(InvalidDiskPermutationError):
        validate_disk(Disk(id=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYA"), alphabet)


def test_duplicate_disk_ids_raises_duplicate_disk_number_error() -> None:
    with pytest.raises(DuplicateDiskNumberError):
        validate_disk_set(
            DiskSet(
                disks=(
                    Disk(id=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
                    Disk(id=1, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
                )
            )
        )


def test_empty_disk_set_raises_invalid_configuration_error() -> None:
    with pytest.raises(InvalidConfigurationError):
        validate_disk_set(DiskSet(disks=()))


def test_empty_text_after_normalization_raises_empty_text_error() -> None:
    with pytest.raises(EmptyTextError):
        normalize_text("12345")


def test_empty_disk_order_raises_invalid_configuration_error() -> None:
    with pytest.raises(InvalidConfigurationError):
        validate_key(_key(disk_order=()), _disk_set())


def test_duplicate_disk_order_ids_raises_duplicate_disk_number_error() -> None:
    with pytest.raises(DuplicateDiskNumberError):
        validate_key(_key(disk_order=(1, 1)), _disk_set())


def test_missing_disk_id_in_disk_order_raises_missing_disk_number_error() -> None:
    with pytest.raises(MissingDiskNumberError):
        validate_key(_key(disk_order=(1, 3)), _disk_set())


def test_non_int_offset_raises_invalid_configuration_error() -> None:
    with pytest.raises(InvalidConfigurationError):
        validate_key(CipherKey(disk_order=(1, 2), offset="2"), _disk_set())


def test_bool_offset_raises_invalid_configuration_error() -> None:
    with pytest.raises(InvalidConfigurationError):
        validate_key(CipherKey(disk_order=(1, 2), offset=True), _disk_set())
