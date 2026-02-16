from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from src.__version__ import APP_VERSION
from src.common.exceptions.exception_handler import ExceptionHandlerMiddleware
from src.dependencies import elastic_client
from src.elastic.elastic_controller import elastic_router
from src.idu_llm.idu_llm_controller import idu_llm_router
from src.logs.logs_router import logs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await elastic_client.check_indexes()
    yield


app = FastAPI(lifespan=lifespan, root_path="/api/v1", version=APP_VERSION)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ExceptionHandlerMiddleware)

app.include_router(elastic_router, prefix="")
app.include_router(idu_llm_router, prefix="")
app.include_router(logs_router, prefix="")


@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs")
