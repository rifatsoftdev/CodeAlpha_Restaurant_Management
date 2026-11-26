from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import models  # noqa: F401  (registers tables with SQLAlchemy)
from app.core.database import initialize_database
from app.routers import auth, inventory, menu, orders, reports, reservations, tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()  # use Alembic migrations when the schema grows further
    yield



app = FastAPI(title="Restaurant Management System", version="0.1.0", lifespan=lifespan)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

for r in (auth, menu, orders, tables, reservations, inventory, reports):
    app.include_router(r.router)


@app.get("/", tags=["Health"])
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    # Browsers may request this conventional path even when a page declares
    # its own SVG icon, so serve the same icon here instead of returning 404.
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "docs": "/docs"}
