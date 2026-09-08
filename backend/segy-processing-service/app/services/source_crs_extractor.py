import re
from pathlib import Path
from typing import Sequence
import segyio
from pyproj import Transformer

from app.domain.models.segy_metadata import SegyMetadata

EPSG_PATTERN = re.compile(r"\bEPSG\s*[:=]\s*(\d{4,6})\b", re.IGNORECASE)
UTM_PATTERN = re.compile(r"\bUTM\s*(?:ZONE\s*)?(\d{1,2})\s*([NS])?\b", re.IGNORECASE)
VN2000_PATTERN = re.compile(r"\bVN-?2000\b", re.IGNORECASE)
HN72_PATTERN = re.compile(r"\b(?:HN-?72|HANOI\s*1972|HANOI-72)\b", re.IGNORECASE)

DEFAULT_SOURCE_CRS = "EPSG:32649"
DEFAULT_TARGET_CRS = "EPSG:4326"


def extract_sample_coordinates_from_file(file_path: Path | str) -> list[tuple[float, float]]:
    """Extract up to 5 sample scaled trace coordinates (x, y) from a SEG-Y file."""
    coords: list[tuple[float, float]] = []
    try:
        path_str = str(file_path)
        with segyio.open(path_str, "r", ignore_geometry=True) as segy_file:
            n_traces = segy_file.tracecount
            if n_traces == 0:
                return []
            sample_indices = [
                0,
                n_traces // 4,
                n_traces // 2,
                (3 * n_traces) // 4,
                n_traces - 1,
            ]
            sample_indices = sorted(list(set(sample_indices)))
            for idx in sample_indices:
                hdr = segy_file.header[idx]
                scalar = hdr[segyio.TraceField.SourceGroupScalar]
                mult = 1.0 / abs(scalar) if scalar < 0 else (float(scalar) if scalar > 0 else 1.0)

                src_x = hdr[segyio.TraceField.SourceX] * mult
                src_y = hdr[segyio.TraceField.SourceY] * mult
                if src_x != 0 and src_y != 0:
                    coords.append((src_x, src_y))
                else:
                    cdp_x = hdr[segyio.TraceField.CDP_X] * mult
                    cdp_y = hdr[segyio.TraceField.CDP_Y] * mult
                    if cdp_x != 0 and cdp_y != 0:
                        coords.append((cdp_x, cdp_y))
    except Exception:
        pass
    return coords


def validate_and_heal_source_crs(
    candidate_crs: str,
    sample_coords: Sequence[tuple[float, float]] | None = None,
    file_path: Path | str | None = None,
    target_crs: str = DEFAULT_TARGET_CRS,
    reference_target_coords: Sequence[tuple[float, float]] | None = None,
) -> str:
    """
    Cross-validate candidate_crs (EPSG A) by checking spatial alignment and map transformation
    consistency with target_crs (EPSG B, default EPSG:4326).

    1. Checks if raw sample coordinates are ALREADY in target_crs (geographic degrees EPSG:4326).
       If so, candidate_crs is set directly to target_crs (EPSG:4326) to avoid false projection distortion.
    2. Validates that transforming candidate_crs (EPSG A) to target_crs (EPSG B) yields valid
       non-null geographic map coordinates [-180, 180] x [-90, 90].
    3. If reference_target_coords are provided in EPSG B (EPSG:4326), verifies spatial alignment within tolerance.
    """
    coords = list(sample_coords) if sample_coords else []
    if not coords and file_path:
        coords = extract_sample_coordinates_from_file(file_path)

    if not coords:
        return candidate_crs

    # 1. Check if raw file coordinates are ALREADY in geographic degrees (EPSG B / EPSG:4326)
    are_coords_already_geographic = all(
        -180.0 <= x <= 180.0 and -90.0 <= y <= 90.0
        for x, y in coords
    )
    if are_coords_already_geographic:
        return target_crs

    # Helper to test if a CRS code produces valid map coordinates in target_crs
    def is_transformation_spatially_valid(crs_code: str) -> bool:
        try:
            transformer = Transformer.from_crs(crs_code, target_crs, always_xy=True)
            valid_cnt = 0
            for idx, (x, y) in enumerate(coords):
                tx, ty = transformer.transform(x, y)
                # Check valid geographic latitude [-90, 90] and longitude [-180, 180]
                if (
                    isinstance(tx, (int, float)) and isinstance(ty, (int, float))
                    and not (tx != tx or ty != ty)  # Check not NaN
                    and -180.0 <= tx <= 180.0
                    and -90.0 <= ty <= 90.0
                    and not (abs(tx) < 0.0001 and abs(ty) < 0.0001)  # Exclude (0,0) Null Island distortion
                ):
                    # If reference target coords (in EPSG B) are provided, check spatial alignment
                    if reference_target_coords and idx < len(reference_target_coords):
                        ref_x, ref_y = reference_target_coords[idx]
                        dist = ((tx - ref_x) ** 2 + (ty - ref_y) ** 2) ** 0.5
                        if dist > 1.0:  # Tolerance threshold in degrees (~100km)
                            continue
                    valid_cnt += 1
            return valid_cnt > 0 and (valid_cnt / len(coords)) >= 0.5
        except Exception:
            return False

    # 2. Check candidate_crs
    if is_transformation_spatially_valid(candidate_crs):
        return candidate_crs

    # 3. If candidate_crs transformation is invalid, attempt fallback check
    if is_transformation_spatially_valid("EPSG:32649"):
        return "EPSG:32649"

    return candidate_crs


def extract_source_crs(
    metadata: SegyMetadata,
    default_crs: str | None = DEFAULT_SOURCE_CRS,
    file_path: Path | str | None = None,
    sample_coords: Sequence[tuple[float, float]] | None = None,
    target_crs: str = DEFAULT_TARGET_CRS,
    reference_target_coords: Sequence[tuple[float, float]] | None = None,
) -> str:
    """Extract the source CRS authority code from the SEG-Y textual header with target CRS cross-validation."""
    text = metadata.textual_header.raw_text

    # Helper for validation
    def validate(code: str) -> str:
        return validate_and_heal_source_crs(
            code,
            sample_coords=sample_coords,
            file_path=file_path,
            target_crs=target_crs,
            reference_target_coords=reference_target_coords,
        )

    # 1. Regex search for explicit EPSG code
    match = EPSG_PATTERN.search(text)
    if match is not None:
        candidate = f"EPSG:{match.group(1)}"
        return validate(candidate)

    # 2. Regex search for VN-2000
    if VN2000_PATTERN.search(text):
        if "48" in text or "105" in text:
            candidate = "EPSG:3405"
        elif "49" in text or "111" in text:
            candidate = "EPSG:3406"
        else:
            candidate = "EPSG:3406"
        return validate(candidate)

    # 3. Regex search for HN-72
    if HN72_PATTERN.search(text):
        candidate = "EPSG:2048"
        return validate(candidate)

    # 4. Regex search for UTM Projection
    utm_match = UTM_PATTERN.search(text)
    if utm_match is not None:
        zone = int(utm_match.group(1))
        hemi = (utm_match.group(2) or "N").upper()
        if 1 <= zone <= 60:
            epsg_code = 32600 + zone if hemi == "N" else 32700 + zone
            candidate = f"EPSG:{epsg_code}"
            return validate(candidate)

    # 5. Fallback if no matching pattern in header
    if default_crs is not None:
        return validate(default_crs)

    raise ValueError(
        f"No EPSG code found in SEG-Y textual header: {metadata.file_name}"
    )