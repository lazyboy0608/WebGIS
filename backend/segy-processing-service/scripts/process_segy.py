import argparse
from collections import Counter
from math import hypot
from pathlib import Path

from app.infrastructure.segy.segyio_reader import (
    SegyIOReader,
)
from app.services.segy_reader import (
    SegyReaderService,
)
from app.services.segy_validator import (
    SegyValidator,
)


def print_section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def main() -> None:
    # ---------------------------------------------------------
    # 1. Input
    # ---------------------------------------------------------

    parser = argparse.ArgumentParser(description="Inspect and process a SEG-Y file")
    parser.add_argument("file_path", type=Path, help="Path to the SEG-Y file")
    file_path = parser.parse_args().file_path

    print_section(
        "SEG-Y PROCESSING SERVICE"
    )

    print(f"Input file     : {file_path}")
    print(
        f"Absolute path  : "
        f"{file_path.resolve()}"
    )

    print(
        f"File exists    : "
        f"{file_path.exists()}"
    )

    if not file_path.exists():
        print(
            "ERROR: SEG-Y file does not exist."
        )
        return

    file_size = file_path.stat().st_size

    print(
        f"File size      : "
        f"{file_size:,} bytes"
    )

    # ---------------------------------------------------------
    # 2. Initialize services
    # ---------------------------------------------------------

    print_section(
        "INITIALIZING SERVICES"
    )

    reader = SegyIOReader()

    validator = SegyValidator()

    service = SegyReaderService(
        reader=reader,
        validator=validator,
    )

    print(
        "SegyIOReader       : OK"
    )

    print(
        "SegyValidator      : OK"
    )

    print(
        "SegyReaderService  : OK"
    )

    # ---------------------------------------------------------
    # 3. Read metadata
    # ---------------------------------------------------------

    print_section(
        "SEG-Y METADATA"
    )

    metadata = service.read_metadata(
        file_path
    )

    binary = metadata.binary_header

    print(
        f"File               : "
        f"{metadata.file_name}"
    )

    print(
        f"File size          : "
        f"{metadata.file_size_bytes:,} bytes"
    )

    print(
        f"Trace count        : "
        f"{metadata.trace_count}"
    )

    print(
        f"Samples / trace    : "
        f"{binary.samples_per_trace}"
    )

    print(
        f"Sample interval    : "
        f"{binary.sample_interval_microseconds} μs"
    )

    print(
        f"Sample format      : "
        f"{binary.sample_format}"
    )

    print(
        f"Measurement system : "
        f"{binary.measurement_system}"
    )

    print(
        f"SEG-Y revision     : "
        f"{binary.segy_revision_major}."
        f"{binary.segy_revision_minor}"
    )

    # ---------------------------------------------------------
    # 4. Profiling containers
    # ---------------------------------------------------------

    sp_counter: Counter[int] = Counter()

    scalar_counter: Counter[int] = Counter()

    coordinate_units_counter: Counter[int] = (
        Counter()
    )

    coordinate_points: list[
        tuple[float, float]
    ] = []

    trace_records: list[
        tuple[int, int | None, float | None, float | None]
    ] = []

    missing_sp_count = 0

    missing_x_count = 0

    missing_y_count = 0

    missing_coordinate_count = 0

    # ---------------------------------------------------------
    # 5. Read ALL trace headers
    #
    # IMPORTANT:
    # include_samples=False
    #
    # We only read trace headers.
    # Seismic samples are NOT loaded.
    # ---------------------------------------------------------

    print_section(
        "READING TRACE HEADERS"
    )

    for trace in service.iter_traces(
        file_path,
        include_samples=False,
    ):
        header = trace.header

        sp = header.energy_source_point

        x = header.source_x

        y = header.source_y

        scalar = header.coordinate_scalar

        coordinate_units = (
            header.coordinate_units
        )

        # ---------------------------------------------
        # SP
        # ---------------------------------------------

        if sp is not None:
            sp_counter[sp] += 1
        else:
            missing_sp_count += 1

        # ---------------------------------------------
        # Scalar
        # ---------------------------------------------

        if scalar is not None:
            scalar_counter[scalar] += 1

        # ---------------------------------------------
        # Coordinate units
        # ---------------------------------------------

        if coordinate_units is not None:
            coordinate_units_counter[
                coordinate_units
            ] += 1

        # ---------------------------------------------
        # Coordinates
        # ---------------------------------------------

        if x is None:
            missing_x_count += 1

        if y is None:
            missing_y_count += 1

        if x is None or y is None:
            missing_coordinate_count += 1
        else:
            coordinate_points.append(
                (
                    float(x),
                    float(y),
                )
            )

        # ---------------------------------------------
        # Keep trace-level information
        # ---------------------------------------------

        trace_records.append(
            (
                trace.index,
                sp,
                (
                    float(x)
                    if x is not None
                    else None
                ),
                (
                    float(y)
                    if y is not None
                    else None
                ),
            )
        )

    print(
        f"Processed traces : "
        f"{len(trace_records)}"
    )

    # ---------------------------------------------------------
    # 6. SP statistics
    # ---------------------------------------------------------

    print_section(
        "SP STATISTICS"
    )

    print(
        f"Unique SP count   : "
        f"{len(sp_counter)}"
    )

    print(
        f"Missing SP        : "
        f"{missing_sp_count}"
    )

    if sp_counter:
        print(
            f"Minimum SP        : "
            f"{min(sp_counter)}"
        )

        print(
            f"Maximum SP        : "
            f"{max(sp_counter)}"
        )

    print()
    print(
        "First 20 SP values:"
    )

    for sp, count in sorted(
        sp_counter.items()
    )[:20]:

        print(
            f"  SP {sp:<10} "
            f"{count} trace(s)"
        )

    # ---------------------------------------------------------
    # 7. Coordinate statistics
    # ---------------------------------------------------------

    print_section(
        "COORDINATE STATISTICS"
    )

    print(
        f"Valid coordinates : "
        f"{len(coordinate_points)}"
    )

    print(
        f"Missing X         : "
        f"{missing_x_count}"
    )

    print(
        f"Missing Y         : "
        f"{missing_y_count}"
    )

    print(
        f"Missing coordinate: "
        f"{missing_coordinate_count}"
    )

    if coordinate_points:

        xs = [
            point[0]
            for point in coordinate_points
        ]

        ys = [
            point[1]
            for point in coordinate_points
        ]

        min_x = min(xs)
        max_x = max(xs)

        min_y = min(ys)
        max_y = max(ys)

        print()

        print(
            f"X min             : "
            f"{min_x}"
        )

        print(
            f"X max             : "
            f"{max_x}"
        )

        print(
            f"Y min             : "
            f"{min_y}"
        )

        print(
            f"Y max             : "
            f"{max_y}"
        )

        print()

        print(
            f"X range           : "
            f"{max_x - min_x}"
        )

        print(
            f"Y range           : "
            f"{max_y - min_y}"
        )

    # ---------------------------------------------------------
    # 8. Scalar statistics
    # ---------------------------------------------------------

    print_section(
        "COORDINATE SCALAR STATISTICS"
    )

    print(
        f"Unique scalars    : "
        f"{len(scalar_counter)}"
    )

    for scalar, count in sorted(
        scalar_counter.items()
    ):

        print(
            f"  Scalar {scalar:<8} "
            f"{count} trace(s)"
        )

    # ---------------------------------------------------------
    # 9. Coordinate units statistics
    # ---------------------------------------------------------

    print_section(
        "COORDINATE UNITS STATISTICS"
    )

    for units, count in sorted(
        coordinate_units_counter.items()
    ):

        print(
            f"  Unit {units:<10} "
            f"{count} trace(s)"
        )

    # ---------------------------------------------------------
    # 10. Duplicate coordinates
    # ---------------------------------------------------------

    print_section(
        "DUPLICATE COORDINATE ANALYSIS"
    )

    coordinate_counter = Counter(
        coordinate_points
    )

    duplicate_coordinates = {
        coordinate: count
        for coordinate, count
        in coordinate_counter.items()
        if count > 1
    }

    print(
        f"Unique coordinates : "
        f"{len(coordinate_counter)}"
    )

    print(
        f"Duplicate coordinate groups: "
        f"{len(duplicate_coordinates)}"
    )

    if duplicate_coordinates:

        print()

        print(
            "First 20 duplicate coordinates:"
        )

        for coordinate, count in list(
            sorted(
                duplicate_coordinates.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        )[:20]:

            print(
                f"  {coordinate} "
                f"→ {count} occurrence(s)"
            )

    # ---------------------------------------------------------
    # 11. Consecutive coordinate spacing
    # ---------------------------------------------------------

    print_section(
        "CONSECUTIVE COORDINATE SPACING"
    )

    distances: list[float] = []

    previous_point: (
        tuple[float, float] | None
    ) = None

    for x, y in coordinate_points:

        current_point = (x, y)

        if previous_point is not None:

            distance = hypot(
                current_point[0]
                - previous_point[0],
                current_point[1]
                - previous_point[1],
            )

            distances.append(distance)

        previous_point = current_point

    if distances:

        print(
            f"Distance count    : "
            f"{len(distances)}"
        )

        print(
            f"Minimum distance  : "
            f"{min(distances)}"
        )

        print(
            f"Maximum distance  : "
            f"{max(distances)}"
        )

        print(
            f"Average distance  : "
            f"{sum(distances) / len(distances):.4f}"
        )

        print()

        print(
            "First 20 distances:"
        )

        for index, distance in enumerate(
            distances[:20],
            start=1,
        ):

            print(
                f"  {index:>3}: "
                f"{distance:.4f}"
            )

    # ---------------------------------------------------------
    # 12. SP transition analysis
    # ---------------------------------------------------------

    print_section(
        "SP TRANSITION ANALYSIS"
    )

    previous_sp: int | None = None

    transition_counter: Counter[
        tuple[int, int]
    ] = Counter()

    for (
        _trace_index,
        sp,
        _x,
        _y,
    ) in trace_records:

        if (
            previous_sp is not None
            and sp is not None
        ):

            transition_counter[
                (
                    previous_sp,
                    sp,
                )
            ] += 1

        if sp is not None:
            previous_sp = sp

    print(
        f"Unique transitions: "
        f"{len(transition_counter)}"
    )

    print()

    for (
        previous,
        current,
    ), count in list(
        sorted(
            transition_counter.items()
        )
    )[:30]:

        print(
            f"  {previous} → {current} "
            f"({count} time(s))"
        )

    # ---------------------------------------------------------
    # 13. First 20 traces
    # ---------------------------------------------------------

    print_section(
        "FIRST 20 TRACE RECORDS"
    )

    for (
        trace_index,
        sp,
        x,
        y,
    ) in trace_records[:20]:

        print(
            f"Trace #{trace_index:<5} "
            f"SP={str(sp):<8} "
            f"X={str(x):<12} "
            f"Y={str(y):<12}"
        )

    # ---------------------------------------------------------
    # 14. Finish
    # ---------------------------------------------------------

    print_section(
        "PROFILING COMPLETED"
    )

    print(
        "No seismic trace samples were loaded."
    )

    print(
        "Only SEG-Y metadata and trace headers "
        "were analyzed."
    )


if __name__ == "__main__":
    main()
