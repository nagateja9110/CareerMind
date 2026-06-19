from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings


settings = get_settings()
client: AsyncIOMotorClient | None = None
database: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> AsyncIOMotorDatabase:
    global client, database

    if database is not None:
        return database

    client = AsyncIOMotorClient(settings.mongo_uri)
    database = client[settings.mongo_db]
    await database[settings.users_collection].create_index("email", unique=True)
    await database[settings.chats_collection].create_index("user_id")
    await database[settings.resumes_collection].create_index("user_id")
    await database[settings.skills_taxonomy_collection].create_index("role", unique=True)
    await database[settings.jobs_collection].create_index("id", unique=True)
    await database[settings.jobs_collection].create_index("title")
    await database[settings.jobs_collection].create_index("location")
    await database[settings.jobs_collection].create_index("skills")
    return database


def get_database() -> AsyncIOMotorDatabase:
    if database is None:
        raise RuntimeError("Database connection has not been initialized.")
    return database


def close_mongo_client() -> None:
    global client, database

    if client is not None:
        client.close()

    client = None
    database = None
