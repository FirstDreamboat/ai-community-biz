"""政府招投标平台爬虫（示例：中国政府采购网 ccgp.gov.cn）。"""
import logging
from urllib.parse import urljoin

import scrapy

from collector.spiders.base import BaseSpider

logger = logging.getLogger(__name__)


class GovTenderSpider(BaseSpider):
    """政府招投标公告采集（定向：老旧小区改造/城市更新关键词）。"""

    name = "gov_tender"
    category = "tender"

    def start_requests(self):
        base = "https://search.ccgp.gov.cn/bxsearch"
        yield scrapy.Request(
            url=base,
            method="POST",
            headers={"User-Agent": self._user_agent()},
            body=(
                "searchtype=1&page_index=1&bidSort=0&pinMu=0&bidType=1&"
                "displayZone=0&kwd=老旧小区改造"
            ).encode("utf-8"),
            callback=self.parse_list,
            dont_filter=False,
        )

    def parse_list(self, response):
        # 列表页：解析公告链接（选择器需按实际页面调整）
        links = response.css("ul.vT-srch-result-list-bid li a::attr(href)").getall()
        for href in links[:20]:
            url = urljoin(response.url, href)
            yield scrapy.Request(
                url=url,
                headers={"User-Agent": self._user_agent()},
                callback=self.parse_detail,
            )


class RegionalTenderSpider(BaseSpider):
    """省市公共资源交易中心爬虫（示例骨架）。"""

    name = "regional_tender"
    category = "tender"

    def start_requests(self):
        # 各省站点差异大，实际接入时在数据源配置中通过 base_url 注入
        start_urls = getattr(self, "start_urls", [])
        for url in start_urls:
            yield scrapy.Request(
                url=url,
                headers={"User-Agent": self._user_agent()},
                callback=self.parse_list,
            )

    def parse_list(self, response):
        links = response.css("a::attr(href)").re(r".*(zhaobiao|zbgg|cggg).*")
        for href in links[:20]:
            yield scrapy.Request(
                url=urljoin(response.url, href),
                headers={"User-Agent": self._user_agent()},
                callback=self.parse_detail,
            )
