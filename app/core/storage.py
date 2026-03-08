import uuid
from io import BytesIO

import boto3
from botocore.config import Config
from PIL import Image

from app.core.config import settings

s3_client = boto3.client(
    "s3",
    endpoint_url=settings.s3_endpoint_url,
    aws_access_key_id=settings.s3_access_key,
    aws_secret_access_key=settings.s3_secret_key,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGE_DIMENSION = 1200
THUMBNAIL_DIMENSION = 300


def _resize_image(image_bytes: bytes, max_dim: int) -> bytes:
    img = Image.open(BytesIO(image_bytes))
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    if img.width > max_dim or img.height > max_dim:
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    output = BytesIO()
    img.save(output, format="JPEG", quality=85, optimize=True)
    output.seek(0)
    return output.read()


def validate_image(content_type: str, size: int) -> str | None:
    if content_type not in ALLOWED_MIME_TYPES:
        return f"Invalid file type: {content_type}. Allowed: JPEG, PNG, WebP"
    if size > MAX_FILE_SIZE:
        return f"File too large: {size} bytes. Maximum: {MAX_FILE_SIZE} bytes"
    return None


def upload_image(image_bytes: bytes, folder: str) -> tuple[str, str]:
    resized = _resize_image(image_bytes, MAX_IMAGE_DIMENSION)
    thumbnail = _resize_image(image_bytes, THUMBNAIL_DIMENSION)

    file_id = uuid.uuid4().hex
    image_key = f"{folder}/{file_id}.jpg"
    thumb_key = f"{folder}/{file_id}_thumb.jpg"

    s3_client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=image_key,
        Body=resized,
        ContentType="image/jpeg",
    )
    s3_client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=thumb_key,
        Body=thumbnail,
        ContentType="image/jpeg",
    )

    image_url = f"{settings.s3_public_url}/{image_key}"
    thumb_url = f"{settings.s3_public_url}/{thumb_key}"
    return image_url, thumb_url


def delete_image(image_url: str) -> None:
    if not image_url.startswith(settings.s3_public_url):
        return
    key = image_url.removeprefix(f"{settings.s3_public_url}/")
    s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=key)
    thumb_key = key.replace(".jpg", "_thumb.jpg")
    s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=thumb_key)
