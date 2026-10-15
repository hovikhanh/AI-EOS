"""Endpoint xác thực (T-102): API-AUTH-01 `POST /auth/login`, API-AUTH-06 `POST /auth/logout`,
API-AUTH-07 `GET /auth/me`. T-103: API-AUTH-02 `POST /auth/mfa/verify`, API-AUTH-03 `POST /auth/mfa/enroll`, API-AUTH-04
`POST /auth/mfa/enroll/confirm` — nhận session chờ MFA; xác minh/xác nhận xong đặt cookie session mới.

Router mỏng (ADR-002): kiểm tra đầu vào → gọi `Authenticator` → trả response. `POST /auth/login` là đường dẫn công khai
(API_Specification §1.2): composition root miễn token CSRF cho đường dẫn này, vẫn kiểm `Origin` (T-007).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from aieos.identity.auth import Authenticator, Principal
from aieos.identity.mfa import MfaService
from aieos.platform.api import AUTHENTICATED, PUBLIC, SESSION_COOKIE, Secret, csrf_token, declare

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
