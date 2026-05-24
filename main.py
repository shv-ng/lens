import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from api.routes import router
from api.sse import router as sse_router
from config.logging_config import setup_logging
from db.postgres import Postgres

setup_logging()

logger = logging.getLogger(__name__)

db = Postgres()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Application starting...")
    load_dotenv()
    await db.connect()

    yield

    logger.info("Application shutting down...")

    await db.disconnect()


app = FastAPI(lifespan=lifespan)

app.include_router(router)
app.include_router(sse_router)
