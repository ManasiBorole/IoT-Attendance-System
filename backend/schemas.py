from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

class StudentBase(BaseModel):
    serial_number: int = Field(..., description="Student serial number")
    name: str = Field(..., min_length=1, max_length=100, description="Student full name")
    card_uid: str = Field(..., min_length=1, max_length=50, description="RFID Card UID")

class StudentCreate(StudentBase):
    pass

class StudentUpdate(BaseModel):
    serial_number: Optional[int] = None
    name: Optional[str] = None
    card_uid: Optional[str] = None

class StudentResponse(StudentBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AttendanceResponse(BaseModel):
    id: int
    student_id: Optional[int] = None
    student_serial_number: int
    student_name: str
    card_uid: str
    attendance_date: str
    attendance_time: str
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ScanRequest(BaseModel):
    card_uid: str = Field(..., min_length=1, description="Scanned RFID UID")

class LatestScanResponse(BaseModel):
    success: bool
    status_type: str  # "MARKED", "ALREADY_MARKED", "NOT_REGISTERED"
    message: str
    card_uid: str
    student: Optional[Dict[str, Any]] = None
    date: Optional[str] = None
    time: Optional[str] = None
    status: Optional[str] = None
    scan_timestamp: Optional[str] = None
