from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Зареждане на .env файла
load_dotenv()

# Взимане на URL за връзка от .env файла
DATABASE_URL = os.getenv("DATABASE_URL")

# Създаване на engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Създаване на session
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base клас за ORM моделите
Base = declarative_base()

# Dependency за взимане на сесия
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
