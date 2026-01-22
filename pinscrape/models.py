from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional


class PinImage(BaseModel):
    url: HttpUrl


class PinResult(BaseModel):
    images: Dict[str, PinImage]


class SearchData(BaseModel):
    results: List[PinResult] = []


class ResourceResponse(BaseModel):
    data: Optional[SearchData] = None

    # allow all extra fields Pinterest returns
    class Config:
        extra = "allow"


class SearchResponse(BaseModel):
    resource_response: ResourceResponse
    client_context: Dict[str, Any]


class BoardData(BaseModel):
    created_at: Optional[str]


class BoardResourceResponse(BaseModel):
    data: Optional[BoardData] = None

    class Config:
        extra = "allow"


class BoardResponse(BaseModel):
    resource_response: BoardResourceResponse
