import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.redis_client import redis_client
from app.core.database import connect_db, disconnect_db
from app.api.v1.endpoints import verify

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup with generous retry logic
    max_retries = 10
    for attempt in range(max_retries):
        try:
            await redis_client.connect()
            break
        except Exception as e:
            print(f"Redis connection attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(3)  # Wait longer between retries
    
    for attempt in range(max_retries):
        try:
            await connect_db()
            break
        except Exception as e:
            print(f"Postgres connection attempt {attempt+1} failed: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(3)
    
    yield
    
    # Shutdown
    await redis_client.disconnect()
    await disconnect_db()

# Rest of main.py unchanged...

# Rest of the file unchanged...

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(verify.router, prefix=settings.API_V1_STR, tags=["verification"])

@app.get("/")
async def root():
    return {"message": "ClickGuard API is running"}