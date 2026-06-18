import pytest
from fastapi import HTTPException

from app.routes.resume import MAX_RESUME_BYTES, _extract_resume_text


class FakeUpload:
    def __init__(self, content: bytes, filename: str, content_type: str):
        self._content = content
        self.filename = filename
        self.content_type = content_type

    async def read(self) -> bytes:
        return self._content


async def test_extract_text_from_plain_text_file():
    upload = FakeUpload(b"Python and SQL expert.", "resume.txt", "text/plain")
    text = await _extract_resume_text(upload)
    assert text == "Python and SQL expert."


async def test_rejects_empty_file():
    upload = FakeUpload(b"", "resume.txt", "text/plain")
    with pytest.raises(HTTPException) as exc_info:
        await _extract_resume_text(upload)
    assert exc_info.value.status_code == 400


async def test_rejects_oversized_file():
    oversized = b"a" * (MAX_RESUME_BYTES + 1)
    upload = FakeUpload(oversized, "resume.txt", "text/plain")
    with pytest.raises(HTTPException) as exc_info:
        await _extract_resume_text(upload)
    assert exc_info.value.status_code == 413


async def test_rejects_unsupported_file_type():
    upload = FakeUpload(b"some bytes", "resume.xyz", "application/octet-stream")
    with pytest.raises(HTTPException) as exc_info:
        await _extract_resume_text(upload)
    assert exc_info.value.status_code == 400


async def test_rejects_malformed_pdf():
    upload = FakeUpload(b"not a real pdf", "resume.pdf", "application/pdf")
    with pytest.raises(HTTPException) as exc_info:
        await _extract_resume_text(upload)
    assert exc_info.value.status_code == 400
