import argparse
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
from app.services.trace_header_profiler import (
    TraceHeaderProfiler,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile headers in a SEG-Y file")
    parser.add_argument("file_path", type=Path, help="Path to the SEG-Y file")
    segy_file = parser.parse_args().file_path

    print("=" * 70)
    print("SEG-Y TRACE HEADER PROFILER")
    print("=" * 70)

    print(f"Input file : {segy_file}")
    print(f"Exists     : {segy_file.exists()}")

    reader_service = SegyReaderService(
        reader=SegyIOReader(),
        validator=SegyValidator(),
    )

    profiler = TraceHeaderProfiler()

    traces = reader_service.iter_traces(
        file_path=segy_file,
        include_samples=False,
    )

    profile = profiler.profile(traces)

    print()
    print("=" * 70)
    print("GENERAL")
    print("=" * 70)

    print(f"Trace count : {profile.trace_count}")

    for field_name, statistics in (
        profile.fields.items()
    ):
        print()
        print("-" * 70)
        print(field_name)

        print(
            f"Total   : "
            f"{statistics.total_count}"
        )

        print(
            f"Missing : "
            f"{statistics.missing_count}"
        )

        print(
            f"Unique  : "
            f"{statistics.unique_count}"
        )

        print(
            f"Minimum : "
            f"{statistics.minimum}"
        )

        print(
            f"Maximum : "
            f"{statistics.maximum}"
        )

        print("Top values:")

        sorted_values = sorted(
            statistics.values.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        for value, count in sorted_values[:20]:
            print(
                f"  {value}: "
                f"{count} trace(s)"
            )


if __name__ == "__main__":
    main()
