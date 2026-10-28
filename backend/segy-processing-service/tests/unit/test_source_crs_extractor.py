import pytest

from app.domain.models.segy_metadata import SegyMetadata
from app.domain.models.textual_header import TextualHeader
from app.services.source_crs_extractor import extract_source_crs, parse_segy_textual_header


def make_metadata(text: str) -> SegyMetadata:
    return SegyMetadata(
        file_name="survey.sgy",
        file_size_bytes=1,
        trace_count=1,
        textual_header=TextualHeader(
            raw_text=text,
            encoding="ascii",
            lines=[text],
        ),
        binary_header=None,
    )


def test_extract_source_crs_from_textual_header() -> None:
    metadata = make_metadata("C07 Projection: [EPSG:32605] WGS 84 / UTM zone 5N")

    assert extract_source_crs(metadata) == "EPSG:32605"


def test_extract_source_crs_accepts_case_insensitive_epsg() -> None:
    metadata = make_metadata("Projection: [epsg=26782]")

    assert extract_source_crs(metadata) == "EPSG:26782"


def test_extract_source_crs_from_utm_textual_header() -> None:
    metadata = make_metadata("PROJECTION: UTM49N DATUM: WGS84")

    assert extract_source_crs(metadata) == "EPSG:32649"


def test_extract_source_crs_from_block_16_1_header() -> None:
    raw_header = """
    C01CLIENT: HOANG LONG JOINT OPERATING COMPANY  AREA : VIETNAM
    C02SURVEY: BLOCK 16-1                          CONTRACTOR : CGGVeritas
    C03LINE ID 161-11-1568P1001                    SEQUENCE NUMBER 001
    C14DATUM        : WGS84                      ELLIPSOID           :        WGS84
    C15SEMI-MAJOR AXIS (M) : 6378137.000         INVERSE FLATTENING  : 298.2572236
    C16PROJECTION   : UTM-48N  ZONE : 48         SCALE FACTOR        : 0.9996
    C17LONGITUDE OF ORIGIN : 105 Deg E           FALSE EASTING (M)   : 500000.00 E
    C18LATITUDE OF ORIGIN  : 0 Deg N             FALSE NORTHING (M)  : 0.00 N
    C19UNIT : INTERNATIONAL METER
    """
    metadata = make_metadata(raw_header)
    assert extract_source_crs(metadata) == "EPSG:32648"

    details = parse_segy_textual_header(raw_header)
    assert details["survey"] == "BLOCK 16-1"
    assert details["line_id"] == "161-11-1568P1001"
    assert details["datum"] == "WGS84"
    assert details["projection"] == "UTM-48N"
    assert details["zone"] == 48
    assert details["central_meridian_deg"] == 105.0
    assert details["false_easting"] == 500000.0
    assert details["scale_factor"] == 0.9996


def test_extract_source_crs_falls_back_to_default_when_no_epsg() -> None:
    metadata = make_metadata("Projection: Unknown Local Grid")

    assert extract_source_crs(metadata) == "EPSG:32649"


def test_extract_source_crs_requires_epsg_code_when_default_disabled() -> None:
    metadata = make_metadata("Projection: Unknown Local Grid")

    with pytest.raises(ValueError, match="No EPSG code found"):
        extract_source_crs(metadata, default_crs=None)


def test_extract_source_crs_louisiana_south() -> None:
    # Test case matching slb1.sgy header pattern
    header_text = (
        "C05 PROJECTION : NAD_1927_StatePlane_Louisiana_South_FIPS_1702\n"
        "C06 DATUM: NAD27 SPCS LOUISIANA SOUTH LAMBERT CONIC"
    )
    metadata = make_metadata(header_text)
    assert extract_source_crs(metadata) == "EPSG:26782"


def test_extract_source_crs_louisiana_north() -> None:
    header_text = (
        "C05 PROJECTION : NAD_1927_StatePlane_Louisiana_North_FIPS_1701\n"
        "C06 DATUM: NAD27 SPCS LOUISIANA NORTH LAMBERT CONIC"
    )
    metadata = make_metadata(header_text)
    assert extract_source_crs(metadata) == "EPSG:26781"


