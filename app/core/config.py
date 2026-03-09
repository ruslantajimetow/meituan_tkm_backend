import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: str
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # S3 / MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "delivery-images"
    s3_public_url: str = "http://localhost:9000/delivery-images"

    # SMS / OTP
    sms_provider: str = "mock"
    unimtx_access_key_id: str = os.getenv("UNIMTX_ACCESS_KEY_ID", "")
    unimtx_secret_key_id: str = os.getenv("UNIMTX_SECRET_KEY_ID", "")

    # App
    app_env: str = "development"
    app_debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]

    # OTP
    otp_expire_minutes: int = 5
    otp_max_attempts: int = 5
    otp_max_sends_per_phone: int = 3
    otp_rate_limit_minutes: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
