"""Endpoint xác thực (T-102): API-AUTH-01 `POST /auth/login`, API-AUTH-06 `POST /auth/logout`,
API-AUTH-07 `GET /auth/me`. T-103: API-AUTH-02 `POST /auth/mfa/verify`, API-AUTH-03 `POST /auth/mfa/enroll`, API-AUTH-04
`POST /auth/mfa/enroll/confirm` — nhận session chờ MFA; xác minh/xác nhận xong đặt cookie session mới.
T-104: API-AUTH-05 `POST /auth/reauth`, API-AUTH-09 `POST /auth/password` (`STEP-UP`). T-109: API-ADM-01
`GET /admin/users`, API-ADM-04 `PATCH /admin/users/{id}`, API-ADM-05 `PUT /admin/users/{id}/roles` (`PermissionGuard`).

Router mỏng (ADR-002): kiểm tra đầu vào → gọi `Authenticator` → trả response. `POST /auth/login` là đường dẫn công khai
(API_Specification §1.2): composition root miễn token CSRF cho đường dẫn này, vẫn kiểm `Origin` (T-007).
"""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from aieos.access.api import Actor, PermissionGuard
from aieos.identity.auth import Authenticator, Principal
from aieos.identity.mfa import MfaService
from aieos.identity.stepup import StepUpService
from aieos.identity.users import UserAdmin, UserView
from aieos.platform.api import (
    AUTHENTICATED,
    PAGE_DEFAULT_LIMIT,
    PAGE_MAX_LIMIT,
    PUBLIC,
    SESSION_COOKIE,
    ApiError,
    Secret,
    csrf_token,
    declare,
    decode_cursor,
    encode_cursor,
    etag,
    require_if_match,
)

LOGIN_PATH = "/auth/login"


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    mfa_required: bool
    mfa_enrolled: bool
    csrf_token: str  # session chờ MFA không gọi được `/auth/me` nhưng vẫn cần token CSRF cho API MFA (T-103)


class MfaCodeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=32)


class ReauthBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1, max_length=1024)
    code: str | None = Field(default=None, min_length=6, max_length=32)


class PasswordBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_password: str = Field(min_length=1, max_length=4096)  # độ dài thật kiểm ở service (D-58)


class EnrollResponse(BaseModel):
    secret: str
    otpauth_uri: str


class RecoveryCodesResponse(BaseModel):
    recovery_codes: list[str]


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, secure=True, httponly=True, samesite="lax", path="/")


def build_auth_router(auth: Authenticator, csrf_key: Secret) -> APIRouter:
    router = APIRouter(tags=["auth"])
    full_session = Annotated[Principal, Depends(auth.require_session)]
    any_session = Annotated[Principal, Depends(auth.require_session_allow_pending)]

    @router.post(LOGIN_PATH, response_model=LoginResponse, **declare(PUBLIC))
    def login(body: LoginBody, request: Request, response: Response) -> LoginResponse:
        result = auth.login(
            body.email,
            body.password,
            ip=request.client.host if request.client else None,
            old_token=request.cookies.get(SESSION_COOKIE),
            user_agent=request.headers.get("user-agent"),
        )
        set_session_cookie(response, result.token)
        return LoginResponse(
            mfa_required=result.mfa_required,
            mfa_enrolled=result.mfa_enrolled,
            csrf_token=csrf_token(csrf_key, result.token),
        )

    @router.post("/auth/logout", status_code=204, **declare(AUTHENTICATED))
    def logout(principal: any_session) -> Response:
        auth.logout(principal)
        response = Response(status_code=204)
        response.delete_cookie(SESSION_COOKIE, secure=True, httponly=True, samesite="lax", path="/")
        return response

    @router.get("/auth/me", **declare(AUTHENTICATED))
    def me(request: Request, principal: full_session) -> dict[str, Any]:
        body = auth.me(principal)
        body["csrf_token"] = csrf_token(csrf_key, request.cookies.get(SESSION_COOKIE, ""))
        return body

    return router


def _client(request: Request) -> tuple[str | None, str | None]:
    return (request.client.host if request.client else None), request.headers.get("user-agent")


