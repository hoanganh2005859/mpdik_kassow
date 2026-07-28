"""Tests for the Phase 0 PDF reference: existence + SHA256 match."""

from srpdik import constants
from srpdik.paths import repo_root
from utils.file_checksum import sha256_file


def test_pdf_reference_exists_and_hash_matches():
    path = repo_root() / constants.PDF_REFERENCE_RELATIVE_PATH
    assert path.is_file()
    assert sha256_file(path) == constants.PDF_REFERENCE_SHA256


def test_pdf_reference_hash_detects_single_byte_tamper(tmp_path):
    original = repo_root() / constants.PDF_REFERENCE_RELATIVE_PATH
    tampered = tmp_path / "tampered.pdf"
    data = bytearray(original.read_bytes())
    data[0] ^= 0xFF  # flip a single byte
    tampered.write_bytes(bytes(data))
    assert sha256_file(tampered) != constants.PDF_REFERENCE_SHA256
