from app.domain.cipher import (
    CipherKey,
    CipherResult,
    Disk,
    DiskSet,
    decrypt,
    encrypt,
    normalize_text,
)


def _disk_set() -> DiskSet:
    return DiskSet(
        disks=(
            Disk(id=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            Disk(id=2, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
            Disk(id=3, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
            Disk(id=4, sequence="DEFGHIJKLMNOPQRSTUVWXYZABC"),
        )
    )


def _key(offset: int = 2) -> CipherKey:
    return CipherKey(disk_order=(1, 2, 3, 4), offset=offset)


def test_normalize_text_removes_non_letters() -> None:
    assert normalize_text("Hello, World! 123") == "HELLOWORLD"


def test_encrypt_with_simple_disks_returns_expected_text() -> None:
    result = encrypt("HELLOWORLD", _disk_set(), _key())
    assert result.text == "JGNNQYQTNF"
    assert isinstance(result, CipherResult)


def test_decrypt_reverses_encrypt() -> None:
    disk_set = _disk_set()
    key = _key()

    encrypted = encrypt("HELLOWORLD", disk_set, key)
    decrypted = decrypt(encrypted.text, disk_set, key)

    assert decrypted.text == "HELLOWORLD"


def test_trace_contains_one_step_per_normalized_char() -> None:
    result = encrypt("HELLOWORLD", _disk_set(), _key())

    assert len(result.trace) == len(result.normalized_text)

    step = result.trace[0]
    assert step.block_index == 0
    assert step.char_index == 0
    assert step.disk_id == 1
    assert step.input_char == "H"
    assert step.output_char == "J"
    assert step.input_position == 7
    assert step.output_position == 9
    assert step.offset == 2
    assert step.mode == "encrypt"


def test_trace_reports_second_block_indices() -> None:
    result = encrypt("HELLOWORLD", _disk_set(), _key())

    step = result.trace[4]
    assert step.block_index == 1
    assert step.char_index == 0


def test_decrypt_trace_mode_is_decrypt_for_all_steps() -> None:
    result = decrypt("JGNNQYQTNF", _disk_set(), _key())

    assert {step.mode for step in result.trace} == {"decrypt"}


def test_sparse_disk_ids_work_by_id() -> None:
    disk_set = DiskSet(
        disks=(
            Disk(id=10, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            Disk(id=20, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
            Disk(id=30, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
        )
    )
    key = CipherKey(disk_order=(10, 20, 30), offset=2)

    result = encrypt("ABC", disk_set, key)

    assert result.text == "CDE"
    assert result.normalized_text == "ABC"


def test_disk_set_tuple_order_does_not_override_disk_id_lookup() -> None:
    ordered_disk_set = DiskSet(
        disks=(
            Disk(id=10, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            Disk(id=20, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
            Disk(id=30, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
        )
    )
    shuffled_disk_set = DiskSet(
        disks=(
            Disk(id=30, sequence="CDEFGHIJKLMNOPQRSTUVWXYZAB"),
            Disk(id=10, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            Disk(id=20, sequence="BCDEFGHIJKLMNOPQRSTUVWXYZA"),
        )
    )
    key = CipherKey(disk_order=(10, 20, 30), offset=2)

    ordered_result = encrypt("ABC", ordered_disk_set, key)
    shuffled_result = encrypt("ABC", shuffled_disk_set, key)

    assert shuffled_result.text == ordered_result.text == "CDE"


def test_negative_offset_round_trip_returns_normalized_plaintext() -> None:
    disk_set = _disk_set()
    key = _key(-1)

    encrypted = encrypt("Hello, World!", disk_set, key)
    decrypted = decrypt(encrypted.text, disk_set, key)

    assert decrypted.text == "HELLOWORLD"


def test_offset_26_with_identity_disks_is_identity() -> None:
    disk_set = DiskSet(
        disks=(
            Disk(id=1, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            Disk(id=2, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            Disk(id=3, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            Disk(id=4, sequence="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        )
    )

    result = encrypt("HELLOWORLD", disk_set, _key(26))

    assert result.text == result.normalized_text == "HELLOWORLD"


def test_offset_is_normalized_by_alphabet_length() -> None:
    disk_set = _disk_set()
    result_with_offset_2 = encrypt("HELLOWORLD", disk_set, _key(2))
    result_with_offset_28 = encrypt("HELLOWORLD", disk_set, _key(28))

    assert result_with_offset_28.text == result_with_offset_2.text
    assert result_with_offset_28.trace[0].offset == 2
