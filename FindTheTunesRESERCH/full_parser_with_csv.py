#!/usr/bin/env python3
"""
Полный парсер с автоматическим обновлением CSV файла
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import csv
from datetime import datetime
import conf
import logging
import subprocess
import sys
import os

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

def update_csv_with_results(results, input_csv=conf.INPUT_CSV, output_csv=None):
    """Обновляет CSV файл с текущими результатами"""
    
    if output_csv is None:
        base, ext = os.path.splitext(input_csv)
        output_csv = f"{base}_results{ext}"
    
    # Создаем словарь результатов для быстрого поиска
    results_dict = {}
    for track in results:
        key = f"{track.get('artist', '')}_{track.get('title', '')}"
        if track.get('found'):
            results_dict[key] = 'FindTheTune'
        elif track.get('status') == 'not_found':
            results_dict[key] = 'NIL'
        elif track.get('status') == 'error':
            results_dict[key] = 'ERROR'
        else:
            results_dict[key] = ''
    
    # Читаем исходный CSV и добавляем результаты
    rows_with_results = []
    
    with open(input_csv, 'r', encoding='utf-8') as f:
        sample = f.read(1024)
        f.seek(0)
        delimiter = ';' if ';' in sample else ','
        
        reader = csv.DictReader(f, delimiter=delimiter)
        fieldnames = reader.fieldnames + ['FindStatus']
        
        for row in reader:
            artist = row.get('Artist', '').strip()
            title = row.get('Title', '').strip()
            key = f"{artist}_{title}"
            
            # Добавляем результат поиска
            row['FindStatus'] = results_dict.get(key, '')
            rows_with_results.append(row)
    
    # Записываем новый CSV файл
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows_with_results)
    
    return True

def full_parser_with_csv():
    """Полный парсер с автоматическим обновлением CSV"""
    
    # Настройка браузера (БЕЗ headless режима)
    options = Options()
    options.add_argument(f'--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Создание драйвера
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 30)
    
    try:
        # Переход на страницу входа
        logger.info(f"Открываю страницу {conf.LOGIN_URL}")
        driver.get(conf.LOGIN_URL)
        
        print("\n" + "="*60)
        print("ПОЛНЫЙ ПАРСЕР С ОБНОВЛЕНИЕМ CSV")
        print("="*60)
        print("\n1. Войдите в свой аккаунт вручную в открывшемся браузере")
        print("2. После успешного входа нажмите Enter в этом терминале")
        print("\n" + "="*60)
        
        input("\nНажмите Enter после успешной авторизации...")
        
        # Проверка авторизации
        current_url = driver.current_url
        logger.info(f"Текущий URL после авторизации: {current_url}")
        
        print("\n✅ Авторизация подтверждена. Начинаю поиск всех треков...")
        print("📝 CSV файл будет обновляться каждые 20 треков")
        
        # Загрузка треков из CSV
        tracks = []
        with open(conf.INPUT_CSV, 'r', encoding='utf-8') as file:
            sample = file.read(1024)
            file.seek(0)
            delimiter = ';' if ';' in sample else ','
            
            reader = csv.DictReader(file, delimiter=delimiter)
            for row in reader:
                tracks.append({
                    'title': row.get('Title', '').strip(),
                    'artist': row.get('Artist', '').strip(),
                    'status': 'pending',
                    'found': False
                })
        
        logger.info(f"Загружено {len(tracks)} треков для поиска")
        
        # Результаты поиска
        results = []
        
        # Поиск каждого трека
        for i, track in enumerate(tracks, 1):
            if not track['title'] or not track['artist']:
                continue
                
            print(f"\n[{i}/{len(tracks)}] Поиск: {track['artist']} - {track['title']}", end=' ')
            
            try:
                # Сохраняем текущий URL перед поиском
                before_search_url = driver.current_url
                
                # Поиск поля поиска на странице
                search_field = None
                
                # Попытка найти поле поиска разными способами
                selectors = [
                    "input[type='search']",
                    "input[placeholder*='Search']",
                    "input[placeholder*='search']",
                    "input[name*='search']",
                    "input[id*='search']",
                    "input.search",
                    "#search",
                    "input[type='text']"
                ]
                
                for selector in selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed() and elem.is_enabled():
                                search_field = elem
                                break
                        if search_field:
                            break
                    except:
                        continue
                
                if not search_field:
                    logger.warning(f"Не найдено поле поиска для трека {i}")
                    track['status'] = 'error'
                    track['error'] = 'Поле поиска не найдено'
                    results.append(track)
                    print("⚠️ ОШИБКА")
                    continue
                
                # Очистка поля поиска - используем JavaScript для надежности
                try:
                    driver.execute_script("arguments[0].value = '';", search_field)
                    time.sleep(0.2)
                except:
                    pass
                
                search_field.click()
                time.sleep(0.1)
                search_field.send_keys(Keys.CONTROL + "a")
                time.sleep(0.1)
                search_field.send_keys(Keys.BACKSPACE)
                time.sleep(0.2)
                search_field.clear()
                time.sleep(0.2)
                
                # Финальная проверка и очистка
                current_value = search_field.get_attribute('value')
                if current_value:
                    for _ in range(len(current_value) + 10):
                        search_field.send_keys(Keys.BACKSPACE)
                    time.sleep(0.2)
                
                # Ввод запроса
                search_query = f"{track['artist']} {track['title']}"
                search_field.send_keys(search_query)
                time.sleep(0.3)
                
                # Отправка запроса
                search_field.send_keys(Keys.RETURN)
                
                # Ждем загрузку результатов
                results_loaded = False
                max_wait_time = 10
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    current_url = driver.current_url
                    if current_url != before_search_url:
                        results_loaded = True
                        time.sleep(2)
                        break
                    
                    try:
                        body_text = driver.find_element(By.TAG_NAME, "body").text
                        if any(keyword in body_text.lower() for keyword in ['results', 'found', 'tracks', 'no results', 'not found']):
                            results_loaded = True
                            time.sleep(1)
                            break
                    except:
                        pass
                    
                    time.sleep(0.5)
                
                # Анализ результатов
                page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                
                track['page_url'] = driver.current_url
                track['search_query'] = search_query
                
                # Проверяем различные индикаторы результатов
                found_indicators = [
                    'result' in page_text and 'no result' not in page_text,
                    'found' in page_text and 'not found' not in page_text,
                    'track' in page_text,
                    track['title'].lower() in page_text,
                    track['artist'].lower() in page_text
                ]
                
                not_found_indicators = [
                    'no results' in page_text,
                    'not found' in page_text,
                    '0 results' in page_text,
                    'nothing found' in page_text,
                    'no tracks' in page_text
                ]
                
                # Попытка найти конкретные элементы результатов
                result_elements = []
                result_selectors = [
                    ".result", ".track", ".song", 
                    "[class*='result']", "[class*='track']", "[class*='song']",
                    ".item", ".list-item", "tr", "li"
                ]
                
                for selector in result_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            visible_elements = [e for e in elements if e.is_displayed() and e.text.strip()]
                            if visible_elements:
                                result_elements.extend(visible_elements[:5])
                                break
                    except:
                        continue
                
                # Определение статуса
                if any(not_found_indicators):
                    track['found'] = False
                    track['status'] = 'not_found'
                    print("❌ NIL")
                elif result_elements or any(found_indicators):
                    track['found'] = True
                    track['status'] = 'found'
                    track['matches_count'] = len(result_elements)
                    print("✅ FindTheTune")
                else:
                    track['status'] = 'unknown'
                    print("❓")
                
                results.append(track)
                
                # Возврат на исходную страницу для следующего поиска
                if i < len(tracks):
                    driver.get(before_search_url)
                    time.sleep(1)
                
                # Сохранение промежуточных результатов и обновление CSV каждые 20 треков
                if i % 20 == 0:
                    intermediate_json_path = os.path.join(BASE_DIR, 'intermediate_full_results.json')
                    save_results(results, intermediate_json_path)
                    update_csv_with_results(results)
                    print(f"\n💾 Промежуточные результаты сохранены и CSV обновлен ({i} треков обработано)")
                    
            except Exception as e:
                logger.error(f"Ошибка при поиске трека {track['artist']} - {track['title']}: {e}")
                track['status'] = 'error'
                track['error'] = str(e)
                results.append(track)
                print("⚠️ ОШИБКА")
        
        # Сохранение финальных результатов
        final_json_path = os.path.join(BASE_DIR, 'full_search_results.json')
        save_results(results, final_json_path)
        update_csv_with_results(results)
        
        # Вывод статистики
        print("\n" + "="*60)
        print("СТАТИСТИКА ПОЛНОГО ПОИСКА:")
        print("="*60)
        found_count = sum(1 for r in results if r.get('found'))
        not_found_count = sum(1 for r in results if r.get('status') == 'not_found')
        unknown_count = sum(1 for r in results if r.get('status') == 'unknown')
        error_count = sum(1 for r in results if r.get('status') == 'error')
        
        print(f"✅ FindTheTune: {found_count} ({found_count/len(results)*100:.1f}%)")
        print(f"❌ NIL: {not_found_count} ({not_found_count/len(results)*100:.1f}%)")
        print(f"❓ Неопределенные: {unknown_count}")
        print(f"⚠️ Ошибки: {error_count}")
        print(f"📊 Всего обработано: {len(results)}")
        print("="*60)
        
        print(f"\n📁 Результаты сохранены в full_search_results.json")
        print(f"📋 CSV файл обновлен: serch_list_with_results.csv")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        raise
    
    finally:
        print("\nПарсер завершен. Браузер закроется через 5 секунд...")
        time.sleep(5)
        driver.quit()

def save_results(results, filename):
    """Сохранение результатов в JSON"""
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

if __name__ == "__main__":
    full_parser_with_csv()
