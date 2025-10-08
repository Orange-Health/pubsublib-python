import base64
import gzip
from io import BytesIO


def gzip_compress(data: bytes, level: int = 9) -> bytes:
    """compresses the given data"""
    buf = BytesIO()
    with gzip.GzipFile(fileobj=buf, mode='wb', compresslevel=level) as gz:
        gz.write(data)
    return buf.getvalue()


def gzip_decompress(data: bytes) -> bytes:
    """decompresses gzip-compressed bytes"""
    with gzip.GzipFile(fileobj=BytesIO(data), mode='rb') as gz:
        return gz.read()


def b64_encode(data: bytes) -> str:
    """returns base64-encoded string of data"""
    return base64.b64encode(data).decode('ascii')


def b64_decode(s: str) -> bytes:
    """decodes base64 string to bytes"""
    return base64.b64decode(s)


def gzip_and_b64(data: bytes, level: int = 9) -> str:
    """gzip + base64. returns b64 string"""
    to_encode = gzip_compress(data, level=level)
    return b64_encode(to_encode)


def b64_decode_and_gunzip_if(b64s: str, compressed: bool) -> bytes:
    """base64 decode + gunzip if compressed"""
    decoded = b64_decode(b64s)
    if compressed:
        return gzip_decompress(decoded)
    return decoded
