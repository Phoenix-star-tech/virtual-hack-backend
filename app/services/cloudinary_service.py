import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("cloudinary")

CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

_cloudinary_available = False
_upload_image_fn = None
_delete_image_fn = None

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    try:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api

        cloudinary.config(
            cloud_name=CLOUDINARY_CLOUD_NAME,
            api_key=CLOUDINARY_API_KEY,
            api_secret=CLOUDINARY_API_SECRET,
            secure=True,
        )

        def _upload(file, folder="virtual_hack_2k26", public_id=None, **kwargs):
            return cloudinary.uploader.upload(file, folder=folder, public_id=public_id, **kwargs)

        def _delete(public_id, **kwargs):
            return cloudinary.uploader.destroy(public_id, **kwargs)

        _upload_image_fn = _upload
        _delete_image_fn = _delete
        _cloudinary_available = True
        logger.info("Cloudinary configured successfully")
    except ImportError:
        logger.warning("cloudinary package not installed")
    except Exception as e:
        logger.warning("Failed to configure Cloudinary: %s", e)
else:
    logger.warning("Cloudinary not configured: missing environment variables")


def upload_image(file, folder="virtual_hack_2k26", public_id=None):
    if not _cloudinary_available:
        raise RuntimeError("Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET in .env")
    return _upload_image_fn(file, folder=folder, public_id=public_id)


def delete_image(public_id):
    if not _cloudinary_available:
        raise RuntimeError("Cloudinary is not configured")
    return _delete_image_fn(public_id)


def is_available():
    return _cloudinary_available
