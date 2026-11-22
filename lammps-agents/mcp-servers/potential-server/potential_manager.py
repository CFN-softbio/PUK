"""Business logic for downloading, creating, and validating interatomic potentials."""

import os
import re
import shutil
import tarfile
import zipfile
import urllib.request
from dataclasses import dataclass, field

from known_sources import (
    ARCHIVE_EXTENSIONS,
    ELEMENT_MAP,
    GITHUB_BASE,
    GITHUB_POTENTIAL_FILES,
    KNOWN_SOURCES,
    POTENTIAL_EXTENSIONS,
    SW_PARAMETERS,
)


@dataclass
class DownloadResult:
    success: bool
    filepath: str | None = None
    filename: str | None = None
    source: str | None = None
    file_size: int = 0
    error: str | None = None
    alternatives: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool
    format: str = "unknown"
    message: str = ""
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _download_file(url: str, dest: str) -> None:
    """Download *url* to *dest* with browser-like headers."""
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def _is_archive(path_or_url: str) -> bool:
    low = path_or_url.lower()
    return any(low.endswith(ext) for ext in ARCHIVE_EXTENSIONS)


# ---------------------------------------------------------------------------
# Archive extraction
# ---------------------------------------------------------------------------

def _extract_archive(archive_path: str, extract_dir: str) -> list[str]:
    """Extract archive and return list of extracted file paths."""
    os.makedirs(extract_dir, exist_ok=True)
    extracted: list[str] = []

    low = archive_path.lower()
    if low.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_dir)
            extracted = zf.namelist()
    elif any(low.endswith(ext) for ext in [".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"]):
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(extract_dir)
            extracted = tf.getnames()
    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")

    # Return only actual files (not directories)
    return [
        os.path.join(extract_dir, name)
        for name in extracted
        if os.path.isfile(os.path.join(extract_dir, name))
    ]


def _score_potential_file(filepath: str, element: str | None) -> int:
    """Score how likely a file is to be a usable potential file."""
    filename = os.path.basename(filepath).lower()
    score = 0

    # Extension match
    for ext, pts in POTENTIAL_EXTENSIONS.items():
        if filename.endswith(ext):
            score += pts
            break

    # Element name in filename
    if element:
        el = element.lower()
        if el in filename:
            score += 5
        if filename.startswith(el):
            score += 3

    # Potential-related keywords in filename
    for kw in ("potential", "eam", "sw", "tersoff", "meam"):
        if kw in filename:
            score += 2

    # Peek at file content
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(1024)
        for kw in ("eV", "Angstrom", "potential", "EAM", "atomic", "lattice"):
            if kw in head:
                score += 1
    except Exception:
        pass

    return score


def _best_potential_from_archive(
    archive_path: str, extract_dir: str, element: str | None
) -> tuple[str, list[str]]:
    """Extract archive, pick best potential file, return (best_path, alternatives)."""
    files = _extract_archive(archive_path, extract_dir)
    if not files:
        raise RuntimeError("Archive contained no files")

    scored = [(f, _score_potential_file(f, element)) for f in files]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Filter to files that scored > 0
    candidates = [(f, s) for f, s in scored if s > 0]
    if not candidates:
        raise RuntimeError(
            f"No potential files found in archive ({len(files)} files extracted)"
        )

    best = candidates[0][0]
    alternatives = [os.path.basename(f) for f, _ in candidates[1:5]]
    return best, alternatives


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_potential(
    element: str,
    potential_type: str = "eam",
    custom_url: str | None = None,
    workspace: str = ".",
) -> DownloadResult:
    """Download a potential file for *element*.

    Tries in order:
    1. custom_url (if provided)
    2. Known sources matching element + potential_type
    3. GitHub pattern-based search
    """
    element = element.capitalize()
    os.makedirs(workspace, exist_ok=True)
    extract_dir = os.path.join(workspace, "_tmp_extract")

    # --- custom URL ---
    if custom_url:
        try:
            result = _download_from_url(custom_url, element, workspace, extract_dir)
            return result
        except Exception as e:
            pass  # fall through to known sources

    # --- known sources ---
    pt = potential_type.lower()
    sources = KNOWN_SOURCES.get(element, [])
    for url, src_type, filename in sources:
        if pt and src_type != pt:
            continue
        try:
            result = _download_from_url(url, element, workspace, extract_dir, filename)
            return result
        except Exception:
            continue

    # Also try sources regardless of type if type-filtered ones all failed
    if pt:
        for url, src_type, filename in sources:
            if src_type == pt:
                continue  # already tried
            try:
                result = _download_from_url(url, element, workspace, extract_dir, filename)
                return result
            except Exception:
                continue

    # --- GitHub pattern search ---
    for ghfile in GITHUB_POTENTIAL_FILES:
        if ghfile.lower().startswith(element.lower()):
            url = GITHUB_BASE + ghfile
            try:
                result = _download_from_url(url, element, workspace, extract_dir, ghfile)
                return result
            except Exception:
                continue

    return DownloadResult(
        success=False,
        error=f"No working source found for {element} ({potential_type}). "
              f"Try providing a custom_url from OpenKIM or NIST.",
    )


