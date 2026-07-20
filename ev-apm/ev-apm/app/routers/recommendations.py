"""
app/routers/recommendations.py
================================
GET /api/v1/recommendations/{vehicle_id}

Returns charging and maintenance advice for one vehicle, generated
by services/recommendation_service.py.
"""

from fastapi import APIRouter
from app.models.schemas import RecommendationOut
from app.services.recommendation_service import generate_recommendations

router = APIRouter()


@router.get("/recommendations/{vehicle_id}", response_model=list[RecommendationOut])
async def get_recommendations(vehicle_id: str):
    """
    Returns a prioritized list of charging/maintenance recommendations.
    Priority 1 = most urgent (e.g. "replace battery"),
    Priority 3 = informational (e.g. "current habits are fine").
    """
    recs = await generate_recommendations(vehicle_id)
    return recs
