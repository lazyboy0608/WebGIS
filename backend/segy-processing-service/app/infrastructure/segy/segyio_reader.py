from collections.abc import Iterator
from pathlib import Path

import segyio

from app.domain.enums.data_format import (
    SeismicDataFormat,
)
from app.domain.interfaces.segy_reader import (
    SegyReader,
)
from app.domain.models.binary_header import (
    BinaryHeader,
)
from app.domain.models.segy_metadata import (
    SegyMetadata,
)
from app.domain.models.textual_header import (
    TextualHeader,
)
from app.domain.models.trace import Trace
from app.domain.models.trace_header import (
    TraceHeader,
)
from app.exceptions.segy_exceptions import (
    SegyReadException,
)


class SegyIOReader(SegyReader):

    def read_metadata(
        self,
        file_path: Path,
    ) -> SegyMetadata:

        try:
            with segyio.open(
                str(file_path),
                "r",
                ignore_geometry=True,
            ) as segy_file:

                textual_header = (
                    self._read_textual_header(
                        segy_file
                    )
                )

                binary_header = (
                    self._read_binary_header(
                        segy_file
                    )
                )

                return SegyMetadata(
                    file_name=file_path.name,
                    file_size_bytes=file_path.stat().st_size,
                    trace_count=segy_file.tracecount,
                    textual_header=textual_header,
                    binary_header=binary_header,
                )

        except Exception as exc:
            raise SegyReadException(
                f"Failed to read SEG-Y metadata: "
                f"{file_path}"
            ) from exc

    def iter_traces(
        self,
        file_path: Path,
        include_samples: bool = False,
    ) -> Iterator[Trace]:

        try:
            with segyio.open(
                str(file_path),
                "r",
                ignore_geometry=True,
            ) as segy_file:

                for index in range(
                    segy_file.tracecount
                ):

                    header = (
                        self._read_trace_header(
                            segy_file,
                            index,
                        )
                    )

                    samples = None

                    if include_samples:
                        samples = (
                            segy_file.trace[index]
                            .tolist()
                        )

                    yield Trace(
                        index=index,
                        header=header,
                        samples=samples,
                    )

        except Exception as exc:
            raise SegyReadException(
                f"Failed to read SEG-Y traces: "
                f"{file_path}"
            ) from exc
    def _read_textual_header(
        self,
        segy_file: segyio.SegyFile,
    ) -> TextualHeader:

        raw_header = segy_file.text[0]

        if isinstance(raw_header, (bytes, bytearray)):
            text = bytes(raw_header).decode(
                "ascii",
                errors="replace",
            )
            encoding = "ascii"
        else:
            text = str(raw_header)
            encoding = "ascii"

        lines = [
            text[index:index + 80]
            for index in range(
                0,
                len(text),
                80,
            )
        ]

        return TextualHeader(
            raw_text=text,
            encoding=encoding,
            lines=lines,
        )
    def _read_binary_header(
        self,
        segy_file: segyio.SegyFile,
    ) -> BinaryHeader:

        sample_interval = int(
            segy_file.bin[
                segyio.BinField.Interval
            ]
        )

        samples_per_trace = int(
            segy_file.bin[
                segyio.BinField.Samples
            ]
        )

        format_code = int(
            segy_file.bin[
                segyio.BinField.Format
            ]
        )

        ensemble_fold = int(
            segy_file.bin[
                segyio.BinField.EnsembleFold
            ]
        )

        measurement_system = int(
            segy_file.bin[
                segyio.BinField.MeasurementSystem
            ]
        )

        revision_major = int(
            segy_file.bin[
                segyio.BinField.SEGYRevision
            ]
        )

        revision_minor = int(
            segy_file.bin[
                segyio.BinField.SEGYRevisionMinor
            ]
        )

        try:
            sample_format = (
                SeismicDataFormat(format_code)
            )
        except ValueError:
            raise SegyReadException(
                f"Unsupported SEG-Y sample "
                f"format code: {format_code}"
            )

        return BinaryHeader(
            sample_interval_microseconds=sample_interval,
            samples_per_trace=samples_per_trace,
            sample_format=sample_format,
            ensemble_fold=ensemble_fold,
            measurement_system=measurement_system,
            segy_revision_major=revision_major,
            segy_revision_minor=revision_minor,
        )
    def _read_trace_header(
        self,
        segy_file: segyio.SegyFile,
        index: int,
    ) -> TraceHeader:

        header = segy_file.header[index]

        return TraceHeader(
            trace_sequence_number=header[
                segyio.TraceField.TRACE_SEQUENCE_LINE
            ],

            trace_sequence_number_within_line=header[
                segyio.TraceField.TRACE_SEQUENCE_FILE
            ],

            original_field_record_number=header[
                segyio.TraceField.FieldRecord
            ],

            trace_number_within_field_record=header[
                segyio.TraceField.TraceNumber
            ],

            energy_source_point=header[
                segyio.TraceField.EnergySourcePoint
            ],

            cdp_ensemble_number=header[
                segyio.TraceField.CDP
            ],

            cdp_trace_number=header[
                segyio.TraceField.CDP_TRACE
            ],

            source_x=header[
                segyio.TraceField.SourceX
            ],

            source_y=header[
                segyio.TraceField.SourceY
            ],

            coordinate_scalar=header[
                segyio.TraceField.SourceGroupScalar
            ],

            coordinate_units=header[
                segyio.TraceField.CoordinateUnits
            ],
        )