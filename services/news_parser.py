import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Optional, Tuple
import re
from urllib.parse import urljoin, urlparse
import asyncio
from dateutil import parser as date_parser

from app.schemas.parser import ParsedNews, ParsedNewsImage

class TPGKNewsParser:
    """Парсер новостей с сайта ТПГК (https://tpgk70.gosuslugi.ru/)"""
    
    def __init__(self):
        self.base_url = "https://tpgk70.gosuslugi.ru"
        self.news_url = f"{self.base_url}/novosti"
        self.timeout = 30
        self.max_retries = 3
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """Загружает HTML страницы"""
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.text
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        print(f"Failed to fetch {url}: {e}")
                        return None
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    def parse_news_list(self, html: str) -> List[Tuple[str, str, str]]:
        """
        Парсит список новостей.
        Возвращает список кортежей (url, заголовок, дата)
        """
        soup = BeautifulSoup(html, 'lxml')
        news_items = []
        
        # Адаптируем селекторы под структуру сайта на gosuslugi.ru
        # Обычно новости на таких сайтах имеют структуру:
        articles = soup.select('article.news-item, div.news-card, a.news-link')
        
        if not articles:
            # Пробуем другие селекторы
            articles = soup.select('div[class*="news"] a[href*="novosti"], a[href*="news"]')
        
        for article in articles:
            # Извлекаем URL
            if article.name == 'a':
                url = article.get('href')
                title_elem = article
            else:
                url_elem = article.select_one('a[href]')
                url = url_elem.get('href') if url_elem else None
                title_elem = article.select_one('h3, h4, .title, .news-title') or article
            
            if not url:
                continue
            
            # Формируем полный URL
            full_url = urljoin(self.base_url, url)
            
            # Извлекаем заголовок
            title = title_elem.get_text(strip=True)
            if not title:
                continue
            
            # Извлекаем дату
            date_elem = article.select_one('time, .date, .news-date, [datetime]')
            date_str = None
            if date_elem:
                if date_elem.get('datetime'):
                    date_str = date_elem.get('datetime')
                else:
                    date_str = date_elem.get_text(strip=True)
            
            news_items.append((full_url, title, date_str))
        
        return news_items
    
    def parse_single_news(self, html: str, url: str) -> Optional[ParsedNews]:
        """
        Парсит одну страницу новости
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Заголовок
        title_elem = soup.select_one('h1, .news-title, .article-title')
        if not title_elem:
            return None
        title = title_elem.get_text(strip=True)
        
        # Дата
        date_elem = soup.select_one('time, .news-date, .article-date, [datetime]')
        date = datetime.now()
        if date_elem:
            date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
            try:
                date = date_parser.parse(date_str)
            except:
                pass
        
        # Контент
        content_elem = soup.select_one('article, .news-content, .article-content, .content')
        if not content_elem:
            content_elem = soup.body
        
        # Очищаем контент
        for script in content_elem.select('script, style, nav, header, footer'):
            script.decompose()
        
        # Изображения
        images = []
        for i, img in enumerate(content_elem.select('img')):
            img_url = img.get('src')
            if not img_url:
                continue
            
            # Делаем URL абсолютным
            img_url = urljoin(self.base_url, img_url)
            
            # Подпись к изображению
            caption = None
            figcaption = img.find_parent('figure')
            if figcaption:
                caption_elem = figcaption.select_one('figcaption')
                if caption_elem:
                    caption = caption_elem.get_text(strip=True)
            
            images.append(ParsedNewsImage(
                url=img_url,
                caption=caption,
                is_main=(i == 0)  # Первое изображение считаем главным
            ))
        
        # Формируем preview текст (первые 200 символов)
        text_content = content_elem.get_text(strip=True)
        preview_text = text_content[:200] + "..." if len(text_content) > 200 else text_content
        
        # Получаем HTML контент
        content_html = str(content_elem)
        
        return ParsedNews(
            title=title,
            date=date,
            content_html=content_html,
            preview_text=preview_text,
            source_url=url,
            images=images
        )
    
    async def parse_news(
        self,
        max_news: int = 10,
        days_back: int = 30
    ) -> List[ParsedNews]:
        """
        Основной метод парсинга новостей
        """
        print(f"Starting news parse from {self.news_url}")
        
        # Загружаем страницу со списком новостей
        html = await self.fetch_page(self.news_url)
        if not html:
            print("Failed to fetch news list")
            return []
        
        # Парсим список
        news_items = self.parse_news_list(html)
        print(f"Found {len(news_items)} news items")
        
        # Фильтруем по дате (последние days_back дней)
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        parsed_news = []
        for url, title, date_str in news_items[:max_news]:
            try:
                # Загружаем страницу новости
                news_html = await self.fetch_page(url)
                if not news_html:
                    continue
                
                # Парсим новость
                news = self.parse_single_news(news_html, url)
                if not news:
                    continue
                
                # Проверяем дату
                if news.date < cutoff_date:
                    continue
                
                parsed_news.append(news)
                print(f"Parsed: {news.title}")
                
                # Небольшая задержка между запросами
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error parsing {url}: {e}")
                continue
        
        print(f"Successfully parsed {len(parsed_news)} news items")
        return parsed_news
    
    async def check_for_updates(self, last_news_date: datetime) -> bool:
        """
        Проверяет, есть ли новые новости
        """
        html = await self.fetch_page(self.news_url)
        if not html:
            return False
        
        news_items = self.parse_news_list(html)
        if not news_items:
            return False
        
        # Берем первую (самую свежую) новость
        latest_url, _, date_str = news_items[0]
        
        # Загружаем её
        news_html = await self.fetch_page(latest_url)
        if not news_html:
            return False
        
        latest_news = self.parse_single_news(news_html, latest_url)
        if not latest_news:
            return False
        
        return latest_news.date > last_news_date


# Парсер для конкретного сайта (можно добавить специфичные селекторы)
class TPGKNewsParser(TPGKNewsParser):
    """Специализированный парсер для сайта ТПГК"""
    
    def parse_news_list(self, html: str) -> List[Tuple[str, str, str]]:
        """
        Переопределяем для конкретной структуры сайта ТПГК
        """
        soup = BeautifulSoup(html, 'lxml')
        news_items = []
        
        # На сайте gosuslugi.ru новости часто в таком формате
        cards = soup.select('.feed-card, .card, .news-card')
        
        for card in cards:
            # Ссылка
            link = card.select_one('a[href*="novosti"], a[href*="news"]')
            if not link:
                continue
            
            url = link.get('href')
            full_url = urljoin(self.base_url, url)
            
            # Заголовок
            title_elem = card.select_one('.card-title, h3, .title')
            title = title_elem.get_text(strip=True) if title_elem else link.get_text(strip=True)
            
            # Дата
            date_elem = card.select_one('.card-date, time, .date')
            date_str = date_elem.get_text(strip=True) if date_elem else None
            
            news_items.append((full_url, title, date_str))
        
        return news_items