def _download_from_url(
    url: str,
    element: str,
    workspace: str,
    extract_dir: str,
    filename: str | None = None,
) -> DownloadResult:
    """Download from a single URL (direct file or archive)."""
    if _is_archive(url):
        # Download archive to temp, extract, pick best file
        archive_name = os.path.basename(url)
        archive_path = os.path.join(workspace, f"_tmp_{archive_name}")
        try:
            _download_file(url, archive_path)
            if os.path.getsize(archive_path) < 100:
                raise RuntimeError("Downloaded archive is empty or too small")

            best, alternatives = _best_potential_from_archive(
                archive_path, extract_dir, element
            )

            # Determine final filename
            final_name = filename or os.path.basename(best)
            final_path = os.path.join(workspace, final_name)
            shutil.copy2(best, final_path)

            return DownloadResult(
                success=True,
                filepath=final_path,
                filename=final_name,
                source=url,
                file_size=os.path.getsize(final_path),
                alternatives=alternatives,
            )
        finally:
            # Cleanup temp files
            if os.path.exists(archive_path):
                os.remove(archive_path)
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, ignore_errors=True)
    else:
        # Direct file download
        if not filename:
            filename = os.path.basename(url)
        dest = os.path.join(workspace, filename)
        _download_file(url, dest)
        fsize = os.path.getsize(dest)
        if fsize < 100:
            os.remove(dest)
            raise RuntimeError(f"Downloaded file too small ({fsize} bytes)")
        return DownloadResult(
            success=True,
            filepath=dest,
            filename=filename,
            source=url,
            file_size=fsize,
        )


def download_from_openkim(
    kim_model_id: str,
    element: str | None = None,
    workspace: str = ".",
) -> DownloadResult:
    """Download a potential from OpenKIM by model ID."""
    url = f"https://openkim.org/download/{kim_model_id}.txz"

    if not element:
        element = _extract_element_from_kim_id(kim_model_id)

    os.makedirs(workspace, exist_ok=True)
    extract_dir = os.path.join(workspace, "_tmp_extract")

    try:
        return _download_from_url(url, element or "Unknown", workspace, extract_dir)
    except Exception as e:
        return DownloadResult(
            success=False,
            error=f"OpenKIM download failed for {kim_model_id}: {e}",
        )


def _extract_element_from_kim_id(kim_id: str) -> str | None:
    """Try to extract element symbol(s) from an OpenKIM model ID."""
    # Pattern: ..._ElementElement__MO_...  e.g. ..._CuAu__MO_...
    m = re.search(r"_([A-Z][a-z]?(?:[A-Z][a-z]?)*)__MO_", kim_id)
    if m:
        return m.group(1)
    return None


# ---------------------------------------------------------------------------
# SW potential generation
# ---------------------------------------------------------------------------

