from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.init_db import DEFAULT_DISK_SET_SLUG
from app.db.models import DiskSetModel
from app.db.session import get_db
from app.domain.cipher.exceptions import CipherDomainError
from app.domain.cipher.models import CipherKey
from app.services.auth import (
    DuplicateEmailError,
    InvalidRefreshTokenError,
    authenticate_user,
    issue_token_pair,
    logout_refresh_token,
    register_user,
)
from app.services.cipher_from_disk_set import (
    decrypt_with_disk_set_id,
    encrypt_with_disk_set_id,
)
from app.services.disk_sets import (
    DiskSetNotFoundError,
    DiskSetSlugAlreadyExistsError,
    DiskSetValidationError,
    create_user_disk_set,
    delete_user_disk_set,
    get_any_disk_set_by_id,
    list_disk_sets,
    update_user_disk_set,
)
from app.web.auth import (
    WebSessionState,
    clear_web_session_cookies,
    resolve_web_csrf_token,
    resolve_web_session,
    set_web_csrf_cookie,
    set_web_session_cookies,
    validate_web_csrf_token,
)
from app.web.forms import (
    WebFormError,
    parse_cipher_form,
    parse_disk_set_form,
    parse_login_form,
    parse_register_form,
)
from app.web.view_models import (
    AlertView,
    CipherDiskInfoView,
    CipherFormView,
    CipherResultView,
    CipherTraceStepView,
    DiskSetCardView,
    DiskSetFormView,
    DiskSetOptionView,
    NavLinkView,
)

router = APIRouter(include_in_schema=False)
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _nav_links(active_path: str) -> list[NavLinkView]:
    return [
        NavLinkView(label="Главная", href="/", active=active_path == "/"),
        NavLinkView(
            label="Шифр",
            href="/cipher",
            active=active_path.startswith("/cipher"),
        ),
        NavLinkView(
            label="Наборы",
            href="/disk-sets",
            active=active_path.startswith("/disk-sets"),
        ),
        NavLinkView(label="Войти", href="/login", active=active_path == "/login"),
        NavLinkView(
            label="Регистрация",
            href="/register",
            active=active_path == "/register",
        ),
    ]


def _visibility_badge(disk_set: DiskSetModel) -> str:
    if disk_set.owner_id is None and disk_set.slug == DEFAULT_DISK_SET_SLUG:
        return "system"
    if disk_set.owner_id is None:
        return "public"
    return "private"


def _visibility_label(disk_set: DiskSetModel) -> str:
    badge = _visibility_badge(disk_set)
    if badge == "system":
        return "Системный"
    if badge == "public":
        return "Публичный"
    return "Личный"


def _disk_set_card_view(disk_set: DiskSetModel) -> DiskSetCardView:
    return DiskSetCardView(
        id=disk_set.id,
        name=disk_set.name,
        slug=disk_set.slug,
        badge=_visibility_badge(disk_set),
        badge_label=_visibility_label(disk_set),
        disks_count=len(disk_set.disks),
        alphabet=disk_set.alphabet,
        is_owned=disk_set.owner_id is not None,
    )


def _disk_order_string(disk_set: DiskSetModel | None) -> str:
    if disk_set is None:
        return ""
    return ",".join(str(disk.position) for disk in disk_set.disks)


def _disk_set_options(
    disk_sets: list[DiskSetModel],
    selected_disk_set_id: int | None,
) -> list[DiskSetOptionView]:
    return [
        DiskSetOptionView(
            id=disk_set.id,
            name=disk_set.name,
            slug=disk_set.slug,
            badge=_visibility_badge(disk_set),
            badge_label=_visibility_label(disk_set),
            selected=disk_set.id == selected_disk_set_id,
        )
        for disk_set in disk_sets
    ]


def _disk_set_form_view(disk_set: DiskSetModel | None = None) -> DiskSetFormView:
    if disk_set is None:
        return DiskSetFormView()
    return DiskSetFormView(
        name=disk_set.name,
        slug=disk_set.slug,
        alphabet=disk_set.alphabet,
        disks="\n".join(f"{disk.position}:{disk.sequence}" for disk in disk_set.disks),
    )


def _disk_set_alert(action: str) -> AlertView:
    message_map = {
        "created": "Набор дисков создан.",
        "updated": "Набор дисков обновлён.",
        "deleted": "Набор дисков удалён.",
    }
    return _success_alert(message_map.get(action, "Набор дисков обновлён."))


