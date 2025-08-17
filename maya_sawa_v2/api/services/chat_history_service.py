import json
import os
import time
from typing import Any, Dict, List, Optional

import redis


class ChatHistoryService:
    """Redis-backed chat history per session.

    Key schema:
      - chat:session:{session_id} -> Redis List of JSON messages
      - chat:meta:{session_id} -> Redis Hash for metadata (created_at, user_id, etc.)
    Message format:
      {"role": "user|assistant|system", "content": str, "ts": int}
    """

    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: Optional[int] = None) -> None:
        self.redis_url = redis_url or os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL")
        if not self.redis_url:
            raise RuntimeError("REDIS_URL not configured for ChatHistoryService")
        self.client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        # default 7 days
        self.ttl_seconds = ttl_seconds or int(os.getenv("CHAT_HISTORY_TTL_SECONDS", "604800"))

    def _key_list(self, session_id: str) -> str:
        return f"chat:session:{session_id}"

    def _key_meta(self, session_id: str) -> str:
        return f"chat:meta:{session_id}"

    def append_message(self, session_id: str, role: str, content: str, extra: Optional[Dict[str, Any]] = None) -> None:
        payload: Dict[str, Any] = {"role": role, "content": content, "ts": int(time.time())}
        if extra:
            payload.update(extra)
        pipe = self.client.pipeline()
        pipe.rpush(self._key_list(session_id), json.dumps(payload))
        # update expiry on list and meta
        pipe.expire(self._key_list(session_id), self.ttl_seconds)
        pipe.hset(self._key_meta(session_id), mapping={"updated_at": str(payload["ts"])})
        pipe.expire(self._key_meta(session_id), self.ttl_seconds)
        pipe.execute()

    def set_meta(self, session_id: str, mapping: Dict[str, Any]) -> None:
        self.client.hset(self._key_meta(session_id), mapping=mapping)
        self.client.expire(self._key_meta(session_id), self.ttl_seconds)

    def get_history(self, session_id: str, start: int = 0, end: int = -1) -> List[Dict[str, Any]]:
        raw = self.client.lrange(self._key_list(session_id), start, end)
        out: List[Dict[str, Any]] = []
        for s in raw:
            try:
                out.append(json.loads(s))
            except Exception:
                continue
        return out

    def get_meta(self, session_id: str) -> Dict[str, Any]:
        return self.client.hgetall(self._key_meta(session_id))

    def clear(self, session_id: str) -> None:
        pipe = self.client.pipeline()
        pipe.delete(self._key_list(session_id))
        pipe.delete(self._key_meta(session_id))
        pipe.execute()


