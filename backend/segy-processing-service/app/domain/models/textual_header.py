from dataclasses import dataclass


@dataclass(slots=True)
class TextualHeader:
    raw_text: str
    encoding: str
    lines: list[str]

    @property
    def line_count(self) -> int:
        return len(self.lines)