from app.errors import object_payload
from fastapi import APIRouter, Body
from app.modules.m8_evidence.service import execute
from app.pipeline import sample_text
from app.errors import BusinessError
router = APIRouter()


@router.post("/api/8")
def calculate(payload: object = Body(default=None)):
    payload = object_payload(payload)
    text = payload.get("text", sample_text())
    if not isinstance(text, str):
        raise BusinessError("TEXT", "输入须为文本")
    return execute(text)


@router.get("/api/8")
def sample():
    return execute(sample_text())
