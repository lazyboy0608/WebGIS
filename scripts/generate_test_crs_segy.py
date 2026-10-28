#!/usr/bin/env python3
"""
Generate synthetic 2D SEG-Y test datasets to verify Source CRS detection and manual override.
Creates:
1. data/test_crs/Test_01_CuuLong_UTM48N.sgy  (Properly labeled UTM Zone 48N - Cuu Long Basin)
2. data/test_crs/Test_02_Mislabeled_UTM49N.sgy (Header claims UTM Zone 49N, but coordinates are in Zone 48N)
"""

import sys
from pathlib import Path
import numpy as np
import segyio

def generate_synthetic_segy(
    output_path: Path,
    line_name: str,
    survey_area: str,
    datum: str,
    projection: str,
    epsg_comment: str,
    base_x: float = 770000.0,
    base_y: float = 1100000.0,
    trace_count: int = 50,
):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    spec = segyio.spec()
    spec.samples = list(range(0, 1000, 2))  # 500 samples, dt=2ms
    spec.tracecount = trace_count
    spec.format = 5  # IEEE float32

    # Construct standard 3200-byte EBCDIC/ASCII header with 40 cards of 80 chars
    lines = {
        1: f"LINE: {line_name}",
        2: f"AREA: {survey_area}",
        3: f"DATUM: {datum}",
        4: f"PROJECTION: {projection}",
        5: f"CRS COMMENT: {epsg_comment}",
        6: f"SAMPLE RATE: 2000 US, SAMPLES PER TRACE: 500",
        7: f"SCALAR: -100 (MULTIPLY COORDINATES BY 100)",
        8: f"SHOTPOINTS: 101 - {100 + trace_count}",
        40: "END TEXTUAL HEADER",
    }
    raw_text = segyio.tools.create_text_header(lines)

    # Synthetic Ricker wavelet for realistic seismic waveform
    t = np.linspace(-0.15, 0.15, 500)
    wavelet = (1.0 - 2.0 * (np.pi * 35.0 * t) ** 2) * np.exp(-(np.pi * 35.0 * t) ** 2)

    with segyio.create(str(output_path), spec) as f:
        f.text[0] = raw_text.encode("ascii")

        for i in range(trace_count):
            # Write amplitude samples with slight dip
            trace_data = np.roll(wavelet, i * 2).astype(np.float32)
            f.trace[i] = trace_data

            # Coordinates in UTM (scalar = -100 means raw int = meter * 100)
            curr_x = base_x + i * 50.0  # 50m step
            curr_y = base_y + i * 40.0
            raw_int_x = int(round(curr_x * 100))
            raw_int_y = int(round(curr_y * 100))

            hdr = f.header[i]
            hdr[segyio.TraceField.FieldRecord] = 1
            hdr[segyio.TraceField.EnergySourcePoint] = 101 + i
            hdr[segyio.TraceField.CDP] = 101 + i
            hdr[segyio.TraceField.SourceGroupScalar] = -100
            hdr[segyio.TraceField.ElevationScalar] = -100

            hdr[segyio.TraceField.SourceX] = raw_int_x
            hdr[segyio.TraceField.SourceY] = raw_int_y
            hdr[segyio.TraceField.GroupX] = raw_int_x
            hdr[segyio.TraceField.GroupY] = raw_int_y
            hdr[segyio.TraceField.CDP_X] = raw_int_x
            hdr[segyio.TraceField.CDP_Y] = raw_int_y

    print(f"-> Generated {output_path.name} ({output_path.stat().st_size / 1024:.1f} KB)")


def main():
    root_dir = Path(__file__).resolve().parent.parent
    target_dir = root_dir / "data" / "test_crs"
    target_dir.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print("  Generating Synthetic 2D SEG-Y Datasets for CRS Testing")
    print(f"  Target Directory: {target_dir}")
    print("=================================================================")

    # 1. Correctly labeled UTM Zone 48N
    file_1 = target_dir / "Test_01_CuuLong_UTM48N.sgy"
    generate_synthetic_segy(
        output_path=file_1,
        line_name="LINE_CUULONG_48N",
        survey_area="CUU LONG BASIN - OFFSHORE VIETNAM",
        datum="WGS-84",
        projection="UTM ZONE 48N",
        epsg_comment="EPSG:32648",
        base_x=770000.0,
        base_y=1100000.0,
    )

    # 2. Mislabeled as UTM Zone 49N (to test manual override)
    file_2 = target_dir / "Test_02_Mislabeled_UTM49N.sgy"
    generate_synthetic_segy(
        output_path=file_2,
        line_name="LINE_MISLABELED_49N",
        survey_area="CUU LONG BASIN - OFFSHORE VIETNAM",
        datum="WGS-84",
        projection="UTM ZONE 49N",
        epsg_comment="EPSG:32649",
        base_x=770000.0,
        base_y=1100000.0,
    )

    print("\nGeneration completed successfully! Both test files are ready.")


if __name__ == "__main__":
    main()
