from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import DB_models
from src import login, websocket_endpoint, user, general, group

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(DB_models.Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Booting up: Ensuring database tables exist...")
    await init_db()

    yield
    print("Shutting down gracefully...")
app = FastAPI(lifespan=lifespan, root_path="/chatapp/api")

origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://16.112.64.12",
    "http://16.112.64.12.nip.io"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Use the list instead of "*" for better security with credentials
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(login.router, tags=["Login"])
app.include_router(websocket_endpoint.router)
app.include_router(user.router, prefix="/users", tags=["User APIs"])
app.include_router(general.router, tags=["General APIs"])
app.include_router(group.router, prefix="/groups", tags=["Group APIs"])