from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, Tuple

try:
    from botocore.config import Config  # type: ignore
    from botocore.exceptions import ClientError  # type: ignore
except Exception:  # pragma: no cover - botocore optional until S3 enabled
    Config = None  # type: ignore
    ClientError = None  # type: ignore


class StorageService:
    """Abstract storage service used in production for media objects.

    Backends: local (dev only), s3, azure, gcs. Only 'local' is guaranteed without extra deps.
    """

    def generate_upload_url(self, key: str, content_type: Optional[str] = None, expires_s: int = 900) -> Tuple[str, dict]:
        raise NotImplementedError

    def confirm_object(self, key: str) -> dict:
        """Return metadata for object (exists/size/etc). Backend-specific implementation."""
        raise NotImplementedError

    def generate_download_url(self, key: str, expires_s: int = 900) -> Optional[str]:
        raise NotImplementedError

    def download_to_temp(self, key: str) -> Path:
        raise NotImplementedError

    def get_public_url(self, key: str) -> Optional[str]:
        return None


class LocalStorageService(StorageService):
    """Local dev storage uses the RAW_ROOT on disk. No presign support."""

    def __init__(self, raw_root: Path):
        self.raw_root = Path(raw_root)

    def generate_upload_url(self, key: str, content_type: Optional[str] = None, expires_s: int = 900):
        raise RuntimeError("Presigned upload not supported for local storage; use direct POST /api/assets")

    def confirm_object(self, key: str) -> dict:
        # For local we assume key is a stored_path relative to raw_root
        p = self.raw_root / key
        if not p.exists():
            return {"exists": False}
        try:
            st = p.stat()
            return {"exists": True, "size_bytes": st.st_size}
        except Exception:
            return {"exists": True}

    def generate_download_url(self, key: str, expires_s: int = 900) -> Optional[str]:
        # Served via FastAPI static mount at /assets
        key = str(key).lstrip('/')
        return f"/assets/{key}"

    def download_to_temp(self, key: str) -> Path:
        src = self.raw_root / key
        if not src.exists():
            raise FileNotFoundError(str(src))
        import shutil, tempfile
        tmp = Path(tempfile.gettempdir()) / f"bl_tmp_{os.getpid()}_{src.name}"
        shutil.copy2(src, tmp)
        return tmp


def get_storage(raw_root: Path) -> StorageService:
    backend = os.environ.get("STORAGE_BACKEND", "local").lower().strip()
    if backend in ("", "local"):
        return LocalStorageService(raw_root)
    if backend == "s3":
        # Lazy import boto3 only if configured
        try:
            import boto3  # type: ignore
        except Exception as e:
            raise RuntimeError(f"boto3 required for S3 backend: {e}")

        bucket = os.environ.get("STORAGE_BUCKET")
        if not bucket:
            raise RuntimeError("STORAGE_BUCKET must be set when STORAGE_BACKEND=s3")

        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        prefix = os.environ.get("STORAGE_PREFIX", "").strip()
        if prefix:
            prefix = prefix.lstrip("/")
            if not prefix.endswith("/"):
                prefix = f"{prefix}/"

        endpoint_url = os.environ.get("AWS_ENDPOINT_URL") or os.environ.get("STORAGE_ENDPOINT_URL")
        force_path_style = os.environ.get("AWS_S3_FORCE_PATH_STYLE", "")
        public_base_url = os.environ.get("STORAGE_PUBLIC_BASE_URL")

        session_kwargs = {"region_name": region}
        profile = os.environ.get("AWS_PROFILE")
        if profile:
            session_kwargs["profile_name"] = profile

        session = boto3.session.Session(**session_kwargs)

        client_kwargs = {"region_name": region}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if Config and force_path_style.lower() in {"1", "true", "yes", "on"}:
            client_kwargs["config"] = Config(s3={"addressing_style": "path"})  # type: ignore[arg-type]

        s3 = session.client("s3", **client_kwargs)

        class S3Storage(StorageService):
            def generate_upload_url(self, key: str, content_type: Optional[str] = None, expires_s: int = 900):
                full_key = f"{prefix}{key}" if prefix else key
                params = {
                    'Bucket': bucket,
                    'Key': full_key,
                }
                if content_type:
                    params['ContentType'] = content_type
                url = s3.generate_presigned_url(
                    ClientMethod='put_object',
                    Params=params,
                    ExpiresIn=int(expires_s),
                    HttpMethod='PUT',
                )
                headers = {'Content-Type': content_type} if content_type else {}
                return url, headers

            def confirm_object(self, key: str) -> dict:
                full_key = f"{prefix}{key}" if prefix else key
                try:
                    head = s3.head_object(Bucket=bucket, Key=full_key)
                    return {"exists": True, "size_bytes": head.get('ContentLength')}
                except Exception as exc:
                    if ClientError and isinstance(exc, ClientError):
                        code = exc.response.get("Error", {}).get("Code")
                        if code in {"404", "NoSuchKey"}:
                            return {"exists": False}
                    return {"exists": False}

            def generate_download_url(self, key: str, expires_s: int = 900) -> Optional[str]:
                full_key = f"{prefix}{key}" if prefix else key
                return s3.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={'Bucket': bucket, 'Key': full_key},
                    ExpiresIn=int(expires_s),
                )

            def download_to_temp(self, key: str) -> Path:
                import tempfile
                full_key = f"{prefix}{key}" if prefix else key
                tmp = Path(tempfile.gettempdir()) / f"bl_tmp_{os.getpid()}_{Path(key).name}"
                s3.download_file(bucket, full_key, str(tmp))
                return tmp

            def get_public_url(self, key: str) -> Optional[str]:
                if public_base_url:
                    base = public_base_url.rstrip('/')
                    full_key = f"{prefix}{key}" if prefix else key
                    return f"{base}/{full_key}"
                return None

        return S3Storage()
    if backend in ("azure", "gcs"):
        raise RuntimeError("Azure/GCS backends not yet implemented; set STORAGE_BACKEND=local or s3")
    raise RuntimeError(f"Unknown STORAGE_BACKEND: {backend}")
