import re
from pathlib import Path
from typing import Any, Sequence
import segyio
from pyproj import Transformer

from app.domain.models.segy_metadata import SegyMetadata

EPSG_PATTERN = re.compile(r"\bEPSG\s*[:=]\s*(\d{4,6})\b", re.IGNORECASE)
UTM_PATTERN = re.compile(r"\bUTM\s*[-_ ]?(?:ZONE\s*)?(\d{1,2})\s*([NS])?\b", re.IGNORECASE)
VN2000_PATTERN = re.compile(r"\bVN-?2000\b", re.IGNORECASE)
HN72_PATTERN = re.compile(r"\b(?:HN-?72|HANOI\s*1972|HANOI-72)\b", re.IGNORECASE)

DEFAULT_SOURCE_CRS = "EPSG:32649"
DEFAULT_TARGET_CRS = "EPSG:4326"


def parse_segy_textual_header(text: str | None) -> dict[str, Any]:
    """
    Parse seismic acquisition and navigation parameters from the SEG-Y 3200-byte textual header.
    Extracts Survey, Line ID, Client, Contractor, Datum, Ellipsoid, Projection, Zone,
    Central Meridian, False Easting, False Northing, Scale Factor, Units, etc.
    """
    if not text:
        return {}

    details: dict[str, Any] = {}

    def extract_field(patterns: list[str]) -> str | None:
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                val = m.group(1).strip()
                if val:
                    return val
        return None

    # 1. Survey / Block Name
    survey = extract_field([
        r"\bSURVEY\s*[:=]\s*([^:\r\n]+?)(?=\s{2,}[A-Z\s]{3,}\s*:|\r|\n|$)",
        r"\bBLOCK\s*[:=]?\s*([A-Za-z0-9_\-\s]+?)(?=\s{2,}[A-Z\s]{3,}\s*:|\r|\n|$)",
    ])
    if survey:
        details["survey"] = survey

    # 2. Line ID / Name
    line_id = extract_field([
        r"\b(?:LINE\s*ID|LINE\s*NAME|LINE)\s*[:=]?\s*([^:\r\n]+?)(?=\s{2,}[A-Z\s]{3,}\s*:|\r|\n|$)",
    ])
    if line_id:
        details["line_id"] = line_id

    # 3. Client & Contractor
    client = extract_field([
        r"\bCLIENT\s*[:=]\s*([^:\r\n]+?)(?=\s{2,}[A-Z\s]{3,}\s*:|\r|\n|$)",
    ])
    if client:
        details["client"] = client

    contractor = extract_field([
        r"\bCONTRACTOR\s*[:=]\s*([^:\r\n]+?)(?=\s{2,}[A-Z\s]{3,}\s*:|\r|\n|$)",
    ])
    if contractor:
        details["contractor"] = contractor

    # 4. Datum & Ellipsoid
    datum = extract_field([
        r"\bDATUM\s*[:=]\s*([A-Za-z0-9_\-]+)",
    ])
    if datum:
        details["datum"] = datum.upper()

    ellipsoid = extract_field([
        r"\bELLIPSOID\s*[:=]\s*([A-Za-z0-9_\-]+)",
    ])
    if ellipsoid:
        details["ellipsoid"] = ellipsoid.upper()

    # 5. Projection & Zone
    projection = extract_field([
        r"\bPROJECTION\s*[:=]\s*([A-Za-z0-9_\-]+)",
    ])
    if projection:
        details["projection"] = projection.upper()

    zone_val = extract_field([
        r"\bZONE\s*[:=]?\s*(\d{1,2})\b",
        r"\bUTM-?(\d{1,2})[NS]?\b",
    ])
    if zone_val and zone_val.isdigit():
        details["zone"] = int(zone_val)

    # 6. Central Meridian / Longitude of Origin
    m_cm = re.search(
        r"(?:LONGITUDE\s*OF\s*ORIGIN|CENTRAL\s*MERIDIAN)\s*[:=]\s*([0-9.]+)\s*(?:Deg)?\s*([EW])?",
        text,
        re.IGNORECASE,
    )
    if m_cm:
        deg = float(m_cm.group(1))
        hemi = (m_cm.group(2) or "E").upper()
        details["central_meridian"] = f"{deg}° {hemi}"
        details["central_meridian_deg"] = deg if hemi == "E" else -deg

    # 7. Latitude of Origin
    m_lat = re.search(
        r"\bLATITUDE\s*OF\s*ORIGIN\s*[:=]\s*([0-9.]+)\s*(?:Deg)?\s*([NS])?",
        text,
        re.IGNORECASE,
    )
    if m_lat:
        deg = float(m_lat.group(1))
        hemi = (m_lat.group(2) or "N").upper()
        details["latitude_of_origin"] = f"{deg}° {hemi}"

    # 8. False Easting & False Northing
    fe = extract_field([
        r"\bFALSE\s*EASTING(?:\s*\(M\))?\s*[:=]\s*([0-9.]+)",
    ])
    if fe:
        try:
            details["false_easting"] = float(fe)
        except ValueError:
            pass

    fn = extract_field([
        r"\bFALSE\s*NORTHING(?:\s*\(M\))?\s*[:=]\s*([0-9.]+)",
    ])
    if fn:
        try:
            details["false_northing"] = float(fn)
        except ValueError:
            pass

    # 9. Scale Factor
    sf = extract_field([
        r"\bSCALE\s*FACTOR\s*[:=]\s*([0-9.]+)",
    ])
    if sf:
        try:
            details["scale_factor"] = float(sf)
        except ValueError:
            pass

    # 10. Units
    unit = extract_field([
        r"\bUNIT\s*[:=]\s*([^:\r\n]+?)(?=\s{2,}|\r|\n|$)",
    ])
    if unit:
        details["units"] = unit

    return details


