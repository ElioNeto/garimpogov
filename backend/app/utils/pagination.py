import math
from dataclasses import dataclass


@dataclass
class PaginationParams:
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def total_pages(self, total: int) -> int:
        return math.ceil(total / self.page_size) if self.page_size > 0 else 0
