"""
Главный скрипт для получения публичных ссылок на файлы из Яндекс.Диска.
"""
import logging
import time
import os

import config
from api_client import YandexDiskClient
from file_formatter import format_report

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def main():
    """Основная функция, координирующая процесс."""
    logger = logging.getLogger(__name__)
    logger.info(f"Начинаю обработку папки: {config.FOLDER_PATH}")

    client = YandexDiskClient(token=config.OAUTH_TOKEN, base_url=config.API_BASE_URL)

    # 1. Публикуем корневую папку, чтобы убедиться, что она доступна
    client.publish(config.FOLDER_PATH)

    # 2. Получаем список всех элементов в папке
    items = client.list_items(config.FOLDER_PATH)
    if not items:
        logger.warning("В папке нет файлов или не удалось получить список.")
        return

    # 3. Находим файлы, которые нужно опубликовать
    files_to_publish = [
        item for item in items
        if item.get("type") == "file"
        and os.path.splitext(item.get("name", ""))[1].lower() in config.ALLOWED_EXTENSIONS
        and not item.get("public_url")
    ]

    # 4. Публикуем найденные файлы
    if files_to_publish:
        logger.info(f"Найдено {len(files_to_publish)} файлов для публикации...")
        for item in files_to_publish:
            full_path = f"{config.FOLDER_PATH}/{item['name']}"
            client.publish(full_path)
        
        # Пауза, чтобы Яндекс.Диск успел сгенерировать ссылки
        logger.info("Ожидание 2 секунды для обновления ссылок на сервере...")
        time.sleep(2.0)
    else:
        logger.info("Все видеофайлы в папке уже опубликованы.")

    # 5. Получаем финальную информацию (папка + файлы)
    folder_info = client.get_resource_info(config.FOLDER_PATH)
    all_files = client.list_items(config.FOLDER_PATH)

    video_files = [
        item for item in all_files
        if item.get("type") == "file"
        and os.path.splitext(item.get("name", ""))[1].lower() in config.ALLOWED_EXTENSIONS
    ]

    # 6. Формируем и сохраняем отчет
    report = format_report(folder_info, video_files)
    print("\n" + "-"*20 + "\n" + report)

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.OUTPUT_FILE)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Результат успешно сохранен в файл: {output_path}")
    except IOError as e:
        logger.error(f"Не удалось записать файл '{output_path}': {e}")

if __name__ == "__main__":
    main()