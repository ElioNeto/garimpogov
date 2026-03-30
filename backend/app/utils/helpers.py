import re
from datetime import datetime
from typing import Optional


def parse_salary(salary_str: str) -> Optional[float]:
    """Parse Brazilian salary string to float. E.g. 'R$ 5.500,00' -> 5500.0"""
    if not salary_str:
        return None
    cleaned = re.sub(r"[^\d,]", "", salary_str)
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_date(date_str: str) -> Optional[datetime]:
    """Try common Brazilian date formats."""
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None