def _disk_set_validation_message(message: str) -> str:
    message_map = {
        "Empty update payload": "Заполните данные набора дисков.",
        "Disks list cannot be empty": "Добавьте хотя бы один диск.",
        "Full disk list required": "Укажите полный список дисков.",
        "InvalidAlphabetError": "Алфавит должен быть полным и без повторов.",
        "InvalidDiskPermutationError": (
            "Диск должен содержать все символы алфавита ровно один раз."
        ),
        "DuplicateDiskNumberError": "Номера дисков не должны повторяться.",
        "MissingDiskNumberError": "Укажите все номера дисков без пропусков.",
        "InvalidConfigurationError": "Проверьте конфигурацию набора дисков.",
    }
    return message_map.get(message, "Проверьте данные набора дисков.")


def _selected_disk_set_model(
    disk_sets: list[DiskSetModel],
    selected_disk_set_id: int | None,
) -> DiskSetModel | None:
    if not disk_sets:
        return None
    if selected_disk_set_id is not None:
        for disk_set in disk_sets:
            if disk_set.id == selected_disk_set_id:
                return disk_set
    return disk_sets[0]


def _selected_disk_set_view(
    disk_sets: list[DiskSetOptionView],
    selected_disk_set_id: int | None,
) -> DiskSetOptionView | None:
    if not disk_sets:
        return None
    if selected_disk_set_id is not None:
        for disk_set in disk_sets:
            if disk_set.id == selected_disk_set_id:
                return disk_set
    for disk_set in disk_sets:
        if disk_set.selected:
            return disk_set
    return disk_sets[0]


def _cipher_result_view(
    result,
    mode: str,
    disk_set: DiskSetModel,
    disk_order: list[int],
    offset: int,
) -> CipherResultView:
    return CipherResultView(
        text=result.text,
        mode="Зашифровать" if mode == "encrypt" else "Расшифровать",
        disk_set_name=disk_set.name,
        disk_order=disk_order,
        offset=offset,
        disks=[
            CipherDiskInfoView(id=disk.position, sequence=disk.sequence)
            for disk in sorted(disk_set.disks, key=lambda d: d.position)
        ],
        trace=[
            CipherTraceStepView(
                block_index=step.block_index,
                char_index=step.char_index,
                disk_id=step.disk_id,
                input_char=step.input_char,
                output_char=step.output_char,
                input_position=step.input_position,
                output_position=step.output_position,
                offset=step.offset,
                mode=step.mode,
            )
            for step in result.trace
        ],
    )


def _error_alert(message: str) -> AlertView:
    return AlertView(kind="error", message=message)


def _success_alert(message: str) -> AlertView:
    return AlertView(kind="success", message=message)


def _cipher_error_message(error: CipherDomainError) -> str:
    message_map = {
        "EmptyTextError": "Введите текст хотя бы с одной буквой A-Z.",
        "InvalidAlphabetError": "У выбранного набора дисков неверный алфавит.",
        "InvalidDiskPermutationError": "Одна из последовательностей дисков неверна.",
        "DuplicateDiskNumberError": "Порядок дисков содержит дублирующиеся номера.",
        "MissingDiskNumberError": (
            "В выбранном наборе нет одного из запрошенных дисков."
        ),
        "InvalidConfigurationError": "Проверьте порядок дисков и смещение.",
    }
    return message_map.get(
        error.__class__.__name__,
        "Не удалось обработать входные данные шифра.",
    )


def _base_context(
    request: Request,
    *,
    current_user,
    alert: AlertView | None = None,
    page_title: str,
    active_path: str,
) -> dict[str, object]:
    return {
        "request": request,
        "current_user": current_user,
        "nav_links": _nav_links(active_path),
        "alert": alert,
        "page_title": page_title,
        "csrf_token": resolve_web_csrf_token(request),
    }


