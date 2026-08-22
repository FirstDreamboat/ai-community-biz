"""公告文本清洗（对应 DLD 3.2）。"""
import re


def clean_html(raw_html: str) -> str:
    """去除脚本/样式/标签，保留文本。"""
    text = re.sub(r"<script.*?</script>", "", raw_html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = re.sub(r"&[a-zA-Z]+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