def extract_sample_coordinates_from_file(file_path: Path | str) -> list[tuple[float, float]]:
    """
    Extract up to 5 sample scaled trace coordinates (x, y) from a SEG-Y file.
    Supports both SAC (SourceGroupScalar) and SAED (ElevationScalar) fallback.
    """
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
                sac = hdr[segyio.TraceField.SourceGroupScalar]
                saed = hdr[segyio.TraceField.ElevationScalar] if segyio.TraceField.ElevationScalar in hdr else 1

                # Priority: SAC (bytes 71-72) -> fallback SAED (bytes 69-70) if SAC is 0 or 1
                scalar = sac if (sac != 0 and sac != 1) else (saed if (saed != 0 and saed != 1) else 1)
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
                if (
                    isinstance(tx, (int, float)) and isinstance(ty, (int, float))
                    and not (tx != tx or ty != ty)  # Check not NaN
                    and -180.0 <= tx <= 180.0
                    and -90.0 <= ty <= 90.0
                    and not (abs(tx) < 0.0001 and abs(ty) < 0.0001)  # Exclude (0,0) Null Island
                ):
                    if reference_target_coords and idx < len(reference_target_coords):
                        ref_x, ref_y = reference_target_coords[idx]
                        dist = ((tx - ref_x) ** 2 + (ty - ref_y) ** 2) ** 0.5
                        if dist > 1.0:  # Tolerance threshold in degrees
                            continue
                    valid_cnt += 1
            return valid_cnt > 0 and (valid_cnt / len(coords)) >= 0.5
        except Exception:
            return False

    # 2. Check candidate_crs
    if is_transformation_spatially_valid(candidate_crs):
        return candidate_crs

    # 3. If candidate_crs transformation is invalid, attempt fallback check
    if is_transformation_spatially_valid("EPSG:32648"):
        return "EPSG:32648"
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
    """
    Extract the source CRS authority code from the SEG-Y textual header with target CRS cross-validation.
    Synthesizes Projection, Zone, Datum, Ellipsoid, Central Meridian, False Easting/Northing, and Survey context.
    """
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

    # 1. Regex search for explicit EPSG code in textual header
    match = EPSG_PATTERN.search(text)
    if match is not None:
        candidate = f"EPSG:{match.group(1)}"
        return validate(candidate)

    # 2. Parse structured header parameters
    details = parse_segy_textual_header(text)
    datum_str = str(details.get("datum", "")).upper()
    proj_str = str(details.get("projection", "")).upper()
    zone_int = details.get("zone")
    cm_deg = details.get("central_meridian_deg")

    # If zone is not explicitly provided, deduce from central meridian (105° -> 48, 111° -> 49, 117° -> 50)
    if zone_int is None and cm_deg is not None:
        if abs(cm_deg - 105.0) < 1.0:
            zone_int = 48
        elif abs(cm_deg - 111.0) < 1.0:
            zone_int = 49
        elif abs(cm_deg - 117.0) < 1.0:
            zone_int = 50

    # If zone is still None, check regex search in entire text for UTM-48N or UTM-49N or ZONE 48/49
    if zone_int is None:
        m_zone = re.search(r"\b(?:UTM[-_ ]?|ZONE\s*[:=]?\s*)(\d{1,2})\b", text, re.IGNORECASE)
        if m_zone:
            zone_int = int(m_zone.group(1))

    # Determine hemisphere (default N)
    hemi = "N"
    m_hemi = re.search(r"\bUTM[-_ ]?\d{1,2}\s*([NS])\b", text, re.IGNORECASE)
    if m_hemi:
        hemi = m_hemi.group(1).upper()

    # 3. Check VN-2000
    if "VN2000" in datum_str or "VN-2000" in datum_str or VN2000_PATTERN.search(text):
        if zone_int == 48 or (cm_deg and abs(cm_deg - 105.0) < 1.0):
            return validate("EPSG:3405")
        elif zone_int == 49 or (cm_deg and abs(cm_deg - 111.0) < 1.0):
            return validate("EPSG:3406")
        elif "48" in text or "105" in text:
            return validate("EPSG:3405")
        else:
            return validate("EPSG:3406")

    # 4. Check Hanoi 1972 (HN-72)
    if "HN72" in datum_str or "HN-72" in datum_str or "HANOI" in datum_str or HN72_PATTERN.search(text):
        if zone_int == 49 or "49" in text:
            return validate("EPSG:2049")
        return validate("EPSG:2048")

    # 5. Check UTM with WGS84 or general UTM projection
    if "UTM" in proj_str or "UTM" in text.upper() or zone_int is not None:
        if zone_int and 1 <= zone_int <= 60:
            epsg_code = 32600 + zone_int if hemi == "N" else 32700 + zone_int
            return validate(f"EPSG:{epsg_code}")

    # 6. Check SURVEY context (e.g. Block 16-1, Block 15-1 in Cuu Long Basin -> UTM 48N)
    survey_text = str(details.get("survey", "")).upper()
    if any(k in survey_text for k in ["16-1", "15-1", "15-2", "09-1", "BACH HO", "TE GIAC TRANG"]):
        return validate("EPSG:32648")
    elif any(k in survey_text for k in ["05-2", "05-3", "06-1", "NAM CON SON"]):
        return validate("EPSG:32649")

    # 7. Fallback to default
    if default_crs is not None:
        return validate(default_crs)

    raise ValueError(
        f"No EPSG code found in SEG-Y textual header: {metadata.file_name}"
    )