def create_sw_potential(element: str, workspace: str = ".") -> DownloadResult:
    """Generate a Stillinger-Weber potential file from built-in parameters."""
    element = element.capitalize()
    if element not in SW_PARAMETERS:
        available = list(SW_PARAMETERS.keys())
        return DownloadResult(
            success=False,
            error=f"No built-in SW parameters for {element}. Available: {available}",
        )

    p = SW_PARAMETERS[element]
    content = (
        f"# Stillinger-Weber potential for {element}\n"
        f"# {p['ref']}\n"
        f"# Parameters: epsilon={p['epsilon']} eV, sigma={p['sigma']} A\n"
        f"\n"
        f"{element} {element} {element} "
        f"{p['epsilon']} {p['sigma']} {p['a']} {p['lambda_']} "
        f"{p['gamma']} {p['costheta0']} "
        f"{p['A']} {p['B']} {p['p']} {p['q']} {p['tol']}\n"
    )

    os.makedirs(workspace, exist_ok=True)
    filename = f"{element}.sw"
    filepath = os.path.join(workspace, filename)
    with open(filepath, "w") as f:
        f.write(content)

    return DownloadResult(
        success=True,
        filepath=filepath,
        filename=filename,
        source="built-in SW parameters",
        file_size=os.path.getsize(filepath),
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_potential(
    filepath: str, element: str | None = None, workspace: str = "."
) -> ValidationResult:
    """Validate a potential file with format-specific checks."""
    # Resolve relative paths
    if not os.path.isabs(filepath):
        filepath = os.path.join(workspace, filepath)

    if not os.path.exists(filepath):
        return ValidationResult(valid=False, message=f"File not found: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        return ValidationResult(valid=False, message=f"Cannot read file: {e}")

    lines = content.split("\n")

    # --- General checks (all formats) ---

    # Dummy/placeholder detection
    dummy_indicators = [
        "dummy", "placeholder", "demonstration", "# ... more data ...",
        "dummy values", "dummy header", "TODO", "FIXME", "replace with actual",
    ]
    content_lower = content.lower()
    for indicator in dummy_indicators:
        if indicator.lower() in content_lower:
            return ValidationResult(
                valid=False,
                message=f"Dummy/placeholder content detected: '{indicator}'",
            )

    if len(lines) < 3:
        return ValidationResult(valid=False, message="File too short (< 3 lines)")

    # --- Format-specific validation ---
    fname = os.path.basename(filepath).lower()

    if fname.endswith(".sw"):
        return _validate_sw(lines, filepath)
    elif fname.endswith(".eam.alloy") or fname.endswith(".eam.fs") or fname.endswith(".eam"):
        return _validate_eam(lines, filepath)
    elif fname.endswith(".meam"):
        return _validate_meam(lines, filepath)
    elif fname.endswith(".tersoff"):
        return _validate_tersoff(lines, filepath)
    else:
        return _validate_general(lines, filepath)


def _validate_sw(lines: list[str], filepath: str) -> ValidationResult:
    """Validate Stillinger-Weber format."""
    non_comment = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if len(non_comment) < 1:
        return ValidationResult(
            valid=False, format="sw", message="No parameter lines found"
        )

    # Check that parameter line has enough numeric fields
    for line in non_comment:
        parts = line.strip().split()
        # SW parameter line: elem elem elem + 11 numeric values (or elem elem elem + values on 2 lines)
        numeric_count = 0
        for part in parts:
            try:
                float(part)
                numeric_count += 1
            except ValueError:
                pass
        if numeric_count >= 5:
            return ValidationResult(
                valid=True,
                format="sw",
                message=f"SW potential validated ({len(lines)} lines)",
                details={"lines": len(lines), "param_fields": numeric_count},
            )

    return ValidationResult(
        valid=False,
        format="sw",
        message="SW file missing numeric parameter data",
    )


def _validate_eam(lines: list[str], filepath: str) -> ValidationResult:
    """Validate EAM (funcfl / alloy / fs) format."""
    fname = os.path.basename(filepath).lower()
    details: dict = {"lines": len(lines)}

    # Count numeric data lines
    numeric_lines = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            try:
                float(stripped.split()[0])
                numeric_lines += 1
            except (ValueError, IndexError):
                pass

    details["numeric_lines"] = numeric_lines

    if numeric_lines < 200:
        return ValidationResult(
            valid=False,
            format="eam",
            message=f"Insufficient numeric data: {numeric_lines} lines (need >200)",
            details=details,
        )

    # funcfl-specific header check
    if fname.endswith(".eam") and not fname.endswith(".eam.alloy") and not fname.endswith(".eam.fs"):
        try:
            header = lines[1].strip().split()
            if len(header) >= 4:
                atomic_num = float(header[0])
                mass = float(header[1])
                lattice_const = float(header[2])
                if not (0 < atomic_num <= 118):
                    return ValidationResult(
                        valid=False, format="eam",
                        message=f"Invalid atomic number: {atomic_num}",
                        details=details,
                    )
                if not (0 < mass <= 300):
                    return ValidationResult(
                        valid=False, format="eam",
                        message=f"Invalid atomic mass: {mass}",
                        details=details,
                    )
                if not (0 < lattice_const <= 10):
                    return ValidationResult(
                        valid=False, format="eam",
                        message=f"Invalid lattice constant: {lattice_const}",
                        details=details,
                    )
                details["atomic_num"] = atomic_num
                details["mass"] = mass
                details["lattice_const"] = lattice_const
        except (ValueError, IndexError):
            pass  # Non-standard header, but data is sufficient

    return ValidationResult(
        valid=True,
        format="eam",
        message=f"EAM potential validated ({numeric_lines} data lines)",
        details=details,
    )


def _validate_meam(lines: list[str], filepath: str) -> ValidationResult:
    """Validate MEAM format."""
    if len(lines) < 10:
        return ValidationResult(valid=False, format="meam", message="MEAM file too short")

    meam_keywords = ["rc", "delr", "augt1", "gsmooth_factor", "beta"]
    found = 0
    for line in lines[:20]:
        for kw in meam_keywords:
            if kw in line.lower():
                found += 1
                break

    if found < 2:
        return ValidationResult(
            valid=False, format="meam",
            message=f"Missing MEAM keywords (found {found}/5)",
        )

    return ValidationResult(
        valid=True, format="meam",
        message=f"MEAM potential validated ({len(lines)} lines, {found} keywords)",
    )


def _validate_tersoff(lines: list[str], filepath: str) -> ValidationResult:
    """Validate Tersoff format."""
    non_comment = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if len(non_comment) < 3:
        return ValidationResult(
            valid=False, format="tersoff", message="Tersoff file too short",
        )

    # Tersoff parameter lines typically have 14+ fields
    for line in non_comment:
        parts = line.strip().split()
        if len(parts) >= 14:
            return ValidationResult(
                valid=True, format="tersoff",
                message=f"Tersoff potential validated ({len(lines)} lines)",
            )

    return ValidationResult(
        valid=False, format="tersoff",
        message="No valid Tersoff parameter lines found (need 14+ fields)",
    )


def _validate_general(lines: list[str], filepath: str) -> ValidationResult:
    """Fallback validation for unknown formats."""
    data_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    if len(data_lines) < 10:
        return ValidationResult(
            valid=False, format="unknown",
            message=f"Insufficient data ({len(data_lines)} non-comment lines)",
        )
    return ValidationResult(
        valid=True, format="unknown",
        message=f"General validation passed ({len(lines)} lines, {len(data_lines)} data)",
    )


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------

_POTENTIAL_EXTS = {".eam", ".alloy", ".fs", ".sw", ".tersoff", ".meam", ".airebo", ".reax", ".table"}


def list_potential_files(workspace: str = ".") -> list[dict]:
    """List potential files in workspace."""
    if not os.path.isdir(workspace):
        return []

    results = []
    for name in os.listdir(workspace):
        path = os.path.join(workspace, name)
        if not os.path.isfile(path):
            continue
        # Match known potential extensions (check compound extensions first)
        low = name.lower()
        is_potential = False
        for ext in (".eam.alloy", ".eam.fs", ".eam", ".sw", ".tersoff", ".meam", ".airebo", ".reax", ".table"):
            if low.endswith(ext):
                is_potential = True
                break
        if not is_potential:
            continue

        results.append({
            "name": name,
            "size_bytes": os.path.getsize(path),
        })
    return results


def list_available_sources(element: str | None = None) -> dict:
    """List known download sources for an element (or all elements)."""
    if element:
        element = element.capitalize()
        sources = KNOWN_SOURCES.get(element, [])
        sw_available = element in SW_PARAMETERS
        return {
            "element": element,
            "known_sources": [
                {"url": url, "type": stype, "filename": fname}
                for url, stype, fname in sources
            ],
            "sw_generation": sw_available,
            "github_files": [
                f for f in GITHUB_POTENTIAL_FILES
                if f.lower().startswith(element.lower())
            ],
        }

    # All elements summary
    elements = {}
    for el, sources in KNOWN_SOURCES.items():
        elements[el] = {
            "source_count": len(sources),
            "types": list({s[1] for s in sources}),
        }
    for el in SW_PARAMETERS:
        if el not in elements:
            elements[el] = {"source_count": 0, "types": []}
        elements[el]["sw_generation"] = True

    return {"elements": elements}
