import os
import pickle
import threading
from typing import Dict, Optional

class UUIDManager:
    """
    Username → UUID index with pickle persistence.

    - Case-sensitive by default: 'Justin' and 'justin' are different keys.
    - Atomic save: temp file + os.replace to avoid corruption.
    - Thread-safe via an RLock.
    """

    def __init__(self, path: str = "username_index.pkl", autosave: bool = False):
        self.path = path
        self.autosave = autosave
        self.uuids: Dict[str, str] = {}
        self._lock = threading.RLock()

    # ---------- internal helpers ----------
    def _key(self, username: str) -> str:
        if username is None:
            raise KeyError("username is None")
        # If you want to keep *exact* spacing too, remove .strip()
        return username.strip()

    # ---------- persistence ----------
    def load(self) -> None:
        """Load the index from disk (or create it if missing)."""
        with self._lock:
            if os.path.exists(self.path):
                with open(self.path, "rb") as f:
                    data = pickle.load(f)
                self.uuids = dict(data) if isinstance(data, dict) else {}
            else:
                self.uuids = {}
                self.save()  # create empty file the first time

    def save(self) -> None:
        """Atomically save the index to disk."""
        with self._lock:
            tmp = self.path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(self.uuids, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp, self.path)

    # ---------- dict-like interface ----------
    def __getitem__(self, username: str) -> str:
        return self.uuids[self._key(username)]

    def __setitem__(self, username: str, user_id: str) -> None:
        if user_id is None:
            raise ValueError("user_id cannot be None")
        with self._lock:
            self.uuids[self._key(username)] = user_id
            if self.autosave:
                self.save()

    def __delitem__(self, username: str) -> None:
        with self._lock:
            del self.uuids[self._key(username)]
            if self.autosave:
                self.save()

    def __contains__(self, username: str) -> bool:
        return self._key(username) in self.uuids

    def get(self, username: str, default: Optional[str] = None) -> Optional[str]:
        return self.uuids.get(self._key(username), default)

    def clear(self) -> None:
        with self._lock:
            self.uuids.clear()
            if self.autosave:
                self.save()

    def rename(self, old_username: str, new_username: str) -> None:
        """
        Change the username key while keeping the same UUID.
        Case-sensitive uniqueness: 'Justin' and 'justin' are distinct keys.
        """
        with self._lock:
            old_k = self._key(old_username)
            new_k = self._key(new_username)
            if new_k in self.uuids and new_k != old_k:
                raise ValueError("Username is already taken.")
            user_id = self.uuids.pop(old_k)  # KeyError if old missing
            self.uuids[new_k] = user_id
            if self.autosave:
                self.save()
