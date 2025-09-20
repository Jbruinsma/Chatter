from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import socket
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Import the async database function needed during startup
from backend.database import create_db_and_tables

# Import managers and routes
from backend.routes import user_routes, chat_routes, websocket


# ---------- Directories ----------
APP_ROOT = Path(__file__).resolve().parent
MEDIA_DIR = APP_ROOT / "media"
AVATAR_DIR = MEDIA_DIR / "avatars"
CHAT_COVER_DIR = MEDIA_DIR / "covers"

# ---------- Config ----------
PORT = int(os.getenv("PORT", "8000"))
VITE_PORT = os.getenv("VITE_PORT", "5173")  # only used for logging text

# Dev-friendly: allow any http/https origin + optional port (works with credentials).
# Tighten this for production.
ALLOW_ORIGIN_REGEX = r"^https?://[^/]+(?::\d{2,5})?$"

load_dotenv()


def get_lan_ip(default: str = "127.0.0.1") -> str:
    """Best-effort LAN (or upstream) IP discovery for startup logs."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # No traffic is actually sent; this selects the right interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return default


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- One-time startup tasks ---
    print("Ensuring media directories exist...")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    CHAT_COVER_DIR.mkdir(parents=True, exist_ok=True)

    # Create database and tables using the imported async function
    print("Creating database and tables if they don't exist...")
    await create_db_and_tables()  # <-- The key change is here

    print(f"[startup] MEDIA_DIR: {MEDIA_DIR}")
    print(f"[startup] AVATAR_DIR: {AVATAR_DIR}")
    print(f"[startup] CHAT_COVER_DIR: {CHAT_COVER_DIR}")
    print("Startup complete. Application is ready.")

    yield

    # --- Graceful shutdown tasks can be added here if needed ---
    print("Application shutting down.")

app = FastAPI(title="Chat App", lifespan=lifespan)


# ---------- CORS ----------
# Allows your Vue app to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=ALLOW_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Static files ----------
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# Expose media directories to routes
app.state.MEDIA_DIR = MEDIA_DIR
app.state.CHAT_COVER_DIR = CHAT_COVER_DIR
app.state.AVATAR_DIR = AVATAR_DIR

# ---------- Routers ----------
app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(chat_routes.router, prefix="/chats", tags=["Chats"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])

if __name__ == "__main__":
    import uvicorn

    lan_ip = get_lan_ip()
    print("\n=== FastAPI Dev Server ===")
    print(f"Local:   http://127.0.0.1:{PORT}")
    print(f"Network: http://{lan_ip}:{PORT}  (open this from other devices on the same Wi-Fi)")
    print(f"CORS allows: any http/https origin (dev) — tighten for prod; Vite default port {VITE_PORT}\n")

    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=True, log_level="info")