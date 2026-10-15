"""MFA TOTP (T-103; SRS-IAM-05, ADR-006; API-AUTH-02, API-AUTH-03, API-AUTH-04).

- **TOTP (RFC 6238):** HMAC-SHA1, 6 chữ số, bước 30 giây — tham số mặc định mà ứng dụng xác thực phổ biến hỗ trợ;
  chấp nhận lệch ±1 bước (đồng hồ lệch). Mã đã chấp nhận không được chấp nhận lại (RFC 6238 §5.2): lưu bước gần nhất ở
  `user_account.mfa_last_step` (migration 0007).
- **Secret:** 20 byte ngẫu nhiên (160 bit, RFC 4226 §4); lưu mã hóa AES-256-GCM bằng `AIEOS_TOTP_ENCRYPTION_KEY`
  (32 byte, base64), nonce 12 byte ngẫu nhiên, dữ liệu liên kết = id tài khoản (bản mã không dùng được cho tài khoản
  khác). Khóa không lưu trong CSDL (ADR-006).
- **Đăng ký:** chỉ tài khoản bắt buộc MFA (role `ADMIN`; MFA cho role khác là DEFERRED — D-30). `enroll` tạo secret tạm
  (lưu mã hóa, `mfa_enabled = false`); `confirm` kiểm mã → bật MFA, sinh `RECOVERY_CODE_COUNT` mã khôi phục dùng một
  lần (chỉ trả một lần, CSDL lưu SHA-256 — INV-16; mã cũ bị đánh dấu đã dùng), xoay session.
- **Xác minh:** session chờ MFA + mã TOTP hoặc mã khôi phục → xoay session (ID mới, `mfa_verified`; ADR-006). Giới hạn
  thử theo IP và tài khoản (D-57). Sai → `401 INVALID_CREDENTIALS`, audit `SECURITY`. Không ghi mã vào log/audit.
"""

import base64
import binascii
import hashlib
import hmac
import secrets
import struct
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.orm import Session

from aieos.audit.api import Outcome
from aieos.identity.auth import Authenticator, Principal, audit_security, mfa_required
from aieos.identity.tokens import hash_token
from aieos.platform.api import ApiError, Secret, transaction

ISSUER = "AI-EOS"
DIGITS = 6
PERIOD_SECONDS = 30
DRIFT_STEPS = 1
SECRET_BYTES = 20
RECOVERY_CODE_COUNT = 10
_RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # bỏ I, O, 0, 1 để đọc/chép tay không nhầm
_NONCE_BYTES = 12


class MfaKeyError(ValueError):
    """`AIEOS_TOTP_ENCRYPTION_KEY` không phải 32 byte base64; thông điệp chỉ nêu tên biến."""


def parse_totp_key(secret: Secret) -> bytes:
    try:
        key = base64.b64decode(secret.reveal().strip(), altchars=b"-_", validate=True)
    except (binascii.Error, ValueError):
        raise MfaKeyError("AIEOS_TOTP_ENCRYPTION_KEY phải là 32 byte mã hóa base64") from None
    if len(key) != 32:
        raise MfaKeyError("AIEOS_TOTP_ENCRYPTION_KEY phải là 32 byte mã hóa base64")
    return key


# ---------- TOTP (RFC 6238) ----------