def _cipher_context(
    request: Request,
    db: Session,
    *,
    session_state: WebSessionState,
    form: CipherFormView | None = None,
    selected_disk_set_id: int | None = None,
    alert: AlertView | None = None,
    field_errors: dict[str, str] | None = None,
    result: CipherResultView | None = None,
) -> dict[str, object]:
    disk_set_models = list_disk_sets(
        db,
        session_state.user.id if session_state.user is not None else None,
    )
    disk_sets = _disk_set_options(disk_set_models, selected_disk_set_id)
    selected_disk_set_model = _selected_disk_set_model(
        disk_set_models,
        selected_disk_set_id,
    )
    selected_disk_set = _selected_disk_set_view(disk_sets, selected_disk_set_id)
    if form is None:
        form = _cipher_form_view(
            mode="encrypt",
            text="",
            disk_set_id=selected_disk_set.id if selected_disk_set else 0,
            disk_order=_disk_order_string(selected_disk_set_model),
            offset=0,
            explanation_open=False,
        )

    return {
        **_base_context(
            request,
            current_user=session_state.user,
            alert=alert,
            page_title="Шифр",
            active_path="/cipher",
        ),
        "disk_sets": disk_sets,
        "form": form,
        "field_errors": field_errors or {},
        "result": result,
    }


def _is_truthy_form_flag(value: str) -> bool:
    return value.lower() in {"1", "true", "on", "yes"}


def _cipher_form_view(
    *,
    mode: str,
    text: str,
    disk_set_id: int,
    disk_order: str,
    offset: int,
    explanation_open: bool = False,
) -> CipherFormView:
    return CipherFormView(
        mode=mode,
        text=text,
        disk_set_id=disk_set_id,
        disk_order=disk_order,
        offset=offset,
        explanation_open=explanation_open,
    )


def _apply_session_state(
    response: HTMLResponse,
    session_state: WebSessionState,
    request: Request,
) -> HTMLResponse:
    if session_state.clear_cookies:
        clear_web_session_cookies(response)
    if session_state.refreshed_tokens is not None:
        set_web_session_cookies(response, session_state.refreshed_tokens)
    set_web_csrf_cookie(response, resolve_web_csrf_token(request))
    return response


def _render(
    request: Request,
    template_name: str,
    context: dict[str, object],
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        template_name,
        context,
        status_code=status_code,
    )


@router.get("/", name="web_home")
def home(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    return _apply_session_state(
        _render(
            request,
            "home.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    page_title="Шифр Джефферсона",
                    active_path="/",
                ),
            },
        ),
        session_state,
        request,
    )


@router.get("/register", name="web_register")
def register_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    return _apply_session_state(
        _render(
            request,
            "auth/register.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    page_title="Регистрация",
                    active_path="/register",
                ),
                "form": {"email": ""},
                "field_errors": {},
            },
        ),
        session_state,
        request,
    )


@router.post("/register", name="web_register_submit")
def register_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    email: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(""),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    if not validate_web_csrf_token(request, csrf_token):
        response = _render(
            request,
            "auth/register.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    alert=_error_alert("Неверный CSRF-токен."),
                    page_title="Регистрация",
                    active_path="/register",
                ),
                "form": {"email": email},
                "field_errors": {"form": "Неверный CSRF-токен."},
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
        set_web_csrf_cookie(response, resolve_web_csrf_token(request))
        return response
    try:
        form = parse_register_form(email=email, password=password)
        user = register_user(db, form.email, form.password)
        tokens = issue_token_pair(db, user)
    except WebFormError as error:
        return _apply_session_state(
            _render(
                request,
                "auth/register.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert(error.message),
                        page_title="Регистрация",
                        active_path="/register",
                    ),
                    "form": {"email": email},
                    "field_errors": error.field_errors,
                },
            ),
            session_state,
            request,
        )
    except DuplicateEmailError:
        return _apply_session_state(
            _render(
                request,
                "auth/register.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert("Email уже зарегистрирован."),
                        page_title="Регистрация",
                        active_path="/register",
                    ),
                    "form": {"email": email},
                    "field_errors": {"email": "Email уже зарегистрирован."},
                },
            ),
            session_state,
            request,
        )

    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    set_web_session_cookies(response, tokens)
    set_web_csrf_cookie(response, resolve_web_csrf_token(request))
    return response


@router.get("/login", name="web_login")
def login_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    return _apply_session_state(
        _render(
            request,
            "auth/login.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    page_title="Вход",
                    active_path="/login",
                ),
                "form": {"email": ""},
                "field_errors": {},
            },
        ),
        session_state,
        request,
    )


