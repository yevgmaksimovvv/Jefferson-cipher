from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator


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
    include_trace: bool = False

    @field_validator("disk_set_id", "offset", mode="before")
    @classmethod
    def reject_booleans_for_numbers(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("Invalid number")
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
                    raise ValueError("Disk order must contain only numbers")
                try:
                    disk_order.append(int(part))
                except ValueError as exc:
                    raise ValueError("Disk order must contain only numbers") from exc
            if not disk_order:
                raise ValueError("Enter a comma-separated disk order")
            return disk_order

        if isinstance(value, Iterable):
            disk_order = []
            for item in value:
                if isinstance(item, bool):
                    raise ValueError("Disk order must contain only numbers")
                try:
                    disk_order.append(int(item))
                except (TypeError, ValueError) as exc:
                    raise ValueError("Disk order must contain only numbers") from exc
            if not disk_order:
                raise ValueError("Enter a comma-separated disk order")
            return disk_order

        raise ValueError("Enter a comma-separated disk order")


def parse_login_form(email: str, password: str) -> LoginFormData:
    try:
        return LoginFormData(email=email, password=password)
    except ValidationError as exc:
        raise WebFormError(
            "Enter a valid email address and password.",
            _field_errors(exc),
        ) from exc


def parse_register_form(email: str, password: str) -> RegisterFormData:
    try:
        return RegisterFormData(email=email, password=password)
    except ValidationError as exc:
        raise WebFormError(
            "Enter a valid email address and password.",
            _field_errors(exc),
        ) from exc


def parse_cipher_form(
    mode: str,
    text: str,
    disk_set_id: Any,
    disk_order: str,
    offset: Any,
    include_trace: bool,
) -> CipherFormData:
    try:
        return CipherFormData(
            mode=mode,
            text=text,
            disk_set_id=disk_set_id,
            disk_order=disk_order,
            offset=offset,
            include_trace=include_trace,
        )
    except ValidationError as exc:
        raise WebFormError(
            "Fix the highlighted cipher fields.",
            _field_errors(exc),
        ) from exc
