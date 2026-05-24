from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, status
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
from app.services.disk_sets import list_disk_sets
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
    parse_login_form,
    parse_register_form,
)
from app.web.view_models import (
    AlertView,
    CipherFormView,
    CipherResultView,
    CipherTraceStepView,
    DiskSetOptionView,
    NavLinkView,
)

router = APIRouter(include_in_schema=False)
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _nav_links(active_path: str) -> list[NavLinkView]:
    return [
        NavLinkView(label="Home", href="/", active=active_path == "/"),
        NavLinkView(
            label="Cipher",
            href="/cipher",
            active=active_path.startswith("/cipher"),
        ),
        NavLinkView(label="Login", href="/login", active=active_path == "/login"),
        NavLinkView(
            label="Register",
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
            selected=disk_set.id == selected_disk_set_id,
        )
        for disk_set in disk_sets
    ]


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


def _cipher_result_view(result) -> CipherResultView:
    return CipherResultView(
        text=result.text,
        normalized_text=result.normalized_text,
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
        "EmptyTextError": "Enter text that contains at least one A-Z letter.",
        "InvalidAlphabetError": "The selected disk set has an invalid alphabet.",
        "InvalidDiskPermutationError": "One of the disk sequences is invalid.",
        "DuplicateDiskNumberError": "The disk order contains duplicate IDs.",
        "MissingDiskNumberError": "The selected disk set is missing a requested disk.",
        "InvalidConfigurationError": "Check the disk order and offset.",
    }
    return message_map.get(error.__class__.__name__, "Unable to process cipher input.")


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
        form = CipherFormView(
            mode="encrypt",
            disk_set_id=selected_disk_set.id if selected_disk_set else 0,
            disk_order=_disk_order_string(selected_disk_set_model),
        )

    return {
        **_base_context(
            request,
            current_user=session_state.user,
            alert=alert,
            page_title="Cipher",
            active_path="/cipher",
        ),
        "disk_sets": disk_sets,
        "form": form,
        "field_errors": field_errors or {},
        "result": result,
    }


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
                    page_title="Jefferson Cipher Service",
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
                    page_title="Register",
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
                    alert=_error_alert("Invalid CSRF token."),
                    page_title="Register",
                    active_path="/register",
                ),
                "form": {"email": email},
                "field_errors": {"form": "Invalid CSRF token."},
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
                        page_title="Register",
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
                        alert=_error_alert("Email is already registered."),
                        page_title="Register",
                        active_path="/register",
                    ),
                    "form": {"email": email},
                    "field_errors": {"email": "Email is already registered."},
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
                    page_title="Login",
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
                    alert=_error_alert("Invalid CSRF token."),
                    page_title="Login",
                    active_path="/login",
                ),
                "form": {"email": email},
                "field_errors": {"form": "Invalid CSRF token."},
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
                        page_title="Login",
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
                        alert=_error_alert("Invalid email or password."),
                        page_title="Login",
                        active_path="/login",
                    ),
                    "form": {"email": email},
                    "field_errors": {
                        "email": "Invalid email or password.",
                        "password": "Invalid email or password.",
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
                    alert=_error_alert("Invalid CSRF token."),
                    page_title="Jefferson Cipher Service",
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


@router.get("/cipher", name="web_cipher")
def cipher_page(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    context = _cipher_context(request, db, session_state=session_state)
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
    include_trace: bool = Form(False),
    csrf_token: str = Form(""),
) -> HTMLResponse:
    session_state = resolve_web_session(request, db)
    is_hx_request = request.headers.get("HX-Request") == "true"
    if not validate_web_csrf_token(request, csrf_token):
        try:
            selected_disk_set_id = int(disk_set_id)
        except ValueError:
            selected_disk_set_id = None
        if is_hx_request:
            response = _render(
                request,
                "partials/result_card.html",
                {
                    "request": request,
                    "result": None,
                    "alert": _error_alert("Invalid CSRF token."),
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
                        form=CipherFormView(
                            mode=mode or "encrypt",
                            text=text,
                            disk_set_id=selected_disk_set_id or 0,
                            disk_order=disk_order,
                            offset=int(offset)
                            if str(offset).lstrip("-").isdigit()
                            else 0,
                            include_trace=include_trace,
                        ),
                        selected_disk_set_id=selected_disk_set_id,
                        alert=_error_alert("Invalid CSRF token."),
                        field_errors={"form": "Invalid CSRF token."},
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
            include_trace=include_trace,
        )
    except WebFormError as error:
        try:
            selected_disk_set_id = int(disk_set_id)
        except ValueError:
            selected_disk_set_id = None
        if is_hx_request:
            response = _render(
                request,
                "partials/result_card.html",
                {
                    "request": request,
                    "result": None,
                    "alert": _error_alert(error.message),
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
                    form=CipherFormView(
                        mode=mode or "encrypt",
                        text=text,
                        disk_set_id=selected_disk_set_id or 0,
                        disk_order=disk_order,
                        offset=int(offset) if str(offset).lstrip("-").isdigit() else 0,
                        include_trace=include_trace,
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
    try:
        result = transform(
            text=form.text,
            disk_set_id=form.disk_set_id,
            key=CipherKey(
                disk_order=tuple(form.disk_order),
                offset=form.offset,
            ),
            db=db,
            user_id=session_state.user.id if session_state.user is not None else None,
            include_trace=form.include_trace,
        )
    except CipherDomainError as error:
        if is_hx_request:
            response = _render(
                request,
                "partials/result_card.html",
                {
                    "request": request,
                    "result": None,
                    "alert": _error_alert(_cipher_error_message(error)),
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
                    form=CipherFormView(
                        mode=form.mode,
                        text=form.text,
                        disk_set_id=form.disk_set_id,
                        disk_order=disk_order,
                        offset=form.offset,
                        include_trace=form.include_trace,
                    ),
                    selected_disk_set_id=form.disk_set_id,
                    alert=_error_alert(_cipher_error_message(error)),
                ),
            },
        )
        return _apply_session_state(response, session_state, request)

    if result is None:
        if is_hx_request:
            response = _render(
                request,
                "partials/result_card.html",
                {
                    "request": request,
                    "result": None,
                    "alert": _error_alert("Selected disk set is not available."),
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
                    form=CipherFormView(
                        mode=form.mode,
                        text=form.text,
                        disk_set_id=form.disk_set_id,
                        disk_order=disk_order,
                        offset=form.offset,
                        include_trace=form.include_trace,
                    ),
                    selected_disk_set_id=form.disk_set_id,
                    alert=_error_alert("Selected disk set is not available."),
                ),
            },
        )
        return _apply_session_state(response, session_state, request)

    result_view = _cipher_result_view(result)
    if request.headers.get("HX-Request") == "true":
        response = _render(
            request,
            "partials/result_card.html",
            {
                "request": request,
                "result": result_view,
                "alert": _success_alert("Cipher operation completed."),
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
                    form=CipherFormView(
                        mode=form.mode,
                        text=form.text,
                        disk_set_id=form.disk_set_id,
                        disk_order=disk_order,
                        offset=form.offset,
                        include_trace=form.include_trace,
                    ),
                    selected_disk_set_id=form.disk_set_id,
                    result=result_view,
                    alert=_success_alert("Cipher operation completed."),
                ),
            },
        )

    return _apply_session_state(response, session_state, request)
