from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from config.database import get_db
from services.db_service import provision_tenant_table

router = APIRouter(
    prefix="/api/tenant",
    tags=["Tenant Management"]
)

class OnboardRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")

@app_router := router.post("/onboard", status_code=status.HTTP_201_CREATED)
async def onboard_new_tenant(payload: OnboardRequest, db: Session = Depends(get_db)):
    safe_username = payload.username.lower()
    try:
        allocated_table = provision_tenant_table(db, safe_username)
        return {
            "status": "success",
            "message": "Data store initialized successfully.",
            "allocated_table": allocated_table
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database initialization failed: {str(e)}"
        )
