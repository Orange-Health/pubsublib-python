import base64
import gzip
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def gzip_compress(data: bytes, level: int = 9) -> bytes:
    """compresses the given data"""
    in_size = len(data) if data is not None else 0
    logger.info("gzip_compress: start input_bytes=%d level=%d", in_size, level)
    buf = BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=level) as gz:
        gz.write(data)
    out = buf.getvalue()
    out_size = len(out)
    ratio_pct = (1.0 - (out_size / in_size)) * 100.0 if in_size else 0.0
    logger.info(
        "gzip_compress: done input_bytes=%d output_bytes=%d ratio=%.2f%% level=%d",
        in_size,
        out_size,
        ratio_pct,
        level,
    )
    return out


def gzip_decompress(data: bytes) -> bytes:
    """decompresses gzip-compressed bytes"""
    in_size = len(data) if data is not None else 0
    logger.info("gzip_decompress: start input_bytes=%d", in_size)
    try:
        with gzip.GzipFile(fileobj=BytesIO(data), mode='rb') as gz:
            out = gz.read()
    except Exception:
        logger.exception("gzip_decompress: failed input_bytes=%d", in_size)
        raise
    out_size = len(out)
    logger.info(
        "gzip_decompress: done input_bytes=%d output_bytes=%d", in_size, out_size)
    return out


def b64_encode(data: bytes) -> str:
    """returns base64-encoded string of data"""
    return base64.b64encode(data).decode('ascii')


def b64_decode(s: str) -> bytes:
    """decodes base64 string to bytes"""
    return base64.b64decode(s)


def gzip_and_b64(data: bytes, level: int = 9) -> str:
    """gzip + base64. returns b64 string"""
    in_size = len(data) if data is not None else 0
    logger.info("gzip_and_b64: start input_bytes=%d level=%d", in_size, level)
    to_encode = gzip_compress(data, level=level)
    gz_size = len(to_encode)
    b64s = b64_encode(to_encode)
    logger.info(
        "gzip_and_b64: done input_bytes=%d gz_bytes=%d b64_len=%d level=%d",
        in_size,
        gz_size,
        len(b64s),
        level,
    )
    return b64s


def b64_decode_and_gunzip_if(b64s: str, compressed: bool) -> bytes:
    """base64 decode + gunzip if compressed"""
    logger.info(
        "b64_decode_and_gunzip_if: start compressed=%s b64_len=%d",
        compressed,
        len(b64s) if b64s is not None else 0,
    )
    decoded = b64_decode(b64s)
    if compressed:
        out = gzip_decompress(decoded)
        logger.info(
            "b64_decode_and_gunzip_if: done compressed=%s decoded_bytes=%d",
            compressed,
            len(out),
        )
        return out
    logger.info(
        "b64_decode_and_gunzip_if: done compressed=%s decoded_bytes=%d",
        compressed,
        len(decoded),
    )
    return decoded
