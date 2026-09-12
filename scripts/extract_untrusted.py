#!/usr/bin/env python3
"""Extract text from documents so scan_untrusted.py can read it.

    source document  ->  extract_untrusted.py  ->  scan_untrusted.py  ->  you

`scan_untrusted.py` reads decoded UTF-8 text and nothing else, and says so
rather than pretending a PDF it could not parse was clean. This script is the
missing front end. It is deliberately a separate file so the scanner keeps its
zero-dependency guarantee.

DEPENDENCIES

    DOCX, PPTX, XLSX, ODT, EPUB   standard library only (zipfile + ElementTree)
    PDF                           standard library best-effort;
                                  optional: pdfminer.six or pypdf, used if present

No dependency is required. Formats that cannot be read are reported as failures,
never as empty-and-therefore-clean.

WHY OFFICE FILES DESERVE THE ATTENTION

They are ZIP archives of XML, and text can hide in parts a reader never sees:
speaker notes, tracked-change history, comments, headers and footers, and runs
marked hidden or coloured white. This extractor pulls all of them and labels
each part, so a payload in slide notes arrives at the scanner with its location
attached.

USAGE

    python extract_untrusted.py report.docx                 # text to stdout
    python extract_untrusted.py deck.pptx --scan            # extract and scan
    python extract_untrusted.py ./inbox/ --scan             # whole directory
    python extract_untrusted.py paper.pdf --json            # structured output

    python extract_untrusted.py report.docx | \
        python scan_untrusted.py --stdin                    # explicit pipeline

EXIT CODES

    0  everything requested was extracted
    1  extracted, and --scan found something
    2  at least one file could not be extracted, or a target was missing

Coverage failures always reach exit 2. A document that could not be read must
never look like a document that was read and found clean.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import zipfile
import zlib
from dataclasses import dataclass, asdict, field
from pathlib import Path
from xml.etree import ElementTree

SCANNER = Path(__file__).resolve().parent / "scan_untrusted.py"
MAX_BYTES = 100 * 1024 * 1024

# Office XML namespaces, by the local names we need rather than full URIs --
# the URIs differ between formats and versions, so match on the tag suffix.
TEXT_TAGS = {"t", "delText", "instrText"}


@dataclass
class Extraction:
    source: str
    ok: bool
    method: str
    text: str = ""
    parts: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str = ""

    def summary(self) -> str:
        if not self.ok:
            return f"FAILED  {self.source}\n        {self.error}"
        head = (f"OK      {self.source}  ({self.method}, "
                f"{len(self.text)} chars, {len(self.parts)} part(s))")
        for w in self.warnings:
            head += f"\n        ! {w}"
        return head


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_text(blob: bytes) -> str:
    """All text nodes from an Office XML part, in document order."""
    try:
        root = ElementTree.fromstring(blob)
    except ElementTree.ParseError:
        return ""
    out: list[str] = []
    for el in root.iter():
        if _localname(el.tag) in TEXT_TAGS and el.text:
            out.append(el.text)
        elif _localname(el.tag) in {"p", "br", "tab", "tr"}:
            out.append("\n")
    return re.sub(r"\n{3,}", "\n\n", "".join(out))


def _hidden_run_warning(blob: bytes) -> str | None:
    """Runs marked hidden or coloured white. The classic document-borne trick."""
    text = blob.decode("utf-8", errors="replace")
    hits = []
    if re.search(r"<w:vanish\b", text):
        hits.append("hidden (w:vanish) runs")
    if re.search(r'<w:color[^>]*w:val="(?:FFFFFF|ffffff)"', text):
        hits.append("white-coloured text")
    if re.search(r'<a:srgbClr[^>]*val="FFFFFF"', text):
        hits.append("white fill")
    if re.search(r'w:sz w:val="([0-4]?\d)"', text):
        hits.append("text under 2.5pt")
    return ", ".join(hits) if hits else None


# Parts worth reading, per format. Order matters only for readability.
OFFICE_PARTS = {
    ".docx": (r"word/(document|header\d*|footer\d*|footnotes|endnotes|comments)\.xml",),
    ".pptx": (r"ppt/(slides|notesSlides|comments)/[^/]+\.xml",),
    ".xlsx": (r"xl/(sharedStrings|comments\d*)\.xml", r"xl/worksheets/[^/]+\.xml"),
    ".odt":  (r"content\.xml", r"styles\.xml"),
    ".epub": (r".*\.(x?html|htm)$",),
}


def extract_zip_xml(path: Path, suffix: str) -> Extraction:
    patterns = OFFICE_PARTS[suffix]
    result = Extraction(str(path), True, f"zipfile+xml ({suffix})")
    try:
        with zipfile.ZipFile(path) as zf:
            names = [n for n in zf.namelist()
                     if any(re.fullmatch(p, n) or re.match(p, n) for p in patterns)]
            if not names:
                result.warnings.append(
                    "archive contained none of the expected parts; it may not be "
                    "the format its extension claims")
            chunks = []
            for name in sorted(names):
                try:
                    blob = zf.read(name)
                except (KeyError, zlib.error, RuntimeError) as exc:
                    result.warnings.append(f"{name}: unreadable ({exc})")
                    continue
                hidden = _hidden_run_warning(blob)
                if hidden:
                    result.warnings.append(f"{name}: contains {hidden}")
                text = _xml_text(blob)
                if text.strip():
                    result.parts.append(name)
                    chunks.append(f"\n=== [{path.name}] {name} ===\n{text}")
            result.text = "".join(chunks)
    except (zipfile.BadZipFile, OSError) as exc:
        return Extraction(str(path), False, "zipfile+xml", error=str(exc))
    return result


# --------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------

PDF_TEXT_OP = re.compile(rb"\((?:\\.|[^\\()])*\)\s*Tj|\[(?:[^\][]|\\.)*\]\s*TJ")
PDF_STRING = re.compile(rb"\((?:\\.|[^\\()])*\)")


def _pdf_strings(chunk: bytes) -> str:
    out = []
    for op in PDF_TEXT_OP.finditer(chunk):
        for s in PDF_STRING.finditer(op.group()):
            raw = s.group()[1:-1]
            raw = re.sub(rb"\\([nrtbf()\\])", lambda m: {
                b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"", b"f": b"",
                b"(": b"(", b")": b")", b"\\": b"\\"}[m.group(1)], raw)
            out.append(raw.decode("utf-8", errors="replace"))
    return "".join(out)


def extract_pdf_stdlib(path: Path) -> Extraction:
    """Best-effort: inflate FlateDecode streams and pull text-showing operators.

    Handles simple and moderately common PDFs. It does not do font/CMap
    decoding, so text in subsetted or CID-keyed fonts may come out as noise, and
    it cannot see text rendered as vector outlines or images. Those limits are
    reported, not hidden.
    """
    result = Extraction(str(path), True, "stdlib (best-effort)")
    try:
        data = path.read_bytes()
    except OSError as exc:
        return Extraction(str(path), False, "stdlib", error=str(exc))

    if not data.startswith(b"%PDF"):
        result.warnings.append("no %PDF header; may not be a PDF")

    if b"/Encrypt" in data:
        return Extraction(str(path), False, "stdlib",
                          error="PDF is encrypted -- not extracted")

    chunks: list[str] = []
    streams = re.findall(rb"stream\r?\n(.*?)\r?\nendstream", data, re.DOTALL)
    inflated = 0
    for raw in streams:
        body = raw
        try:
            body = zlib.decompress(raw)
            inflated += 1
        except zlib.error:
            pass                      # uncompressed, or a filter we do not do
        text = _pdf_strings(body)
        if text.strip():
            chunks.append(text)

    chunks.append(_pdf_strings(data))     # text outside any stream
    result.text = "\n".join(c for c in chunks if c.strip())
    result.parts = [f"{len(streams)} stream(s), {inflated} inflated"]

    if not result.text.strip():
        result.ok = False
        result.error = (
            "no text recovered. The PDF is probably scanned images, uses "
            "compression filters beyond FlateDecode, or stores text in fonts "
            "this extractor cannot map. Install pdfminer.six for better "
            "coverage, or treat this file as NOT SCANNED.")
    else:
        result.warnings.append(
            "stdlib PDF extraction is approximate: no font/CMap decoding, no "
            "OCR, no vector or image text. Absence of a finding is not evidence "
            "of absence")
    return result


def extract_pdf(path: Path) -> Extraction:
    """Prefer a real PDF library when one happens to be installed."""
    try:
        from pdfminer.high_level import extract_text     # type: ignore
        text = extract_text(str(path))
        if text and text.strip():
            return Extraction(str(path), True, "pdfminer.six", text=text,
                              parts=["full document"])
    except ImportError:
        pass
    except Exception as exc:                              # malformed PDF
        return Extraction(str(path), False, "pdfminer.six", error=str(exc))

    try:
        import pypdf                                      # type: ignore
        reader = pypdf.PdfReader(str(path))
        text = "\n".join((p.extract_text() or "") for p in reader.pages)
        if text.strip():
            return Extraction(str(path), True, "pypdf", text=text,
                              parts=[f"{len(reader.pages)} page(s)"])
    except ImportError:
        pass
    except Exception as exc:
        return Extraction(str(path), False, "pypdf", error=str(exc))

    return extract_pdf_stdlib(path)


def extract_ipynb(path: Path) -> Extraction:
    """Notebooks are JSON: source cells plus, importantly, stored outputs."""
    try:
        nb = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError) as exc:
        return Extraction(str(path), False, "json", error=str(exc))
    chunks, parts = [], []
    for i, cell in enumerate(nb.get("cells", [])):
        src = "".join(cell.get("source", []))
        if src.strip():
            chunks.append(f"\n=== cell {i} ({cell.get('cell_type')}) ===\n{src}")
            parts.append(f"cell {i}")
        for j, out in enumerate(cell.get("outputs", [])):
            text = "".join(out.get("text", []))
            if text.strip():
                chunks.append(f"\n=== cell {i} output {j} ===\n{text}")
    return Extraction(str(path), True, "json (ipynb)", "".join(chunks), parts)


EXTRACTORS = {
    ".docx": lambda p: extract_zip_xml(p, ".docx"),
    ".pptx": lambda p: extract_zip_xml(p, ".pptx"),
    ".xlsx": lambda p: extract_zip_xml(p, ".xlsx"),
    ".odt":  lambda p: extract_zip_xml(p, ".odt"),
    ".epub": lambda p: extract_zip_xml(p, ".epub"),
    ".pdf":  extract_pdf,
    ".ipynb": extract_ipynb,
}

# Honest about what has no extractor at all.
NO_EXTRACTOR = {
    ".doc": "legacy binary Word; convert to .docx first",
    ".ppt": "legacy binary PowerPoint; convert to .pptx first",
    ".xls": "legacy binary Excel; convert to .xlsx first",
    ".rtf": "RTF; convert to .docx first",
    ".png": "image; needs OCR", ".jpg": "image; needs OCR",
    ".jpeg": "image; needs OCR", ".gif": "image; needs OCR",
    ".webp": "image; needs OCR", ".tiff": "image; needs OCR",
    ".bmp": "image; needs OCR", ".heic": "image; needs OCR",
    ".mp3": "audio; needs transcription", ".wav": "audio; needs transcription",
    ".mp4": "video; needs transcription", ".mov": "video; needs transcription",
}


def extract(path: Path) -> Extraction:
    suffix = path.suffix.lower()
    if suffix in NO_EXTRACTOR:
        return Extraction(str(path), False, "none",
                          error=f"no extractor: {NO_EXTRACTOR[suffix]}")
    extractor = EXTRACTORS.get(suffix)
    if extractor is None:
        # Plain text already: hand it through unchanged.
        try:
            return Extraction(str(path), True, "plain text",
                              path.read_text(encoding="utf-8", errors="replace"),
                              ["whole file"])
        except OSError as exc:
            return Extraction(str(path), False, "plain text", error=str(exc))
    try:
        if path.stat().st_size > MAX_BYTES:
            return Extraction(str(path), False, "none",
                              error=f"larger than {MAX_BYTES // 1048576}MB")
        return extractor(path)
    except Exception as exc:                       # never let one bad file stop a batch
        return Extraction(str(path), False, "error", error=f"{type(exc).__name__}: {exc}")


def collect(targets: list[str]) -> tuple[list[Path], list[str]]:
    files, missing = [], []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            files.extend(sorted(f for f in p.rglob("*")
                                if f.is_file() and not f.is_symlink()))
        elif p.is_file():
            files.append(p)
        else:
            missing.append(t)
    return files, missing


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Extract text from documents for scan_untrusted.py.",
        epilog="Formats that cannot be read are reported, never treated as clean.")
    ap.add_argument("targets", nargs="+", help="files or directories")
    ap.add_argument("--scan", action="store_true",
                    help="pipe the extracted text through scan_untrusted.py")
    ap.add_argument("--json", action="store_true", help="structured output")
    ap.add_argument("--quiet", action="store_true",
                    help="text only, no per-file status on stderr")
    args = ap.parse_args()

    files, missing = collect(args.targets)
    results = [extract(f) for f in files]
    failed = [r for r in results if not r.ok]

    if args.json:
        print(json.dumps({
            "extracted": sum(1 for r in results if r.ok),
            "failed": len(failed),
            "missing": missing,
            "coverage_complete": not failed and not missing,
            "results": [asdict(r) for r in results],
        }, indent=2))
    else:
        if not args.quiet:
            for t in missing:
                print(f"MISSING {t}", file=sys.stderr)
            for r in results:
                print(r.summary(), file=sys.stderr)
            if failed or missing:
                print(f"\n{len(failed) + len(missing)} file(s) NOT extracted. "
                      f"Do not treat them as clean.", file=sys.stderr)
                print("", file=sys.stderr)

        combined = "\n".join(r.text for r in results if r.ok and r.text.strip())
        if args.scan:
            proc = subprocess.run(
                [sys.executable, str(SCANNER), "--stdin"],
                input=combined, text=True, encoding="utf-8")
            if failed or missing:
                return 2
            return proc.returncode
        print(combined)

    return 2 if (failed or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
