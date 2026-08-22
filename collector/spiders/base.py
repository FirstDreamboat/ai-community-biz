"""爬虫基类：统一管道接入、关键词过滤、UA 轮换。"""
import logging
from datetime import datetime
from urllib.parse import urljoin

import scrapy
from scrapy.crawler import Crawler
from scrapy.utils.project import get_project_settings

from collector import settings
from collector.pipelines.cleaner import clean_html
from collector.pipelines.db_pipeline import AnnouncementItem, DbPipeline

logger = logging.getLogger(__name__)


class BaseSpider(scrapy.Spider):
    """所有数据源爬虫的基类。"""

    name = "base"
    source_id: int | None = None
    allowed_keywords: list[str] = settings.DEFAULT_KEYWORDS
    category = "tender"

    def __init__(self, source_id: int | None = None, keywords: str | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if source_id:
            self.source_id = int(source_id)
        if keywords:
            self.allowed_keywords = [k.strip() for k in keywords.split(",") if k.strip()]

    @classmethod
    def from_crawler(cls, crawler: Crawler):
        spider = cls()
        spider.crawler = crawler
        return spider

    def _user_agent(self) -> str:
        import random

        return random.choice(settings.USER_AGENTS)

    def start_requests(self):
        raise NotImplementedError

    def _make_item(self, url: str, title: str, html: str,
                   publish_time: datetime | None = None) -> AnnouncementItem | None:
        """构建公告对象（含关键词过滤与清洗）。"""
        title = title.strip()
        if not title:
            return None
        content = clean_html(html)
        if not any(kw in (title + content) for kw in self.allowed_keywords):
            logger.debug("关键词未命中，跳过: %s", title)
            return None
        return AnnouncementItem(
            source_id=self.source_id or 0,
            source_url=url,
            title=title,
            content=content,
            raw_html=html,
            publish_time=publish_time,
            category=self.category,
        )

    def parse_detail(self, response):
        """默认详情页解析入口，子类可覆盖。"""
        title = response.css("title::text").get() or response.css("h1::text").get() or ""
        item = self._make_item(response.url, title, response.text)
        if item:
            pipeline = DbPipeline()
            pipeline.process_item(item)