def build_mfa_router(auth: Authenticator, mfa: MfaService) -> APIRouter:
    router = APIRouter(tags=["auth"])
    any_session = Annotated[Principal, Depends(auth.require_session_allow_pending)]

    @router.post("/auth/mfa/enroll", response_model=EnrollResponse, **declare(AUTHENTICATED))
    def enroll(principal: any_session) -> EnrollResponse:
        result = mfa.enroll(principal)
        return EnrollResponse(secret=result.secret, otpauth_uri=result.otpauth_uri)

    @router.post("/auth/mfa/enroll/confirm", response_model=RecoveryCodesResponse, **declare(AUTHENTICATED))
    def confirm(
        body: MfaCodeBody, request: Request, response: Response, principal: any_session
    ) -> RecoveryCodesResponse:
        ip, user_agent = _client(request)
        result = mfa.confirm(principal, body.code, ip=ip, user_agent=user_agent)
        set_session_cookie(response, result.token)
        return RecoveryCodesResponse(recovery_codes=list(result.recovery_codes))

    @router.post("/auth/mfa/verify", status_code=204, **declare(AUTHENTICATED))
    def verify(body: MfaCodeBody, request: Request, principal: any_session) -> Response:
        ip, user_agent = _client(request)
        result = mfa.verify(principal, body.code, ip=ip, user_agent=user_agent)
        response = Response(status_code=204)
        set_session_cookie(response, result.token)
        return response

    return router


def build_stepup_router(auth: Authenticator, stepup: StepUpService) -> APIRouter:
    router = APIRouter(tags=["auth"])
    full_session = Annotated[Principal, Depends(auth.require_session)]
    step_up = Annotated[Principal, Depends(auth.require_step_up)]

    @router.post("/auth/reauth", status_code=204, **declare(AUTHENTICATED))
    def reauth(body: ReauthBody, request: Request, principal: full_session) -> Response:
        ip, _ = _client(request)
        stepup.reauth(principal, body.password, body.code, ip=ip)
        return Response(status_code=204)

    @router.post("/auth/password", status_code=204, **declare(AUTHENTICATED))
    def change_password(body: PasswordBody, principal: step_up) -> Response:
        stepup.change_password(principal, body.new_password)
        return Response(status_code=204)

    return router


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    status: str
    roles: list[str]
    mfa_enabled: bool
    created_at: datetime
    version: int


class UserPage(BaseModel):
    items: list[UserOut]
    next_cursor: str | None


class StatusBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ACTIVE", "LOCKED", "DISABLED"]
    reason: str | None = Field(default=None, max_length=1000)


class RolesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: list[str] = Field(max_length=10)
    reason: str = Field(min_length=1, max_length=1000)


def _user_response(view: UserView, response: Response) -> UserOut:
    response.headers["ETag"] = etag(view.version)
    return UserOut(**view.__dict__)


def _user_after(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    if cursor is None:
        return None
    created_at, item_id = decode_cursor(cursor, 2)
    try:
        return datetime.fromisoformat(created_at), uuid.UUID(item_id)
    except ValueError:
        raise ApiError("VALIDATION_ERROR", errors=[{"field": "cursor", "message": "cursor không hợp lệ"}]) from None


def build_user_admin_router(admin: UserAdmin, guard: PermissionGuard) -> APIRouter:
    router = APIRouter(tags=["admin"])
    actor_dep = Annotated[Actor, Depends(guard.actor)]
    if_match = Annotated[str | None, Header(alias="If-Match")]

    @router.get("/admin/users", response_model=UserPage, **guard.route("user.manage"))
    def list_users(
        limit: Annotated[int, Query(ge=1, le=PAGE_MAX_LIMIT)] = PAGE_DEFAULT_LIMIT,
        cursor: Annotated[str | None, Query(max_length=256)] = None,
    ) -> UserPage:
        items = admin.list(limit=limit + 1, after=_user_after(cursor))
        next_cursor = None
        if len(items) > limit:
            items = items[:limit]
            next_cursor = encode_cursor((items[-1].created_at.isoformat(), str(items[-1].id)))
        return UserPage(items=[UserOut(**i.__dict__) for i in items], next_cursor=next_cursor)

    @router.patch("/admin/users/{user_id}", response_model=UserOut, **guard.route("user.manage", step_up=True))
    def set_status(
        user_id: uuid.UUID, body: StatusBody, actor: actor_dep, response: Response, version: if_match = None
    ) -> UserOut:
        expected = require_if_match(version)
        view = admin.set_status(
            actor=actor.user_id, user_id=user_id, status=body.status, reason=body.reason, expected_version=expected
        )
        return _user_response(view, response)

    @router.put("/admin/users/{user_id}/roles", response_model=UserOut, **guard.route("role.assign", step_up=True))
    def set_roles(
        user_id: uuid.UUID, body: RolesBody, actor: actor_dep, response: Response, version: if_match = None
    ) -> UserOut:
        expected = require_if_match(version)
        view = admin.set_roles(
            actor=actor.user_id, user_id=user_id, roles=set(body.roles), reason=body.reason, expected_version=expected
        )
        return _user_response(view, response)

    return router
