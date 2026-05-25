from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any, Literal

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
)

from app.schemas.disk_set import DiskSetDiskRequest


class WebFormError(Exception):
    def __init__(
        self,
        message: str,
        field_errors: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.field_errors = field_errors or {}
        super().__init__(message)


def _field_errors(exc: ValidationError) -> dict[str, str]:
    field_errors: dict[str, str] = {}
    for error in exc.errors():
        location = error.get("loc", ())
        field = str(location[0]) if location else "form"
        message = str(error.get("msg", "Invalid value"))
        if message.startswith("Value error, "):
            message = message.removeprefix("Value error, ")
        field_errors.setdefault(field, message)
    return field_errors


class LoginFormData(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterFormData(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class CipherFormData(BaseModel):
    mode: Literal["encrypt", "decrypt"]
    text: str = Field(min_length=1)
    disk_set_id: int = Field(gt=0)
    disk_order: list[int]
    offset: int

    @field_validator("disk_set_id", "offset", mode="before")
    @classmethod
    def reject_booleans_for_numbers(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("Недопустимое число.")
        return value

    @field_validator("disk_order", mode="before")
    @classmethod
    def parse_disk_order(cls, value: Any) -> list[int]:
        if isinstance(value, str):
            parts = [part.strip() for part in value.split(",")]
            disk_order: list[int] = []
            for part in parts:
                if not part:
                    continue
                if part.lower() in {"true", "false"}:
                    raise ValueError("Порядок дисков должен содержать только числа.")
                try:
                    disk_order.append(int(part))
                except ValueError as exc:
                    raise ValueError(
                        "Порядок дисков должен содержать только числа."
                    ) from exc
            if not disk_order:
                raise ValueError("Введите порядок дисков через запятую.")
            return disk_order

        if isinstance(value, Iterable):
            disk_order = []
            for item in value:
                if isinstance(item, bool):
                    raise ValueError("Порядок дисков должен содержать только числа.")
                try:
                    disk_order.append(int(item))
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        "Порядок дисков должен содержать только числа."
                    ) from exc
            if not disk_order:
                raise ValueError("Введите порядок дисков через запятую.")
            return disk_order

        raise ValueError("Введите порядок дисков через запятую.")


class DiskSetFormData(BaseModel):
    name: str = Field(min_length=1)
    slug: str = Field(min_length=1)
    alphabet: str = Field(min_length=1)
    disks: list[DiskSetDiskRequest]
    csrf_token: str = Field(min_length=1)

    @field_validator("disks", mode="before")
    @classmethod
    def parse_disks(
        cls,
        value: Any,
        info: ValidationInfo,
    ) -> list[DiskSetDiskRequest]:
        if not isinstance(value, str):
            raise ValueError(
                "Введите строки дисков в формате номер:последовательность."
            )

        alphabet = info.data.get("alphabet") if info.data else ""
        if not isinstance(alphabet, str):
            alphabet = ""
        expected_length = len(alphabet) if alphabet else None

        disks: list[DiskSetDiskRequest] = []
        seen_positions: set[int] = set()
        for line_number, raw_line in enumerate(value.splitlines(), start=1):
            if not raw_line.strip():
                continue
            line = raw_line
            if ":" not in line:
                raise ValueError(
                    f"Строка {line_number}: "
                    "используйте формат номер:последовательность."
                )

            position_text, sequence = line.split(":", 1)
            position_text = position_text.strip()
            if not position_text:
                raise ValueError(f"Строка {line_number}: нужен номер диска.")
            try:
                position = int(position_text)
            except ValueError as exc:
                raise ValueError(
                    f"Строка {line_number}: номер диска должен быть целым числом."
                ) from exc
            if not sequence.strip():
                raise ValueError(
                    f"Строка {line_number}: "
                    "последовательность диска не может быть пустой."
                )
            if position in seen_positions:
                raise ValueError(
                    f"Строка {line_number}: дублируется номер диска {position}."
                )
            if " " in sequence:
                raise ValueError(
                    f"Строка {line_number}: "
                    "последовательность диска не должна содержать пробелы."
                )
            if expected_length is not None and len(sequence) != expected_length:
                raise ValueError(
                    f"Строка {line_number}: "
                    f"диск должен содержать {expected_length} символов, "
                    f"сейчас {len(sequence)}."
                )
            if alphabet and Counter(sequence) != Counter(alphabet):
                raise ValueError(
                    f"Строка {line_number}: "
                    "диск должен содержать все символы алфавита ровно один раз."
                )
            seen_positions.add(position)
            disks.append(DiskSetDiskRequest(position=position, sequence=sequence))

        if not disks:
            raise ValueError("Введите хотя бы одну строку диска.")
        disks.sort(key=lambda disk: disk.position)
        return disks


def parse_login_form(email: str, password: str) -> LoginFormData:
    try:
        return LoginFormData(email=email, password=password)
    except ValidationError as exc:
        raise WebFormError(
            "Укажите корректный email и пароль.",
            _field_errors(exc),
        ) from exc


def parse_register_form(email: str, password: str) -> RegisterFormData:
    try:
        return RegisterFormData(email=email, password=password)
    except ValidationError as exc:
        raise WebFormError(
            "Укажите корректный email и пароль.",
            _field_errors(exc),
        ) from exc


def parse_cipher_form(
    mode: str,
    text: str,
    disk_set_id: Any,
    disk_order: str,
    offset: Any,
) -> CipherFormData:
    try:
        return CipherFormData(
            mode=mode,
            text=text,
            disk_set_id=disk_set_id,
            disk_order=disk_order,
            offset=offset,
        )
    except ValidationError as exc:
        raise WebFormError(
            "Исправьте выделенные поля шифра.",
            _field_errors(exc),
        ) from exc


def parse_disk_set_form(
    name: str,
    slug: str,
    alphabet: str,
    disks: str,
    csrf_token: str,
) -> DiskSetFormData:
    try:
        return DiskSetFormData(
            name=name,
            slug=slug,
            alphabet=alphabet,
            disks=disks,
            csrf_token=csrf_token,
        )
    except ValidationError as exc:
        raise WebFormError(
            "Исправьте выделенные поля набора дисков.",
            _field_errors(exc),
        ) from exc
