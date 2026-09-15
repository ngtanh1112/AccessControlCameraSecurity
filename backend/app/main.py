from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.cameras import router as cameras_router
from app.api.v1.events import router as events_router
from app.api.v1.management import router as management_router
from app.api.v1.media import router as media_router
from app.api.v1.registry import router as registry_router

app = FastAPI(title="Access Control Camera Security API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(cameras_router)
app.include_router(events_router)
app.include_router(management_router)
app.include_router(media_router)
app.include_router(registry_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
