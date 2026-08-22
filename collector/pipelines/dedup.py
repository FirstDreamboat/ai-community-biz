"""URL + MinHash 双重去重（对应 DLD 3.3）。"""
import hashlib
import re

import redis

from collector import settings

_HASH_FUNCS = [hashlib.md5, hashlib.sha1, hashlib.sha256, hashlib.sha384]
_MINHASH_PERMS = 8  # 排列数量


def normalize_url(url: str) -> str:
    """去除 URL 中的追踪参数。"""
    url = re.sub(r"[?&](utm_[^=&]+|from|source|ref)=[^&]*", "", url)
    url = url.rstrip("?&")
    return url


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def _shingles(text: str, k: int = 5) -> set[str]:
    text = re.sub(r"\s+", "", text)
    if len(text) <= k:
        return {text} if text else set()
    return {text[i:i + k] for i in range(len(text) - k + 1)}


def minhash(text: str) -> str:
    """MinHash 指纹（简化实现，返回 8 个排列哈希拼接）。"""
    shingles = _shingles(text)
    if not shingles:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    sig = []
    for seed in range(_MINHASH_PERMS):
        mins = None
        for s in shingles:
            h = hashlib.sha256((str(seed) + s).encode("utf-8")).hexdigest()
            mins = h if mins is None else min(mins, h)
        sig.append(mins or "")
    return hashlib.sha256("".join(sig).encode("utf-8")).hexdigest()


class DedupFilter:
    """基于 Redis Set 的双重去重。"""

    KEY_URL = "dedup:url"
    KEY_CONTENT = "dedup:content"

    def __init__(self) -> None:
        auth = f":{settings.REDIS_PASSWORD}@" if settings.REDIS_PASSWORD else ""
        self._redis = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT,
            db=settings.REDIS_DB, password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
        )
        self.duplicated = 0

    def is_dup(self, url: str, content: str) -> bool:
        u = url_hash(url)
        if self._redis.sismember(self.KEY_URL, u):
            self.duplicated += 1
            return True
        c = minhash(content)
        if self._redis.sismember(self.KEY_CONTENT, c):
            self.duplicated += 1
            return True
        # 新内容入库
        pipe = self._redis.pipeline()
        pipe.sadd(self.KEY_URL, u)
        pipe.sadd(self.KEY_CONTENT, c)
        pipe.execute()
        return False
