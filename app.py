from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.instances import USER_MANAGER, CHAT_MANAGER
from backend.routes import user_routes, chat_routes, web_socket
import uvicorn
import os
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Checking database files...")
    if not os.path.exists("user_manager.pkl"):
        print("Creating user_manager.pkl...")
        USER_MANAGER.save()
    if not os.path.exists("chat_manager.pkl"):
        print("Creating chat_manager.pkl...")
        CHAT_MANAGER.save_chat_database()
    print("Database initialization complete.")

    yield

    print("Saving all AVL trees before shutdown...")
    USER_MANAGER.save()
    CHAT_MANAGER.save_chat_database()
    print("Data saved.")


app = FastAPI(title="Chat App", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(user_routes.router, prefix="/users", tags=["Users"])
app.include_router(chat_routes.router, prefix="/chats", tags=["Chats"])
app.include_router(web_socket.router, prefix="/ws", tags=["WebSocket"])

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)