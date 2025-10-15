"""
Модуль для форматирования вывода списка файлов и ссылок.
"""
import os
from typing import List, Dict

def format_report(folder_info: Dict, files: List[Dict]) -> str:
    """
    Форматирует итоговый отчет в виде строки.

    Args:
        folder_info (Dict): Информация о главной папке.
        files (List[Dict]): Список файлов с их данными.

    Returns:
        str: Готовый текстовый отчет.
    """
    report_lines = []

    # Блок с информацией о всей папке
    report_lines.append("=== ВЕСЬ РЕПОРТАЖ И РАСШИФРОВКИ ===\n")
    report_lines.append(folder_info.get('name', 'Имя папки не найдено'))
    report_lines.append(folder_info.get('public_url', 'Ссылка на папку не найдена') + "\n")
    
    # Блок с отдельными файлами
    report_lines.append("=== ОТДЕЛЬНЫЕ ИНТЕРВЬЮ ===\n")
    
    if not files:
        report_lines.append("Нет файлов для отображения.\n")
    else:
        for file in files:
            name_no_ext = os.path.splitext(file['name'])[0]
            link = file.get("public_url", "Ссылка не создана")
            report_lines.append(f"{name_no_ext}\n{link}\n")

    report_lines.append("\n=== КОНЕЦ СПИСКА ===")
    
    return "\n".join(report_lines)
