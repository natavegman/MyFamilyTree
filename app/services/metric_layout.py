"""Column layout for Russian Orthodox marriage metric book (two-page spread)."""

from dataclasses import dataclass

# Fractions of image width (left → right) for marriage register columns.
MARRIAGE_COLUMN_BOUNDARIES = [
    ("record_number", 0.00, 0.035),
    ("month_day", 0.035, 0.075),
    ("groom", 0.075, 0.28),
    ("groom_age", 0.28, 0.31),
    ("bride", 0.31, 0.52),
    ("bride_age", 0.52, 0.555),
    ("clergy", 0.555, 0.68),
    ("witnesses", 0.68, 0.92),
    ("signature", 0.92, 1.0),
]

HEADER_HEIGHT_RATIO = 0.17
TABLE_BOTTOM_RATIO = 0.96


@dataclass
class CellRegion:
    column: str
    x1: int
    y1: int
    x2: int
    y2: int
    row_index: int


@dataclass
class RowBand:
    index: int
    y1: int
    y2: int


def detect_row_bands(height: int, header_ratio: float = HEADER_HEIGHT_RATIO) -> list[RowBand]:
    """Split table body into two entry rows (typical for one spread)."""
    table_top = int(height * header_ratio)
    table_bottom = int(height * TABLE_BOTTOM_RATIO)
    table_height = table_bottom - table_top
    mid = table_top + table_height // 2
    return [
        RowBand(index=0, y1=table_top, y2=mid),
        RowBand(index=1, y1=mid, y2=table_bottom),
    ]


def build_cell_grid(width: int, height: int) -> list[CellRegion]:
    rows = detect_row_bands(height)
    cells: list[CellRegion] = []
    for row in rows:
        for column, x_start, x_end in MARRIAGE_COLUMN_BOUNDARIES:
            cells.append(
                CellRegion(
                    column=column,
                    x1=int(width * x_start),
                    y1=row.y1,
                    x2=int(width * x_end),
                    y2=row.y2,
                    row_index=row.index,
                )
            )
    return cells


def header_region(width: int, height: int) -> tuple[int, int, int, int]:
    return (int(width * 0.08), 0, int(width * 0.92), int(height * HEADER_HEIGHT_RATIO))
