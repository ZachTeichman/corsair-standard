from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException

from backend.main import (
    MAX_UPLOAD_BYTES,
    require_cleanup_authorization,
    validate_docx_structure,
    validate_upload_metadata,
)
from tests.docx_factory import baseline_resume_paragraphs, make_docx


class UploadValidationTests(unittest.TestCase):
    def test_upload_rejects_docm(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            validate_upload_metadata("resume.docm", 512)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("DOCM", raised.exception.detail)

    def test_upload_rejects_non_docx(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            validate_upload_metadata("resume.pdf", 512)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn(".docx", raised.exception.detail)

    def test_upload_rejects_files_over_1mb(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            validate_upload_metadata("resume.docx", MAX_UPLOAD_BYTES + 1)
        self.assertEqual(raised.exception.status_code, 413)
        self.assertIn("1MB", raised.exception.detail)

    def test_upload_accepts_docx_under_1mb(self) -> None:
        validate_upload_metadata("resume.docx", MAX_UPLOAD_BYTES)

    def test_docx_structure_rejects_non_zip_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fake.docx"
            path.write_bytes(b"not a zip")
            with self.assertRaises(HTTPException) as raised:
                validate_docx_structure(path)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("real Word .docx", raised.exception.detail)

    def test_docx_structure_rejects_missing_document_xml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "missing-part.docx"
            with ZipFile(path, "w", ZIP_DEFLATED) as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
            with self.assertRaises(HTTPException) as raised:
                validate_docx_structure(path)
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("Required Word document parts", raised.exception.detail)

    def test_docx_structure_accepts_minimal_valid_docx(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = make_docx(Path(temp_dir) / "valid.docx", baseline_resume_paragraphs())
            validate_docx_structure(path)

    def test_cleanup_auth_disabled_without_configured_token(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            require_cleanup_authorization("Bearer anything", configured_token="")
        self.assertEqual(raised.exception.status_code, 404)

    def test_cleanup_auth_rejects_missing_or_wrong_bearer_token(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            require_cleanup_authorization(None, configured_token="secret")
        self.assertEqual(raised.exception.status_code, 401)

        with self.assertRaises(HTTPException) as wrong:
            require_cleanup_authorization("Bearer nope", configured_token="secret")
        self.assertEqual(wrong.exception.status_code, 401)

    def test_cleanup_auth_accepts_matching_bearer_token(self) -> None:
        require_cleanup_authorization("Bearer secret", configured_token="secret")


if __name__ == "__main__":
    unittest.main()