@router.post("/login", name="web_login_submit")
def login_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    email: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(""),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    if not validate_web_csrf_token(request, csrf_token):
        response = _render(
            request,
            "auth/login.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    alert=_error_alert("Неверный CSRF-токен."),
                    page_title="Вход",
                    active_path="/login",
                ),
                "form": {"email": email},
                "field_errors": {"form": "Неверный CSRF-токен."},
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
        set_web_csrf_cookie(response, resolve_web_csrf_token(request))
        return response
    try:
        form = parse_login_form(email=email, password=password)
    except WebFormError as error:
        return _apply_session_state(
            _render(
                request,
                "auth/login.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert(error.message),
                        page_title="Вход",
                        active_path="/login",
                    ),
                    "form": {"email": email},
                    "field_errors": error.field_errors,
                },
            ),
            session_state,
            request,
        )

    user = authenticate_user(db, form.email, form.password)
    if user is None:
        return _apply_session_state(
            _render(
                request,
                "auth/login.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert("Неверный email или пароль."),
                        page_title="Вход",
                        active_path="/login",
                    ),
                    "form": {"email": email},
                    "field_errors": {
                        "email": "Неверный email или пароль.",
                        "password": "Неверный email или пароль.",
                    },
                },
            ),
            session_state,
            request,
        )

    tokens = issue_token_pair(db, user)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    set_web_session_cookies(response, tokens)
    set_web_csrf_cookie(response, resolve_web_csrf_token(request))
    return response


@router.post("/logout", name="web_logout")
def logout(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    csrf_token: str = Form(""),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    if not validate_web_csrf_token(request, csrf_token):
        response = _render(
            request,
            "home.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    alert=_error_alert("Неверный CSRF-токен."),
                    page_title="Шифр Джефферсона",
                    active_path="/",
                ),
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
        set_web_csrf_cookie(response, resolve_web_csrf_token(request))
        return response
    settings = get_settings()
    refresh_token = request.cookies.get(settings.WEB_REFRESH_COOKIE_NAME)
    if refresh_token:
        with contextlib.suppress(InvalidRefreshTokenError):
            logout_refresh_token(db, refresh_token)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    clear_web_session_cookies(response)
    set_web_csrf_cookie(response, resolve_web_csrf_token(request))
    return response


def _disk_sets_context(
    request: Request,
    db: Session,
    *,
    session_state: WebSessionState,
    alert: AlertView | None = None,
    field_errors: dict[str, str] | None = None,
    form: DiskSetFormView | None = None,
) -> dict[str, object]:
    disk_set_models = list_disk_sets(
        db,
        session_state.user.id if session_state.user is not None else None,
    )
    disk_sets = [_disk_set_card_view(disk_set) for disk_set in disk_set_models]
    owned_disk_sets = [disk_set for disk_set in disk_sets if disk_set.is_owned]
    public_disk_sets = [disk_set for disk_set in disk_sets if not disk_set.is_owned]
    return {
        **_base_context(
            request,
            current_user=session_state.user,
            alert=alert,
            page_title="Наборы дисков",
            active_path="/disk-sets",
        ),
        "disk_sets": disk_sets,
        "owned_disk_sets": owned_disk_sets,
        "public_disk_sets": public_disk_sets,
        "form": form,
        "field_errors": field_errors or {},
        "own_empty_message": (
            "Создайте первый личный набор."
            if session_state.user is not None
            else "Войдите, чтобы создать личный набор."
        ),
    }


@router.get("/disk-sets", name="web_disk_sets")
def disk_sets_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    action: str | None = Query(default=None),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    alert = (
        _disk_set_alert(action) if action in {"created", "updated", "deleted"} else None
    )
    return _apply_session_state(
        _render(
            request,
            "disk_sets/list.html",
            _disk_sets_context(
                request,
                db,
                session_state=session_state,
                alert=alert,
            ),
        ),
        session_state,
        request,
    )


@router.get("/disk-sets/new", name="web_disk_sets_new")
def disk_set_new_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    if session_state.user is None:
        return _apply_session_state(
            RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER),
            session_state,
            request,
        )
    return _apply_session_state(
        _render(
            request,
            "disk_sets/form.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    page_title="Наборы дисков",
                    active_path="/disk-sets",
                ),
                "form": _disk_set_form_view(),
                "field_errors": {},
                "mode": "create",
            },
        ),
        session_state,
        request,
    )


