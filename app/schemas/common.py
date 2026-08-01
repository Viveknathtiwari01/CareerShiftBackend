from typing import Any, Generic, TypeVar, List, Optional
from pydantic import BaseModel
from datetime import datetime

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
    errors: Optional[List[str]] = None
    meta: Optional[dict] = None
    timestamp: datetime = datetime.utcnow()
    request_id: Optional[str] = None
