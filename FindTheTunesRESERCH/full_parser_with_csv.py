#!/usr/bin/env python3
"""
Полный парсер с автоматическим обновлением CSV файла
"""
import os
import sys
import json
import csv
import time
import logging
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from webdriver_manager.chrome import ChromeDriverManager

import conf

# Определяем базовую директорию, где лежит скрипт
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Настройка логирования
LOG_FILE_PATH = os.path.join(BASE_DIR, 'full_parser_with_csv.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def initialize_driver():
    """Настраивает и инициализирует WebDriver."""
    logger.info("Инициализация WebDriver...")
    options = Options()
    if conf.HEADLESS_MODE:
        options.add_argument('--headless')
    options.add_argument(f'--window-size={conf.WINDOW_SIZE[0]},{conf.WINDOW_SIZE[1]}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, conf.TIMEOUT)
    logger.info("WebDriver инициализирован.")
    return driver, wait


def login(driver, wait):
    """Выполняет автоматический вход на сайт."""
    logger.info(f"Открываю страницу для входа: {conf.LOGIN_URL}")
    driver.get(conf.LOGIN_URL)
    print("\nАвтоматический вход...")

    try:
        user_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#user")))
        user_field.send_keys(conf.USERNAME)
        logger.info("Введен логин")

        password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#pass")))
        password_field.send_keys(conf.PASSWORD)
        logger.info("Введен пароль")

        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#login-submit")))
        login_button.click()
        logger.info("Нажата кнопка входа")

        # Ожидаем изменения URL как подтверждение входа
        wait.until(EC.url_changes(conf.LOGIN_URL))
        logger.info(f"Авторизация прошла успешно. Текущий URL: {driver.current_url}")
        print("✅ Авторизация подтверждена.")
        return True

    except TimeoutException as e:
        logger.error(f"Ошибка автоматической авторизации (таймаут): {e}")
        print("❌ Не удалось автоматически войти в систему. Проверьте селекторы и учетные данные в conf.py")
        return False


def load_tracks(input_csv_path):
    """Загружает треки из CSV файла."""
    logger.info(f"Загрузка треков из {input_csv_path}")
    tracks = []
    with open(input_csv_path, 'r', encoding='utf-8') as file:
        # Определение диалекта CSV
        try:
            sample = file.read(2048)
            file.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=';,')
        except csv.Error:
            dialect = 'excel' # fallback

        reader = csv.DictReader(file, dialect=dialect)
        for row in reader:
            tracks.append({
                'title': row.get('Title', '').strip(),
                'artist': row.get('Artist', '').strip(),
                'status': 'pending',
                'found': False
            })
    logger.info(f"Загружено {len(tracks)} треков для поиска.")
    return tracks


def search_and_analyze_track(driver, wait, track):
    """Ищет один трек и анализирует результат."""
    if not track['title'] or not track['artist']:
        track['status'] = 'error'
        track['error'] = 'Missing title or artist'
        return track

    try:
        # Принудительный переход на страницу поиска для каждого трека
        driver.get(conf.SEARCH_URL)
        # Ждем, пока оверлей загрузки не исчезнет
        wait.until(EC.invisibility_of_element_located((By.ID, "loader_overlay")))

        # 1. Используем точный селектор для поиска поля и кнопки
        try:
            search_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#search-q-track-elastic")))
            search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#search-track-btn-elastic")))
        except TimeoutException:
            raise Exception("Не удалось найти поле или кнопку поиска на странице. Проверьте селекторы.")

        # 2. Очистка поля и ввод запроса
        try:
            # Кликаем на поле, чтобы активировать JS-события
            search_field.click()
            time.sleep(0.1)
            
            # Самый надежный способ: эмуляция нажатия клавиш
            search_field.send_keys(Keys.CONTROL + "a")
            search_field.send_keys(Keys.BACKSPACE)
            time.sleep(0.1)

            # Дополнительные методы очистки как запасной вариант
            if search_field.get_attribute('value') != '':
                driver.execute_script("arguments[0].value = '';", search_field)
                search_field.clear()

        except Exception as clear_error:
            logger.warning(f"Не удалось полностью очистить поле поиска: {clear_error}")

        search_query = f"{track['artist']} {track['title']}"
        search_field.send_keys(search_query)
        
        # 3. Клик по кнопке поиска
        search_button.click()

        # 3. Ожидание результатов
        # Ждем либо изменения URL, либо появления индикатора "нет результатов"
        wait.until(
            EC.any_of(
                EC.url_changes(conf.SEARCH_URL),
                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'no results')]")),
                EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'not found')]"))
            )
        )
        time.sleep(conf.DELAY_BETWEEN_REQUESTS) # Задержка между запросами

        # 4. Анализ результатов
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        track['page_url'] = driver.current_url
        track['search_query'] = search_query

        not_found_indicators = ['no results', 'not found', '0 results', 'nothing found']
        
        if any(indicator in page_text for indicator in not_found_indicators):
            track['found'] = False
            track['status'] = 'not_found'
            print("❌ NIL")
        else:
            # Упрощенная проверка на наличие названия трека или артиста
            if track['title'].lower() in page_text or track['artist'].lower() in page_text:
                track['found'] = True
                track['status'] = 'found'
                print("✅ FindTheTune")
            else:
                track['status'] = 'unknown'
                print("❓")

    except Exception as e:
        logger.error(f"Ошибка при поиске трека {track['artist']} - {track['title']}: {e}")
        track['status'] = 'error'
        track['error'] = str(e)
        print("⚠️ ОШИБКА")
    
    return track