@router.post("/disk-sets", name="web_disk_sets_create")
def disk_set_create(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    name: str = Form(""),
    slug: str = Form(""),
    alphabet: str = Form(""),
    disks: str = Form(""),
    csrf_token: str = Form(""),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    if session_state.user is None:
        return _apply_session_state(
            RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER),
            session_state,
            request,
        )
    if not validate_web_csrf_token(request, csrf_token):
        response = _render(
            request,
            "disk_sets/form.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    alert=_error_alert("Неверный CSRF-токен."),
                    page_title="Наборы дисков",
                    active_path="/disk-sets",
                ),
                "form": _disk_set_form_view(),
                "field_errors": {"form": "Неверный CSRF-токен."},
                "mode": "create",
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
        set_web_csrf_cookie(response, resolve_web_csrf_token(request))
        return response
    try:
        form = parse_disk_set_form(
            name=name,
            slug=slug,
            alphabet=alphabet,
            disks=disks,
            csrf_token=csrf_token,
        )
        create_user_disk_set(db, session_state.user, form)
    except WebFormError as error:
        return _apply_session_state(
            _render(
                request,
                "disk_sets/form.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert(error.message),
                        page_title="Наборы дисков",
                        active_path="/disk-sets",
                    ),
                    "form": DiskSetFormView(
                        name=name,
                        slug=slug,
                        alphabet=alphabet or "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                        disks=disks,
                    ),
                    "field_errors": error.field_errors,
                    "mode": "create",
                },
            ),
            session_state,
            request,
        )
    except DiskSetSlugAlreadyExistsError:
        return _apply_session_state(
            _render(
                request,
                "disk_sets/form.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert("Такой слаг уже занят."),
                        page_title="Наборы дисков",
                        active_path="/disk-sets",
                    ),
                    "form": DiskSetFormView(
                        name=name,
                        slug=slug,
                        alphabet=alphabet or "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                        disks=disks,
                    ),
                    "field_errors": {"slug": "Такой слаг уже занят."},
                    "mode": "create",
                },
            ),
            session_state,
            request,
        )
    except DiskSetValidationError as error:
        return _apply_session_state(
            _render(
                request,
                "disk_sets/form.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert("Проверьте данные набора дисков."),
                        page_title="Наборы дисков",
                        active_path="/disk-sets",
                    ),
                    "form": DiskSetFormView(
                        name=name,
                        slug=slug,
                        alphabet=alphabet or "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                        disks=disks,
                    ),
                    "field_errors": {
                        "disks": _disk_set_validation_message(error.message),
                    },
                    "mode": "create",
                },
            ),
            session_state,
            request,
        )

    response = RedirectResponse(
        url="/disk-sets?action=created",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    set_web_csrf_cookie(response, resolve_web_csrf_token(request))
    return response


@router.get("/disk-sets/{disk_set_id}/edit", name="web_disk_sets_edit")
def disk_set_edit_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    disk_set_id: int,
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    if session_state.user is None:
        return _apply_session_state(
            RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER),
            session_state,
            request,
        )
    disk_set = get_any_disk_set_by_id(db, disk_set_id)
    if disk_set is None or disk_set.owner_id != session_state.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _apply_session_state(
        _render(
            request,
            "disk_sets/form.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    page_title="Наборы дисков",
                    active_path="/disk-sets",
                ),
                "form": _disk_set_form_view(disk_set),
                "field_errors": {},
                "mode": "edit",
                "disk_set_id": disk_set.id,
            },
        ),
        session_state,
        request,
    )


