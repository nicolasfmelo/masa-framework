from fastapi import FastAPI

from app.routes import router

app = FastAPI(title="Inventory Analysis API")
app.include_router(router)
