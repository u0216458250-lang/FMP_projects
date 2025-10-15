"""
Модуль для взаимодействия с API Яндекс.Диска.
"""
import requests
import logging

class YandexDiskClient:
    """Клиент для работы с API Яндекс.Диска."""
    
    def __init__(self, token: str, base_url: str = "https://cloud-api.yandex.net/v1/disk/resources"):
        self.token = token
        self.base_url = base_url
        self.headers = {"Authorization": f"OAuth {self.token}"}
        self.logger = logging.getLogger(__name__)

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Отправляет запрос к API и обрабатывает базовые ошибки."""
        try:
            response = requests.request(method, url, headers=self.headers, timeout=20, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            self.logger.error(f"Ошибка API: {e.response.status_code} {e.response.text}")
            raise
        except requests.RequestException as e:
            self.logger.error(f"Ошибка сети при запросе к {url}: {e}")
            raise

    def list_items(self, path: str, fields: list = None, limit: int = 100) -> list:
        """Получает список элементов в указанной папке."""
        params = {
            "path": path,
            "fields": ",".join(fields) if fields else "_embedded.items.name,_embedded.items.public_url,_embedded.items.type",
            "limit": limit
        }
        try:
            response = self._request("GET", self.base_url, params=params)
            return response.json().get("_embedded", {}).get("items", [])
        except requests.HTTPError:
            # В случае ошибки возвращаем пустой список, чтобы не прерывать выполнение
            return []

    def publish(self, path: str) -> bool:
        """Публикует ресурс (файл или папку)."""
        url = f"{self.base_url}/publish"
        params = {"path": path}
        try:
            # Используем другой метод _request, т.к. 409 - не ошибка для нас
            response = requests.put(url, headers=self.headers, params=params, timeout=20)
            if response.status_code in [200, 202]:
                self.logger.info(f"Ресурс '{path}' успешно опубликован.")
                return True
            if response.status_code == 409: # Уже опубликован
                self.logger.info(f"Ресурс '{path}' уже был опубликован ранее.")
                return True
            
            # Если код другой, вызываем raise_for_status для логирования
            response.raise_for_status()
            
        except requests.RequestException as e:
            self.logger.error(f"Не удалось опубликовать '{path}': {e}")
        return False

    def get_resource_info(self, path: str, fields: list = None) -> dict:
        """Получает информацию о ресурсе (файле или папке)."""
        params = {
            "path": path,
            "fields": ",".join(fields) if fields else "name,public_url"
        }
        try:
            response = self._request("GET", self.base_url, params=params)
            return response.json()
        except requests.HTTPError:
            return {}
