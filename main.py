from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):
    logger.exception("Unhandled HTTP error")

    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
        },
    )


app.include_router(sse_router)