def test_extract_source_crs_louisiana_offshore() -> None:
    header_text = (
        "C05 PROJECTION : NAD_1927_StatePlane_Louisiana_Offshore\n"
        "C06 DATUM: NAD27 SPCS LOUISIANA OFFSHORE"
    )
    metadata = make_metadata(header_text)
    assert extract_source_crs(metadata) == "EPSG:32099"


def test_geodetic_reverse_matching_utm_wgs84() -> None:
    # Header with pure geodetic parameters (No explicit EPSG code, no zone number)
    raw_header = (
        "C10 DATUM: WGS84\n"
        "C11 PROJECTION: TRANSVERSE MERCATOR\n"
        "C12 SCALE FACTOR : 0.9996\n"
        "C13 CENTRAL MERIDIAN : 105 Deg E\n"
        "C14 FALSE EASTING (M) : 500000.00 E\n"
        "C15 FALSE NORTHING (M) : 0.00 N\n"
    )
    metadata = make_metadata(raw_header)
    assert extract_source_crs(metadata) == "EPSG:32648"


def test_geodetic_reverse_matching_utm_vn2000() -> None:
    # Same projection parameters as UTM 48N, but with VN-2000 Datum -> must resolve to EPSG:3405
    raw_header = (
        "C10 DATUM: VN-2000\n"
        "C11 SCALE FACTOR: 0.9996\n"
        "C12 LONGITUDE OF ORIGIN: 105 Deg E\n"
        "C13 FALSE EASTING: 500000.0\n"
        "C14 FALSE NORTHING: 0.0\n"
    )
    metadata = make_metadata(raw_header)
    assert extract_source_crs(metadata) == "EPSG:3405"


def test_geodetic_reverse_matching_vn2000_zone49() -> None:
    raw_header = (
        "C10 DATUM: VN2000\n"
        "C11 SCALE FACTOR: 0.9996\n"
        "C12 LONGITUDE OF ORIGIN: 111.0 Deg E\n"
        "C13 FALSE EASTING: 500000.0\n"
        "C14 FALSE NORTHING: 0.0\n"
    )
    metadata = make_metadata(raw_header)
    assert extract_source_crs(metadata) == "EPSG:3406"


def test_geodetic_reverse_matching_louisiana_south_from_parameters() -> None:
    # Header with Lambert Conformal Conic, False Easting 2,000,000, NAD27 Datum
    raw_header = (
        "C10 DATUM: NAD-27\n"
        "C11 PROJECTION: LAMBERT CONIC CONFORMAL\n"
        "C12 CENTRAL MERIDIAN: 91.333 Deg W\n"
        "C13 FALSE EASTING: 2000000.0\n"
        "C14 FALSE NORTHING: 0.0\n"
    )
    metadata = make_metadata(raw_header)
    assert extract_source_crs(metadata) == "EPSG:26782"


def test_geodetic_reverse_matching_louisiana_offshore_from_fe() -> None:
    # State Plane Louisiana Offshore uses False Easting 3,000,000
    raw_header = (
        "C10 DATUM: NAD27\n"
        "C11 PROJECTION: LAMBERT\n"
        "C12 FALSE EASTING: 3000000.0\n"
    )
    metadata = make_metadata(raw_header)
    assert extract_source_crs(metadata) == "EPSG:32099"


def test_geodetic_reverse_matching_southern_hemisphere() -> None:
    # False Northing 10,000,000 m denotes Southern Hemisphere UTM
    raw_header = (
        "C10 DATUM: WGS84\n"
        "C11 SCALE FACTOR: 0.9996\n"
        "C12 CENTRAL MERIDIAN: 111 Deg E\n"
        "C13 FALSE EASTING: 500000.0\n"
        "C14 FALSE NORTHING: 10000000.0\n"
    )
    metadata = make_metadata(raw_header)
    assert extract_source_crs(metadata) == "EPSG:32749"

