import databases
import sqlalchemy
from app.core.config import settings

database = databases.Database(settings.DATABASE_URL)
metadata = sqlalchemy.MetaData()

# Use psycopg2 for synchronous engine (for migrations etc.)
engine = sqlalchemy.create_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
)

async def connect_db():
    await database.connect()
    print("✅ Connected to PostgreSQL")

async def disconnect_db():
    await database.disconnect()
    print("❌ Disconnected from PostgreSQL")