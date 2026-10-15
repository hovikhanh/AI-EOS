"""Endpoint xác thực (T-102): API-AUTH-01 `POST /auth/login`, API-AUTH-06 `POST /auth/logout`,
API-AUTH-07 `GET /auth/me`.

Router mỏng (ADR-002): kiểm tra đầu vào → gọi `Authenticator` → trả response. `POST /auth/login` là đường dẫn công khai
(API_Specification §1.2): composition root miễn token CSRF cho đường dẫn này, vẫn kiểm `Origin` (T-007).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from aieos.identity.auth import Authenticator, Principal
from aieos.platform.api import SESSION_COOKIE, Secret, csrf_token

LOGIN_PATH = "/auth/login"


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    mfa_required: bool


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(SESSION_COOKIE, token, secure=True, httponly=True, samesite="lax", path="/")


def build_auth_router(auth: Authenticator, csrf_key: Secret) -> APIRouter:
    router = APIRouter(tags=["auth"])
    full_session = Annotated[Principal, Depends(auth.require_session)]
    any_session = Annotated[Principal, Depends(auth.require_session_allow_pending)]

    @router.post(LOGIN_PATH, response_model=LoginResponse)
    def login(body: LoginBody, request: Request, response: Response) -> LoginResponse:
        result = auth.login(
            body.email,
            body.password,
            ip=request.client.host if request.client else None,
            old_token=request.cookies.get(SESSION_COOKIE),
            user_agent=request.headers.get("user-agent"),
        )
        set_session_cookie(response, result.token)
        return LoginResponse(mfa_required=result.mfa_required)

    @router.post("/auth/logout", status_code=204)
    def logout(principal: any_session) -> Response:
        auth.logout(principal)
        response = Response(status_code=204)
        response.delete_cookie(SESSION_COOKIE, secure=True, httponly=True, samesite="lax", path="/")
        return response

    @router.get("/auth/me")
    def me(request: Request, principal: full_session) -> dict[str, Any]:
        body = auth.me(principal)
        body["csrf_token"] = csrf_token(csrf_key, request.cookies.get(SESSION_COOKIE, ""))
        return body

    return router
