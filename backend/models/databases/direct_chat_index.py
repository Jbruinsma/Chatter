import os, pickle, threading, tempfile
from typing import Optional, Tuple, Iterable

def _pair_key(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a < b else (b, a)

def _atomic_write(path: str, data: bytes) -> None:
    d = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile(dir=d, delete=False) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_name = tmp.name
    os.replace(tmp_name, path)

class DirectIndex:
    """
    O(1) lookups of a direct chat between two users.
    Persist with pickle; thread-safe for simple web workloads.
    """
    def __init__(self, file_path: str = "direct_index.pkl"):
        self._file_path = file_path
        self._by_pair: dict[Tuple[str, str], str] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._file_path):
            with open(self._file_path, "rb") as f:
                self._by_pair = pickle.load(f)

    def _save(self) -> None:
        data = pickle.dumps(self._by_pair, protocol=pickle.HIGHEST_PROTOCOL)
        _atomic_write(self._file_path, data)

    # --- public api ---
    def get(self, a: str, b: str) -> Optional[str]:
        with self._lock:
            return self._by_pair.get(_pair_key(a, b))

    def put(self, a: str, b: str, chat_id: str) -> None:
        with self._lock:
            self._by_pair[_pair_key(a, b)] = chat_id
            self._save()

    def remove(self, a: str, b: str) -> None:
        with self._lock:
            self._by_pair.pop(_pair_key(a, b), None)
            self._save()

    def rebuild_from_chats(self, chats: Iterable["Chat"]) -> None:
        """
        Rebuilds the index from all chats. Use at startup when file is missing/stale.
        """
        with self._lock:
            self._by_pair.clear()
            for chat in chats:
                # tolerate legacy: either explicit type=='direct' or exactly two participants
                p = getattr(chat, "participants", None)
                t = getattr(chat, "chat_type", None)
                if isinstance(p, set) and len(p) == 2 and (t == "direct" or t is None):
                    a, b = sorted(p)
                    self._by_pair[(a, b)] = chat.chat_id
            self._save()