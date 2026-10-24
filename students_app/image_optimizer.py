"""
Automatic image compression for uploads.

Every image field listed in IMAGE_RULES is resized and compressed when a model
is saved with a newly uploaded file. Nothing else in the app has to change.
"""
import io
import logging
import os

from django.apps import apps
from django.core.files.base import ContentFile
from django.db.models.signals import pre_save
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

# model -> field -> rule
# max = (max width, max height) in pixels. Pictures are only ever shrunk, never enlarged.
IMAGE_RULES = {
    'students_app.SchoolCoverPhoto': {
        'cover_photo': {'max': (1920, 1080), 'format': 'WEBP', 'quality': 80},
    },
    'students_app.CarouselEvent': {
        'image': {'max': (1600, 1000), 'format': 'WEBP', 'quality': 80},
    },
    'students_app.NewsArticle': {
        'featured_image': {'max': (1200, 800), 'format': 'WEBP', 'quality': 80},
    },
    'students_app.LeadershipProfile': {
        'photo': {'max': (800, 800), 'format': 'WEBP', 'quality': 82},
    },
    # Logo and signatures stay PNG: transparent backgrounds, and the PDF reports use them
    'students_app.SchoolProfile': {
        'logo': {'max': (600, 600), 'format': 'PNG'},
        'headteacher_signature': {'max': (600, 300), 'format': 'PNG'},
    },
    'users.CustomUser': {
        'signature': {'max': (600, 300), 'format': 'PNG'},
    },
}


def _optimize(upload, rule):
    """Return (bytes, extension) for the compressed picture, or None to keep the original."""
    max_w, max_h = rule['max']
    fmt = rule['format']
    quality = rule.get('quality', 80)

    original_size = getattr(upload, 'size', None)
    upload.seek(0)
    img = Image.open(upload)
    source_format = img.format

    if getattr(img, 'is_animated', False):
        return None  # leave animated pictures alone

    img = ImageOps.exif_transpose(img)  # apply the rotation the phone camera recorded

    resized = img.width > max_w or img.height > max_h
    if resized:
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)

    has_alpha = img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info)
    img = img.convert('RGBA' if has_alpha else 'RGB')

    buffer = io.BytesIO()
    if fmt == 'PNG':
        img.save(buffer, 'PNG', optimize=True)
        extension = '.png'
    else:
        img.save(buffer, 'WEBP', quality=quality, method=6)
        extension = '.webp'

    data = buffer.getvalue()
    if not resized and source_format == fmt and original_size and len(data) >= original_size:
        return None  # already as small as it can get

    return data, extension


def optimize_field_file(field_file, rule):
    try:
        result = _optimize(field_file.file, rule)
    except Exception:
        logger.exception("Image compression failed for %s; keeping the original", field_file.name)
        return
    if result is None:
        return

    data, extension = result
    base_name = os.path.splitext(os.path.basename(field_file.name))[0]
    field_file.file = ContentFile(data)
    field_file.name = base_name + extension


def _handler_for(rules):
    def handler(sender, instance, raw=False, **kwargs):
        if raw:
            return
        for field_name, rule in rules.items():
            field_file = getattr(instance, field_name, None)
            # only touch files that are being uploaded right now
            if field_file and not getattr(field_file, '_committed', True):
                optimize_field_file(field_file, rule)
    return handler


def connect():
    for label, rules in IMAGE_RULES.items():
        try:
            model = apps.get_model(label)
        except LookupError:
            logger.warning("Image rules: model %s not found, skipped", label)
            continue
        pre_save.connect(
            _handler_for(rules), sender=model, weak=False,
            dispatch_uid=f"optimize-images-{label}",
        )