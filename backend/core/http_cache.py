"""
HTTP Caching and Partial Content (Range) Streaming Engine.
Provides RFC 7231 / RFC 7233 compliant conditional headers (ETag, If-None-Match, If-Modified-Since),
smooth partial content 206 streaming for instant video/audio seeking, and client disconnect resilience.
Pure Python standard library with FastAPI / Starlette integration.
"""

import email.utils
import mimetypes
import os
from pathlib import Path
from typing import Optional, Union

from fastapi import Request, Response
from fastapi.responses import FileResponse, StreamingResponse


def compute_file_etag(stat: os.stat_result) -> str:
    """Computes a lightweight, highly accurate HTTP ETag based on mtime nanoseconds and file size."""
    return f'"{stat.st_mtime_ns:x}-{stat.st_size:x}"'


def format_http_date(timestamp: float) -> str:
    """Formats a UNIX timestamp into RFC 7231 GMT HTTP date string."""
    return email.utils.formatdate(timestamp, usegmt=True)


def parse_http_date(date_str: str) -> Optional[float]:
    """Parses an RFC 7231 HTTP date string into a UNIX timestamp."""
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        return dt.timestamp()
    except Exception:
        return None


def is_client_fresh(
    request: Request,
    etag: str,
    last_modified_timestamp: Optional[float] = None,
) -> bool:
    """
    Checks if client cache is fresh according to HTTP conditional request headers.
    Evaluates If-None-Match (highest precedence) followed by If-Modified-Since.
    """
    if_none_match = request.headers.get("if-none-match")
    if if_none_match:
        tags = [t.strip() for t in if_none_match.split(",")]
        # Match wildcard or weak/strong etag match
        for tag in tags:
            clean_tag = tag.lstrip("W/")
            clean_current = etag.lstrip("W/")
            if tag == "*" or tag == etag or clean_tag == clean_current:
                return True
        return False

    if last_modified_timestamp is not None:
        if_modified_since = request.headers.get("if-modified-since")
        if if_modified_since:
            client_time = parse_http_date(if_modified_since)
            if client_time is not None:
                # HTTP dates have 1-second resolution; truncate comparison
                return int(last_modified_timestamp) <= int(client_time)

    return False


def send_cached_range_file(
    file_path: Union[str, Path],
    request: Request,
    media_type: Optional[str] = None,
    max_age: int = 86400,
    chunk_size: int = 512 * 1024,
) -> Response:
    """
    Streams a local file with full HTTP caching and Range (206) support:
    - Returns 304 Not Modified if client cache is fresh (zero bytes transferred).
    - Returns 206 Partial Content when Range header is present (instant video/audio seeking).
    - Returns 416 Range Not Satisfiable when requested byte range is invalid.
    - Emits ETag, Last-Modified, Accept-Ranges: bytes, and Cache-Control headers.
    - Gracefully handles client disconnects (ConnectionResetError, BrokenPipeError).
    """
    path_obj = Path(file_path).resolve()
    if not path_obj.is_file():
        return Response(status_code=404, content="File not found")

    try:
        stat = os.stat(path_obj)
    except OSError:
        return Response(status_code=404, content="File inaccessible")

    file_size = stat.st_size
    etag = compute_file_etag(stat)
    last_mod_str = format_http_date(stat.st_mtime)
    cache_control = f"public, max-age={max_age}, must-revalidate"

    # 1. Evaluate If-None-Match and If-Modified-Since
    if is_client_fresh(request, etag, stat.st_mtime):
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Last-Modified": last_mod_str,
                "Cache-Control": cache_control,
                "Accept-Ranges": "bytes",
            },
        )

    resolved_media_type = media_type or mimetypes.guess_type(str(path_obj))[0] or "application/octet-stream"
    range_header = request.headers.get("range")

    # 2. Non-range request: return standard 200 FileResponse with caching headers
    if not range_header or not range_header.startswith("bytes="):
        return FileResponse(
            path=str(path_obj),
            media_type=resolved_media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "ETag": etag,
                "Last-Modified": last_mod_str,
                "Cache-Control": cache_control,
            },
        )

    # 3. If-Range validation (RFC 7233): if validator doesn't match, return full file 200
    if_range = request.headers.get("if-range")
    if if_range:
        if if_range != etag and if_range != etag.strip('"'):
            # If-Range can also be an HTTP-date
            client_dt = parse_http_date(if_range)
            if client_dt is None or int(client_dt) != int(stat.st_mtime):
                return FileResponse(
                    path=str(path_obj),
                    media_type=resolved_media_type,
                    headers={
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(file_size),
                        "ETag": etag,
                        "Last-Modified": last_mod_str,
                        "Cache-Control": cache_control,
                    },
                )

    # 4. Parse Range header
    raw_range = range_header.strip()[6:].strip()
    if "-" not in raw_range:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    parts = raw_range.split("-", 1)
    try:
        if not parts[0]:
            # Suffix byte range: bytes=-500 (last 500 bytes)
            suffix_len = int(parts[1])
            if suffix_len <= 0:
                start = 0
            else:
                start = max(0, file_size - suffix_len)
            end = file_size - 1
        else:
            start = int(parts[0])
            end = int(parts[1]) if parts[1] else file_size - 1
    except ValueError:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    # 5. Validate byte boundaries
    if start >= file_size or start > end or start < 0:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    end = min(file_size - 1, end)
    content_length = (end - start) + 1
    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": resolved_media_type,
        "ETag": etag,
        "Last-Modified": last_mod_str,
        "Cache-Control": cache_control,
    }

    # Fast path for small byte ranges (HTML5 video probes, metadata atoms <= 64KB)
    if content_length <= 65536:
        try:
            with open(path_obj, "rb") as f:
                f.seek(start)
                raw_bytes = f.read(content_length)
            return Response(
                content=raw_bytes,
                status_code=206,
                headers=headers,
            )
        except Exception:
            pass

    # 6. Generator for streaming larger chunk slices
    def chunk_generator():
        try:
            with open(path_obj, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    read_size = min(remaining, chunk_size)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        except (ConnectionResetError, BrokenPipeError):
            # Client scrubbed or aborted connection mid-stream; close cleanly
            return

    return StreamingResponse(
        chunk_generator(),
        status_code=206,
        headers=headers,
    )

