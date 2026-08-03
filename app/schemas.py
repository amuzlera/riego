from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    api_key: str = Field(default="")
    description: str = Field(default="")
    enabled: bool = True


class DeviceUpdate(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class ExecuteRequest(BaseModel):
    name: str = Field(min_length=1)
    args: Dict[str, Any] = Field(default_factory=dict)


class PinSetRequest(BaseModel):
    value: bool


class RunForRequest(BaseModel):
    seconds: int = Field(gt=0)
    value: bool = True


class ProgramPeriod(BaseModel):
    start: str = Field(min_length=1)
    end: str = Field(min_length=1)


class ProgramCreate(BaseModel):
    pin: str = Field(min_length=1)
    days: list[int] = Field(default_factory=list)
    periods: list[ProgramPeriod | str] = Field(default_factory=list)
    start: Optional[str] = None
    end: Optional[str] = None
    enabled: bool = True
    label: str = ""


class ProgramUpdate(BaseModel):
    pin: Optional[str] = None
    days: Optional[list[int]] = None
    periods: Optional[list[ProgramPeriod | str]] = None
    start: Optional[str] = None
    end: Optional[str] = None
    enabled: Optional[bool] = None
    label: Optional[str] = None


class ActionRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


class SensorReading(BaseModel):
    device: str
    sensor: str
    recorded_at: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    data: Dict[str, Any] = Field(default_factory=dict)
