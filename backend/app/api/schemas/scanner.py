from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ScannerConfigCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    universe_config: Dict[str, Any]
    filter_config: Dict[str, Any]
    ranking_config: Optional[Dict[str, Any]] = None
    timeframe: Optional[str] = None

class ScannerConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    universe_config: Optional[Dict[str, Any]] = None
    filter_config: Optional[Dict[str, Any]] = None
    ranking_config: Optional[Dict[str, Any]] = None
    timeframe: Optional[str] = None
    is_active: Optional[bool] = None