def save_results(results, filename):
    """Сохранение результатов в JSON."""
    output = {
        'search_date': datetime.now().isoformat(),
        'total_tracks': len(results),
        'found': sum(1 for r in results if r.get('found')),
        'not_found': sum(1 for r in results if r.get('status') == 'not_found'),
        'unknown': sum(1 for r in results if r.get('status') == 'unknown'),
        'errors': sum(1 for r in results if r.get('status') == 'error'),
        'tracks': results
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"Результаты сохранены в {filename}")


def update_csv_with_results(results, input_csv=conf.INPUT_CSV, output_csv=None):
    """Обновляет CSV файл с текущими результатами."""
    if output_csv is None:
        base, ext = os.path.splitext(input_csv)
        output_csv = f"{base}_results{ext}"

    results_dict = {f"{t.get('artist', '')}_{t.get('title', '')}": t for t in results}
    
    rows_with_results = []
    fieldnames = []

    with open(input_csv, 'r', encoding='utf-8') as f:
        try:
            sample = f.read(2048)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters=';,')
        except csv.Error:
            dialect = 'excel'  # fallback

        reader = csv.DictReader(f, dialect=dialect)
        fieldnames = reader.fieldnames + ['FindStatus']
        for row in reader:
            key = f"{row.get('Artist', '').strip()}_{row.get('Title', '').strip()}"
            result_track = results_dict.get(key)
            if result_track:
                if result_track.get('found'):
                    row['FindStatus'] = 'FindTheTune'
                elif result_track.get('status') == 'not_found':
                    row['FindStatus'] = 'NIL'
                elif result_track.get('status') == 'error':
                    row['FindStatus'] = 'ERROR'
            else:
                row['FindStatus'] = ''
            rows_with_results.append(row)

    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(rows_with_results)
    logger.info(f"CSV файл обновлен: {output_csv}")
    return output_csv


def run_parser():
    """Основная функция, запускающая парсер."""
    print("=" * 60)
    print("ПОЛНЫЙ ПАРСЕР С ОБНОВЛЕНИЕМ CSV")
    print("=" * 60)

    driver, wait = initialize_driver()
    
    try:
        if not login(driver, wait):
            return # Завершаем работу, если логин не удался

        tracks = load_tracks(conf.INPUT_CSV)
        if not tracks:
            print("Не найдено треков для обработки.")
            return
            
        print(f"Начинаю поиск {len(tracks)} треков...")
        print("📝 CSV файл будет обновляться каждые 20 треков")
        
        results = []

        for i, track in enumerate(tracks, 1):
            print(f"\n[{i}/{len(tracks)}] Поиск: {track['artist']} - {track['title']}", end=' ')
            
            processed_track = search_and_analyze_track(driver, wait, track)
            results.append(processed_track)
            
            # Периодическое сохранение результатов
            if i % 20 == 0:
                save_results(results, 'intermediate_results.json')
                update_csv_with_results(results)
                print(f"\n💾 Промежуточные результаты сохранены и CSV обновлен.")

        # Финальное сохранение
        final_json_path = os.path.join(BASE_DIR, 'full_search_results.json')
        save_results(results, final_json_path)
        final_csv_path = update_csv_with_results(results)

        # Статистика
        print("\n" + "=" * 60)
        print("СТАТИСТИКА ПОЛНОГО ПОИСКА:")
        found = sum(1 for r in results if r.get('found'))
        not_found = sum(1 for r in results if r.get('status') == 'not_found')
        unknown = sum(1 for r in results if r.get('status') == 'unknown')
        errors = sum(1 for r in results if r.get('status') == 'error')
        total = len(results)
        print(f"✅ FindTheTune: {found} ({found/total*100:.1f}%)" if total else "")
        print(f"❌ NIL: {not_found} ({not_found/total*100:.1f}%)" if total else "")
        print(f"❓ Неопределенные: {unknown}")
        print(f"⚠️ Ошибки: {errors}")
        print(f"📊 Всего обработано: {total}")
        print("=" * 60)
        print(f"\n📁 Результаты сохранены в {final_json_path}")
        print(f"📋 CSV файл обновлен: {final_csv_path}")

    except Exception as e:
        logger.critical(f"Произошла критическая ошибка: {e}", exc_info=True)
    
    finally:
        print("\nПарсер завершен. Браузер закроется через 5 секунд...")
        time.sleep(5)
        if 'driver' in locals() and driver:
            driver.quit()


if __name__ == "__main__":
    run_parser()