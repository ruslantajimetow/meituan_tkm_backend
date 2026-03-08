import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OtpProvider(ABC):
    @abstractmethod
    async def send_otp(self, phone: str) -> bool:
        pass

    @abstractmethod
    async def verify_otp(self, phone: str, code: str) -> bool:
        pass


class MockOtpProvider(OtpProvider):
    """Development provider that accepts any 6-digit code."""

    async def send_otp(self, phone: str) -> bool:
        logger.info(f"[MOCK OTP] OTP sent to {phone} (use any 6-digit code to verify)")
        return True

    async def verify_otp(self, phone: str, code: str) -> bool:
        logger.info(f"[MOCK OTP] Verifying code {code} for {phone} — auto-accepting")
        return len(code) == 6 and code.isdigit()


class UnimtxOtpProvider(OtpProvider):
    """UniMTX handles OTP generation, sending, and verification."""

    BASE_URL = "https://api.unimtx.com/"

    async def send_otp(self, phone: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    self.BASE_URL,
                    params={
                        "action": "otp.send",
                        "accessKeyId": settings.unimtx_access_key_id,
                    },
                    json={
                        "to": phone,
                        "digits": 6,
                        "ttl": settings.otp_expire_minutes * 60,
                    },
                )
                data = response.json()
                if data.get("code") == "0":
                    logger.info(f"UniMTX OTP sent to {phone}, id={data.get('data', {}).get('id')}")
                    return True
                logger.error(f"UniMTX send failed: {data}")
                return False
        except httpx.HTTPError as e:
            logger.error(f"UniMTX send error: {e}")
            return False

    async def verify_otp(self, phone: str, code: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.post(
                    self.BASE_URL,
                    params={
                        "action": "otp.verify",
                        "accessKeyId": settings.unimtx_access_key_id,
                    },
                    json={
                        "to": phone,
                        "code": code,
                    },
                )
                data = response.json()
                if data.get("code") == "0":
                    valid = data.get("data", {}).get("valid", False)
                    logger.info(f"UniMTX verify for {phone}: valid={valid}")
                    return valid
                logger.error(f"UniMTX verify failed: {data}")
                return False
        except httpx.HTTPError as e:
            logger.error(f"UniMTX verify error: {e}")
            return False


def get_otp_provider() -> OtpProvider:
    if settings.sms_provider == "unimtx":
        return UnimtxOtpProvider()
    return MockOtpProvider()
