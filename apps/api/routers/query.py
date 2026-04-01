from fastapi import APIRouter

router = APIRouter()

@router.post("/stream")
async def query_stream():
    return {"message": "Stub for stream endpoint"}