@router.post("/disk-sets/{disk_set_id}/edit", name="web_disk_sets_update")
def disk_set_update(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    disk_set_id: int,
    name: str = Form(""),
    slug: str = Form(""),
    alphabet: str = Form(""),
    disks: str = Form(""),
    csrf_token: str = Form(""),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    if session_state.user is None:
        return _apply_session_state(
            RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER),
            session_state,
            request,
        )
    disk_set = get_any_disk_set_by_id(db, disk_set_id)
    if disk_set is None or disk_set.owner_id != session_state.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not validate_web_csrf_token(request, csrf_token):
        response = _render(
            request,
            "disk_sets/form.html",
            {
                **_base_context(
                    request,
                    current_user=session_state.user,
                    alert=_error_alert("Неверный CSRF-токен."),
                    page_title="Наборы дисков",
                    active_path="/disk-sets",
                ),
                "form": DiskSetFormView(
                    name=name,
                    slug=slug,
                    alphabet=alphabet or disk_set.alphabet,
                    disks=disks,
                ),
                "field_errors": {"form": "Неверный CSRF-токен."},
                "mode": "edit",
                "disk_set_id": disk_set.id,
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
        set_web_csrf_cookie(response, resolve_web_csrf_token(request))
        return response
    try:
        form = parse_disk_set_form(
            name=name,
            slug=slug,
            alphabet=alphabet,
            disks=disks,
            csrf_token=csrf_token,
        )
        update_user_disk_set(db, disk_set_id, session_state.user, form)
    except WebFormError as error:
        return _apply_session_state(
            _render(
                request,
                "disk_sets/form.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert(error.message),
                        page_title="Наборы дисков",
                        active_path="/disk-sets",
                    ),
                    "form": DiskSetFormView(
                        name=name,
                        slug=slug,
                        alphabet=alphabet or disk_set.alphabet,
                        disks=disks,
                    ),
                    "field_errors": error.field_errors,
                    "mode": "edit",
                    "disk_set_id": disk_set.id,
                },
            ),
            session_state,
            request,
        )
    except DiskSetSlugAlreadyExistsError:
        return _apply_session_state(
            _render(
                request,
                "disk_sets/form.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert("Такой слаг уже занят."),
                        page_title="Наборы дисков",
                        active_path="/disk-sets",
                    ),
                    "form": DiskSetFormView(
                        name=name,
                        slug=slug,
                        alphabet=alphabet or disk_set.alphabet,
                        disks=disks,
                    ),
                    "field_errors": {"slug": "Такой слаг уже занят."},
                    "mode": "edit",
                    "disk_set_id": disk_set.id,
                },
            ),
            session_state,
            request,
        )
    except DiskSetNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    except DiskSetValidationError as error:
        return _apply_session_state(
            _render(
                request,
                "disk_sets/form.html",
                {
                    **_base_context(
                        request,
                        current_user=session_state.user,
                        alert=_error_alert("Проверьте данные набора дисков."),
                        page_title="Наборы дисков",
                        active_path="/disk-sets",
                    ),
                    "form": DiskSetFormView(
                        name=name,
                        slug=slug,
                        alphabet=alphabet or disk_set.alphabet,
                        disks=disks,
                    ),
                    "field_errors": {
                        "disks": _disk_set_validation_message(error.message),
                    },
                    "mode": "edit",
                    "disk_set_id": disk_set.id,
                },
            ),
            session_state,
            request,
        )

    response = RedirectResponse(
        url="/disk-sets?action=updated",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    set_web_csrf_cookie(response, resolve_web_csrf_token(request))
    return response


@router.post("/disk-sets/{disk_set_id}/delete", name="web_disk_sets_delete")
def disk_set_delete(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    disk_set_id: int,
    csrf_token: str = Form(""),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    if session_state.user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    disk_set = get_any_disk_set_by_id(db, disk_set_id)
    if disk_set is None or disk_set.owner_id != session_state.user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if not validate_web_csrf_token(request, csrf_token):
        response = _render(
            request,
            "disk_sets/list.html",
            {
                **_disk_sets_context(
                    request,
                    db,
                    session_state=session_state,
                    alert=_error_alert("Неверный CSRF-токен."),
                ),
                "field_errors": {"form": "Неверный CSRF-токен."},
            },
            status_code=status.HTTP_403_FORBIDDEN,
        )
        set_web_csrf_cookie(response, resolve_web_csrf_token(request))
        return response
    try:
        delete_user_disk_set(db, disk_set_id, session_state.user)
    except DiskSetNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    except DiskSetValidationError:
        response = _render(
            request,
            "disk_sets/list.html",
            {
                **_disk_sets_context(
                    request,
                    db,
                    session_state=session_state,
                    alert=_error_alert("Не удалось удалить набор дисков."),
                ),
            },
        )
        return _apply_session_state(response, session_state, request)

    response = RedirectResponse(
        url="/disk-sets?action=deleted",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    set_web_csrf_cookie(response, resolve_web_csrf_token(request))
    return response


@router.get("/cipher", name="web_cipher")
def cipher_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    disk_set_id: int | None = Query(default=None, gt=0),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    context = _cipher_context(
        request,
        db,
        session_state=session_state,
        selected_disk_set_id=disk_set_id,
    )
    return _apply_session_state(
        _render(request, "cipher/form.html", context),
        session_state,
        request,
    )


@router.post("/cipher", name="web_cipher_submit")
def cipher_submit(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    mode: str = Form("encrypt"),
    text: str = Form(""),
    disk_set_id: str = Form("0"),
    disk_order: str = Form(""),
    offset: str = Form("0"),
    explanation_open: str = Form("0"),
    csrf_token: str = Form(""),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    is_hx_request = request.headers.get("HX-Request") == "true"
    explanation_open_flag = _is_truthy_form_flag(explanation_open)
    if not validate_web_csrf_token(request, csrf_token):
        try:
            selected_disk_set_id = int(disk_set_id)
        except ValueError:
            selected_disk_set_id = None
        if is_hx_request:
            response = _render(
                request,
                "partials/cipher_workspace.html",
                {
                    **_cipher_context(
                        request,
                        db,
                        session_state=session_state,
                        form=_cipher_form_view(
                            mode=mode or "encrypt",
                            text=text,
                            disk_set_id=selected_disk_set_id or 0,
                            disk_order=disk_order,
                            offset=int(offset)
                            if str(offset).lstrip("-").isdigit()
                            else 0,
                            explanation_open=explanation_open_flag,
                        ),
                        selected_disk_set_id=selected_disk_set_id,
                        alert=_error_alert("Неверный CSRF-токен."),
                        field_errors={"form": "Неверный CSRF-токен."},
                    ),
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )
        else:
            response = _render(
                request,
                "cipher/form.html",
                {
                    **_cipher_context(
                        request,
                        db,
                        session_state=session_state,
                        form=_cipher_form_view(
                            mode=mode or "encrypt",
                            text=text,
                            disk_set_id=selected_disk_set_id or 0,
                            disk_order=disk_order,
                            offset=int(offset)
                            if str(offset).lstrip("-").isdigit()
                            else 0,
                            explanation_open=explanation_open_flag,
                        ),
                        selected_disk_set_id=selected_disk_set_id,
                        alert=_error_alert("Неверный CSRF-токен."),
                        field_errors={"form": "Неверный CSRF-токен."},
                    ),
                },
                status_code=status.HTTP_403_FORBIDDEN,
            )
        set_web_csrf_cookie(response, resolve_web_csrf_token(request))
        return response
    try:
        form = parse_cipher_form(
            mode=mode,
            text=text,
            disk_set_id=disk_set_id,
            disk_order=disk_order,
            offset=offset,
        )
    except WebFormError as error:
        try:
            selected_disk_set_id = int(disk_set_id)
        except ValueError:
            selected_disk_set_id = None
        if is_hx_request:
            response = _render(
                request,
                "partials/cipher_workspace.html",
                {
                    **_cipher_context(
                        request,
                        db,
                        session_state=session_state,
                        form=_cipher_form_view(
                            mode=mode or "encrypt",
                            text=text,
                            disk_set_id=selected_disk_set_id or 0,
                            disk_order=disk_order,
                            offset=int(offset)
                            if str(offset).lstrip("-").isdigit()
                            else 0,
                            explanation_open=explanation_open_flag,
                        ),
                        selected_disk_set_id=selected_disk_set_id,
                        alert=_error_alert(error.message),
                        field_errors=error.field_errors,
                    ),
                },
            )
            return _apply_session_state(response, session_state, request)
        response = _render(
            request,
            "cipher/form.html",
            {
                **_cipher_context(
                    request,
                    db,
                    session_state=session_state,
                    form=_cipher_form_view(
                        mode=mode or "encrypt",
                        text=text,
                        disk_set_id=selected_disk_set_id or 0,
                        disk_order=disk_order,
                        offset=int(offset) if str(offset).lstrip("-").isdigit() else 0,
                        explanation_open=explanation_open_flag,
                    ),
                    selected_disk_set_id=selected_disk_set_id,
                    alert=_error_alert(error.message),
                    field_errors=error.field_errors,
                ),
            },
        )
        return _apply_session_state(response, session_state, request)

    transform = (
        encrypt_with_disk_set_id if form.mode == "encrypt" else decrypt_with_disk_set_id
    )

    user_id = session_state.user.id if session_state.user is not None else None
    disk_set_model = _selected_disk_set_model(
        list_disk_sets(db, user_id),
        form.disk_set_id,
    )

    try:
        result = transform(
            text=form.text,
            disk_set_id=form.disk_set_id,
            key=CipherKey(
                disk_order=tuple(form.disk_order),
                offset=form.offset,
            ),
            db=db,
            user_id=user_id,
        )
    except CipherDomainError as error:
        if is_hx_request:
            response = _render(
                request,
                "partials/cipher_workspace.html",
                {
                    **_cipher_context(
                        request,
                        db,
                        session_state=session_state,
                        form=_cipher_form_view(
                            mode=form.mode,
                            text=form.text,
                            disk_set_id=form.disk_set_id,
                            disk_order=disk_order,
                            offset=form.offset,
                            explanation_open=explanation_open_flag,
                        ),
                        selected_disk_set_id=form.disk_set_id,
                        alert=_error_alert(_cipher_error_message(error)),
                    ),
                },
            )
            return _apply_session_state(response, session_state, request)
        response = _render(
            request,
            "cipher/form.html",
            {
                **_cipher_context(
                    request,
                    db,
                    session_state=session_state,
                    form=_cipher_form_view(
                        mode=form.mode,
                        text=form.text,
                        disk_set_id=form.disk_set_id,
                        disk_order=disk_order,
                        offset=form.offset,
                        explanation_open=explanation_open_flag,
                    ),
                    selected_disk_set_id=form.disk_set_id,
                    alert=_error_alert(_cipher_error_message(error)),
                ),
            },
        )
        return _apply_session_state(response, session_state, request)

    if result is None or disk_set_model is None:
        if is_hx_request:
            response = _render(
                request,
                "partials/cipher_workspace.html",
                {
                    **_cipher_context(
                        request,
                        db,
                        session_state=session_state,
                        form=_cipher_form_view(
                            mode=form.mode,
                            text=form.text,
                            disk_set_id=form.disk_set_id,
                            disk_order=disk_order,
                            offset=form.offset,
                            explanation_open=explanation_open_flag,
                        ),
                        selected_disk_set_id=form.disk_set_id,
                        alert=_error_alert("Выбранный набор дисков недоступен."),
                    ),
                },
            )
            return _apply_session_state(response, session_state, request)
        response = _render(
            request,
            "cipher/form.html",
            {
                **_cipher_context(
                    request,
                    db,
                    session_state=session_state,
                    form=_cipher_form_view(
                        mode=form.mode,
                        text=form.text,
                        disk_set_id=form.disk_set_id,
                        disk_order=disk_order,
                        offset=form.offset,
                        explanation_open=explanation_open_flag,
                    ),
                    selected_disk_set_id=form.disk_set_id,
                    alert=_error_alert("Выбранный набор дисков недоступен."),
                ),
            },
        )
        return _apply_session_state(response, session_state, request)

    result_view = _cipher_result_view(
        result,
        mode=form.mode,
        disk_set=disk_set_model,
        disk_order=form.disk_order,
        offset=form.offset,
    )
    if is_hx_request:
        response = _render(
            request,
            "partials/cipher_workspace.html",
            {
                **_cipher_context(
                    request,
                    db,
                    session_state=session_state,
                    form=_cipher_form_view(
                        mode=form.mode,
                        text=form.text,
                        disk_set_id=form.disk_set_id,
                        disk_order=disk_order,
                        offset=form.offset,
                        explanation_open=explanation_open_flag,
                    ),
                    selected_disk_set_id=form.disk_set_id,
                    result=result_view,
                ),
            },
        )
    else:
        response = _render(
            request,
            "cipher/form.html",
            {
                **_cipher_context(
                    request,
                    db,
                    session_state=session_state,
                    form=_cipher_form_view(
                        mode=form.mode,
                        text=form.text,
                        disk_set_id=form.disk_set_id,
                        disk_order=disk_order,
                        offset=form.offset,
                        explanation_open=explanation_open_flag,
                    ),
                    selected_disk_set_id=form.disk_set_id,
                    result=result_view,
                ),
            },
        )

    return _apply_session_state(response, session_state, request)
