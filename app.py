# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from contextlib import asynccontextmanager

from backend.instances import USER_MANAGER, CHAT_MANAGER, UUID_INDEX, DIRECT_CHAT_INDEX_MANAGER
from backend.routes import user_routes, chat_routes, websocket

# Paths used across the app
APP_ROOT = Path(__file__).resolve().parent
MEDIA_DIR = APP_ROOT / "media"
AVATAR_DIR = MEDIA_DIR / "avatars"
CHAT_COVER_DIR = MEDIA_DIR / "covers"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- One-time startup tasks ---
    # Ensure media folders exist
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    CHAT_COVER_DIR.mkdir(parents=True, exist_ok=True)

    # (Optional) print for sanity while developing
    print(f"[startup] MEDIA_DIR: {MEDIA_DIR}")
    print(f"[startup] AVATAR_DIR: {AVATAR_DIR}")
    print(f"[startup] CHAT_COVER_DIR: {CHAT_COVER_DIR}")

    # Your existing DB/bootstrap logic (kept intact)
    if not os.path.exists("user_manager.pkl"):
        print("Creating user_manager.pkl...")
        USER_MANAGER.save()
    if not os.path.exists("chat_manager.pkl"):
        print("Creating chat_manager.pkl...")
        CHAT_MANAGER.save_chat_database()
    if not os.path.exists(UUID_INDEX.path):
        UUID_INDEX.save()
    UUID_INDEX.load()

    if not os.path.exists("direct_index.pkl"):
        print("Building direct_index.pkl from existing chats...")
        def iter_chats():
            for chat in CHAT_MANAGER.iterate_all():
                yield chat
        DIRECT_CHAT_INDEX_MANAGER.rebuild_from_chats(iter_chats())

    # Hand off control to the application
    yield

    # --- Graceful shutdown tasks ---
    print("Saving all AVL trees before shutdown...")
    USER_MANAGER.save()
    CHAT_MANAGER.save_chat_database()
    UUID_INDEX.save()
    print("Data saved.")

app = FastAPI(title="Chat App", lifespan=lifespan)

# CORS for Vite dev (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve /media/* from ./media
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Expose media directories to routes (used by upload endpoints)
app.state.MEDIA_DIR = MEDIA_DIR
app.state.CHAT_COVER_DIR = CHAT_COVER_DIR
app.state.AVATAR_DIR = AVATAR_DIR

# Routers
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(chat_routes.router, prefix="/chats", tags=["Chats"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
