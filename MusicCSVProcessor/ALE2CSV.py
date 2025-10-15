#!/usr/bin/env python3
"""
Главный скрипт для обработки музыкальных CSV файлов.
Находит все CSV файлы в директории и обрабатывает их.
"""

import os
import glob
import logging
from processor import MusicFileProcessor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('processing.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """
    Основная функция скрипта.
    Находит все CSV файлы в директории (кроме уже обработанных) и обрабатывает их.
    """
    try:
        processor = MusicFileProcessor()
        
        # Получаем список файлов для обработки
        folder = os.path.dirname(os.path.abspath(__file__))
        csv_files = [
            f for f in glob.glob(os.path.join(folder, "*.csv"))
            if not f.endswith("_edit.csv")
        ]
        
        if not csv_files:
            logger.info("Нет файлов для обработки.")
            return
            
        logger.info(f"Найдено файлов для обработки: {len(csv_files)}")
        
        # Обрабатываем каждый файл
        for input_path in csv_files:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_edit{ext}"
            processor.process_file(input_path, output_path)
            
        logger.info("Обработка всех файлов завершена.")
            
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    main()