from fastapi import FastAPI

from src.delivery.http.handlers import router

app = FastAPI(title="Inventory Analysis API")
app.include_router(router)
