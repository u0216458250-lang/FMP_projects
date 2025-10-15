"""
Основной модуль обработки музыкальных файлов
"""
import logging
from typing import List, Dict, Any
import pandas as pd
import os

import config
from models import TrackInfo

class MusicFileProcessor:
    """Процессор для обработки музыкальных файлов"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def read_input(self, input_path: str) -> pd.DataFrame:
        """Читает входной CSV файл"""
        return pd.read_csv(
            input_path,
            sep=config.CSV_SEPARATOR,
            header=None,
            names=config.INPUT_COLUMNS
        )
    
    def parse_filename(self, filename: str) -> tuple[str, str, str]:
        """
        Парсит имя файла и извлекает информацию о треке.
        
        Args:
            filename: Имя файла в формате "*_ID_НАЗВАНИЕ_ИСПОЛНИТЕЛЬ.mp3"
        
        Returns:
            tuple: (item_id, title, artist)
        """
        try:
            main_part = filename.split('.mp3')[0]
            parts = main_part.split('_')
            if len(parts) >= 4:
                artist = parts[-1].replace('-', ' ').title()
                title = parts[-2].replace('-', ' ').title()
                item_id = '_'.join(parts[1:-2])
                return item_id, title, artist
            return None, None, None
        except:
            return None, None, None
    
    def parse_tracks(self, df: pd.DataFrame) -> pd.DataFrame:
        """Извлекает информацию о треках из имен файлов"""
        parsed_cols = df['original_string'].apply(lambda x: pd.Series(self.parse_filename(x)))
        parsed_cols.columns = ['ID', 'Title', 'Artist']
        return pd.concat([parsed_cols, df[['timestamp', 'series_number']].reset_index(drop=True)], axis=1)
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Очищает и форматирует данные"""
        # Исправление заголовков
        fix_mask = df['ID'].str.contains('__', na=False)
        if fix_mask.any():
            split_id = df.loc[fix_mask, 'ID'].str.split('__', n=1, expand=True)
            df.loc[fix_mask, 'ID'] = split_id[0]
            df.loc[fix_mask, 'Title'] = split_id[1].str.replace('-', ' ').str.title()
        
        # Очистка имен исполнителей
        df['Artist'] = df['Artist'].str.replace(config.ARTIST_CLEANUP_PATTERN, '', regex=True).str.strip()
        
        # Конвертация временных меток
        time_parts = df['timestamp'].astype(str).str.split(':', expand=True)
        time_parts = time_parts.apply(pd.to_numeric, errors='coerce').fillna(0)
        total_seconds = (time_parts[0] * 3600 + time_parts[1] * 60 + 
                        time_parts[2] + time_parts[3] / 100.0)
        df['duration_seconds'] = total_seconds.round().astype(int)
        
        # Форматирование ID и кодов библиотеки
        df['library_code'] = df['ID'].str.split('_').str[0]
        df['ID'] = df['ID'].str.upper()
        df['library_code'] = df['library_code'].str.upper()
        
        return df
    
    def process_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Обрабатывает дубликаты треков"""
        # Выбор нужных колонок
        final_cols = ['ID', 'library_code', 'Title', 'Artist', 'duration_seconds', 'series_number']
        df = df[final_cols]
        
        # Группировка уникальных треков
        unique_track_cols = ['ID', 'library_code', 'Title', 'Artist', 'series_number']
        aggregations = {'duration_seconds': 'sum'}
        
        deduped_df = df.groupby(unique_track_cols, as_index=False).agg(aggregations)
        
        # Подсчет повторений
        counts = df.groupby(unique_track_cols).size().reset_index(name='repeat_count')
        return pd.merge(deduped_df, counts, on=unique_track_cols)
    
    def filter_tracks(self, df: pd.DataFrame) -> pd.DataFrame:
        """Фильтрует треки по длительности и названию"""
        duration_mask = df['duration_seconds'] >= config.MINIMUM_DURATION
        title_pattern = '|'.join(config.EXCLUDED_TITLES)
        title_mask = ~df['Title'].str.contains(title_pattern, case=False, na=False)
        
        return df[duration_mask & title_mask].copy()
    
    def format_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """Форматирует данные для вывода"""
        df['duration_seconds'] = df['duration_seconds'].astype(str) + ' сек'
        df['Concatenated'] = df.apply(
            lambda row: f"{row['ID']}__{row['Title']}__{row['Artist']}", axis=1
        )
        df[''] = ''  # Добавляем пустую колонку
        return df[config.OUTPUT_COLUMNS]
    
    def save_output(self, df: pd.DataFrame, output_path: str) -> None:
        """Сохраняет результат в CSV файл"""
        df.to_csv(
            output_path,
            index=False,
            sep=config.CSV_SEPARATOR,
            encoding=config.CSV_ENCODING
        )
    
    def process_file(self, input_path: str, output_path: str) -> None:
        """Обрабатывает один файл"""
        try:
            self.logger.info(f"Начало обработки файла: {input_path}")
            
            df = self.read_input(input_path)
            initial_rows = len(df)
            
            processed_df = (df
                          .pipe(self.parse_tracks)
                          .pipe(self.clean_data)
                          .pipe(self.process_duplicates)
                          .pipe(self.filter_tracks)
                          .pipe(self.format_output))
            
            self.save_output(processed_df, output_path)
            
            self.logger.info(
                f"Обработан: {os.path.basename(input_path)} → {os.path.basename(output_path)} | "
                f"Удалено {initial_rows - len(processed_df)} треков по фильтру."
            )
            
        except FileNotFoundError:
            self.logger.error(f"Ошибка: файл не найден {input_path}")
        except Exception as e:
            self.logger.error(f"Ошибка при обработке {input_path}: {e}")
