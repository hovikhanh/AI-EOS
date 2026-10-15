"""Token bí mật và dạng băm lưu CSDL (ADR-006, INV-16, SRS-IAM-06).

- Token session, lời mời, mã khôi phục: ngẫu nhiên ≥ 256 bit (`new_token`), chỉ trả cho người dùng một lần; CSDL lưu
  `token_hash` = SHA-256 (32 byte). Không ghi token vào log/audit — chỉ ghi ID bản ghi.
- Email trong `login_attempt`: lưu `email_hash` (SHA-256 của email đã chuẩn hóa chữ thường, bỏ khoảng trắng hai đầu)
  để giới hạn tốc độ theo tài khoản mà không lưu email rõ.
"""

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32  # 256 bit (ADR-006: ≥ 256 bit)


def new_token() -> str:
    """Token ngẫu nhiên 256 bit, mã hóa base64url (43 ký tự)."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> bytes:
    """SHA-256 của token — giá trị duy nhất được lưu (INV-16)."""
    if not token:
        raise ValueError("token rỗng")
    return hashlib.sha256(token.encode()).digest()


def token_matches(token: str, stored_hash: bytes) -> bool:
    return hmac.compare_digest(hash_token(token), stored_hash)


def hash_email(email: str) -> bytes:
    return hashlib.sha256(email.strip().lower().encode()).digest()
