import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.bot import bot
from src.elastic.elastic_controller import elastic_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(bot.infinity_polling(), name="bot-task")
    yield


app = FastAPI(
    lifespan=lifespan,
    root_path="/api/v1"
)

app.include_router(elastic_router, prefix="")
