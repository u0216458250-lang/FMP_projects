"""
Определение типов данных для обработки музыкальных файлов
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class TrackInfo:
    """Информация о музыкальном треке"""
    id: str
    title: str
    artist: str
    duration: int
    series_number: int
    library_code: Optional[str] = None
    repeat_count: Optional[int] = None

    def get_concatenated(self) -> str:
        """Возвращает конкатенированную строку с информацией о треке"""
        return f"{self.id}__{self.title}__{self.artist}"