def totp(secret: bytes, step: int) -> str:
    digest = hmac.new(secret, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def current_step(now: float) -> int:
    return int(now) // PERIOD_SECONDS


def match_step(secret: bytes, code: str, now: float, last_step: int | None) -> int | None:
    """Bước khớp với `code` trong cửa sổ ±`DRIFT_STEPS` và lớn hơn `last_step` (chống dùng lại); không khớp → None."""
    if len(code) != DIGITS or not code.isdigit():
        return None
    base = current_step(now)
    found = None
    for step in range(base - DRIFT_STEPS, base + DRIFT_STEPS + 1):
        if hmac.compare_digest(totp(secret, step), code) and (last_step is None or step > last_step):
            found = step
    return found


def otpauth_uri(secret: bytes, account: str) -> str:
    encoded = base64.b32encode(secret).decode().rstrip("=")
    label = quote(f"{ISSUER}:{account}", safe="@:")
    return (
        f"otpauth://totp/{label}?secret={encoded}&issuer={quote(ISSUER)}"
        f"&algorithm=SHA1&digits={DIGITS}&period={PERIOD_SECONDS}"
    )


# ---------- Mã hóa secret ----------


def encrypt_secret(key: bytes, user_id: uuid.UUID, secret: bytes) -> bytes:
    nonce = secrets.token_bytes(_NONCE_BYTES)
    return nonce + AESGCM(key).encrypt(nonce, secret, user_id.bytes)


def decrypt_secret(key: bytes, user_id: uuid.UUID, blob: bytes) -> bytes:
    try:
        return AESGCM(key).decrypt(blob[:_NONCE_BYTES], blob[_NONCE_BYTES:], user_id.bytes)
    except InvalidTag:
        raise RuntimeError("Không giải mã được secret MFA (sai khóa hoặc dữ liệu hỏng)") from None


# ---------- Mã khôi phục ----------


def new_recovery_code() -> str:
    chars = "".join(secrets.choice(_RECOVERY_ALPHABET) for _ in range(10))
    return f"{chars[:5]}-{chars[5:]}"


def normalize_recovery_code(code: str) -> str:
    return code.strip().upper().replace("-", "").replace(" ", "")


# ---------- Dịch vụ ----------


@dataclass(frozen=True)
class Enrollment:
    secret: str  # base32, để nhập tay
    otpauth_uri: str


@dataclass(frozen=True)
class MfaResult:
    token: str  # token session mới (xoay session)
    recovery_codes: tuple[str, ...] = ()


class MfaService:
    def __init__(self, auth: Authenticator, key: bytes, clock: Callable[[], float] = time.time) -> None:
        self.auth = auth
        self.key = key
        self.clock = clock

    def _user(self, session: Session, user_id: uuid.UUID) -> Any:
        return session.execute(
            text(
                "SELECT id, email, mfa_enabled, mfa_secret_enc, mfa_last_step FROM identity.user_account "
                "WHERE id = :i FOR UPDATE"
            ),
            {"i": user_id},
        ).one()

    def _limit(self, principal: Principal, ip: str | None) -> None:
        try:
            self.auth.limiter.hit(f"mfa-ip:{ip or '?'}", f"mfa-acct:{principal.user_id}")
        except ApiError:
            with transaction(self.auth.factory) as session:
                audit_security(session, "auth.mfa.verify", Outcome.BLOCKED, principal.user_id, "RATE_LIMITED")
            raise

    def enroll(self, principal: Principal) -> Enrollment:
        """API-AUTH-03: secret tạm; tài khoản không bắt buộc MFA → 403; đã bật MFA → 409 (đặt lại: `recover-admin`)."""
        with transaction(self.auth.factory) as session:
            user = self._user(session, principal.user_id)
            if user.mfa_enabled:
                raise ApiError("INVALID_STATE", "MFA đã được bật")
            if not mfa_required(session, principal.user_id, False):
                raise ApiError("FORBIDDEN", "MFA cho role này chưa thuộc phạm vi (D-30)")
            secret = secrets.token_bytes(SECRET_BYTES)
            session.execute(
                text(
                    "UPDATE identity.user_account SET mfa_secret_enc = :s, mfa_last_step = NULL, updated_at = now() "
                    "WHERE id = :i"
                ),
                {"s": encrypt_secret(self.key, principal.user_id, secret), "i": principal.user_id},
            )
            audit_security(session, "auth.mfa.enroll", Outcome.SUCCESS, principal.user_id)
            email = str(user.email)
        return Enrollment(base64.b32encode(secret).decode().rstrip("="), otpauth_uri(secret, email))

    def confirm(self, principal: Principal, code: str, *, ip: str | None, user_agent: str | None) -> MfaResult:
        """API-AUTH-04: mã đúng → bật MFA, mã khôi phục mới, xoay session."""
        self._limit(principal, ip)
        with transaction(self.auth.factory) as session:
            user = self._user(session, principal.user_id)
            if user.mfa_enabled or user.mfa_secret_enc is None:
                raise ApiError("INVALID_STATE", "Chưa có đăng ký MFA đang chờ xác nhận")
            secret = decrypt_secret(self.key, principal.user_id, user.mfa_secret_enc)
            step = match_step(secret, code.strip(), self.clock(), None)
            if step is not None:
                session.execute(
                    text(
                        "UPDATE identity.user_account SET mfa_enabled = true, must_enroll_mfa = false, "
                        "mfa_last_step = :s, version = version + 1, updated_at = now() WHERE id = :i"
                    ),
                    {"s": step, "i": principal.user_id},
                )
                codes = self._replace_recovery_codes(session, principal.user_id)
                token = self.auth.rotate_session(session, principal, ip=ip, user_agent=user_agent)
                audit_security(session, "auth.mfa.enroll.confirm", Outcome.SUCCESS, principal.user_id)
                return MfaResult(token, codes)
            audit_security(session, "auth.mfa.enroll.confirm", Outcome.DENIED, principal.user_id, "INVALID_CODE")
        raise ApiError("INVALID_CREDENTIALS")

    def verify(self, principal: Principal, code: str, *, ip: str | None, user_agent: str | None) -> MfaResult:
        """API-AUTH-02: session chờ MFA + mã TOTP hoặc mã khôi phục → xoay session."""
        if principal.mfa_verified:
            raise ApiError("INVALID_STATE", "Session đã xác minh MFA")
        self._limit(principal, ip)
        with transaction(self.auth.factory) as session:
            user = self._user(session, principal.user_id)
            if not user.mfa_enabled:
                raise ApiError("INVALID_STATE", "Tài khoản chưa đăng ký MFA")
            method = self.use_code(session, user, code)
            if method is None:
                audit_security(session, "auth.mfa.verify", Outcome.DENIED, principal.user_id, "INVALID_CODE")
            else:
                token = self.auth.rotate_session(session, principal, ip=ip, user_agent=user_agent)
                audit_security(session, "auth.mfa.verify", Outcome.SUCCESS, principal.user_id, method)
                return MfaResult(token)
        raise ApiError("INVALID_CREDENTIALS")

    def use_code(self, session: Session, user: Any, code: str) -> str | None:
        """Kiểm mã của `user` (dòng `_user`, MFA đã bật): TOTP chưa dùng hoặc mã khôi phục chưa dùng → đánh dấu đã dùng,
        trả `TOTP`/`RECOVERY_CODE`; sai → None. Dùng cho xác minh MFA và xác thực lại (T-104)."""
        secret = decrypt_secret(self.key, user.id, user.mfa_secret_enc)
        step = match_step(secret, code.strip(), self.clock(), user.mfa_last_step)
        if step is not None:
            session.execute(
                text("UPDATE identity.user_account SET mfa_last_step = :s WHERE id = :i"), {"s": step, "i": user.id}
            )
            return "TOTP"
        if self._use_recovery_code(session, user.id, code):
            return "RECOVERY_CODE"
        return None

    def user_for_update(self, session: Session, user_id: uuid.UUID) -> Any:
        return self._user(session, user_id)

    @staticmethod
    def _use_recovery_code(session: Session, user_id: uuid.UUID, code: str) -> bool:
        normalized = normalize_recovery_code(code)
        if len(normalized) != 10:
            return False
        used = session.execute(
            text(
                "UPDATE identity.mfa_recovery_code SET used_at = now() "
                "WHERE user_id = :u AND code_hash = :h AND used_at IS NULL RETURNING id"
            ),
            {"u": user_id, "h": hash_token(normalized)},
        ).first()
        return used is not None

    @staticmethod
    def _replace_recovery_codes(session: Session, user_id: uuid.UUID) -> tuple[str, ...]:
        session.execute(
            text("UPDATE identity.mfa_recovery_code SET used_at = now() WHERE user_id = :u AND used_at IS NULL"),
            {"u": user_id},
        )
        codes = tuple(new_recovery_code() for _ in range(RECOVERY_CODE_COUNT))
        for code in codes:
            session.execute(
                text(
                    "INSERT INTO identity.mfa_recovery_code (id, user_id, code_hash) VALUES (gen_random_uuid(), :u, :h)"
                ),
                {"u": user_id, "h": hash_token(normalize_recovery_code(code))},
            )
        return codes
