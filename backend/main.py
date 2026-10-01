import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from database import engine, Base, get_db
import models
import schemas

# Create database tables
Base.metadata.create_all(bind=engine)

# In-memory tracking of the latest scan event
latest_scan_event: Optional[Dict[str, Any]] = None

def init_seed_data():
    db = next(get_db())
    try:
        count = db.query(models.Student).count()
        if count == 0:
            sample_students = [
                models.Student(
                    serial_number=1,
                    name="Manasi Borole",
                    card_uid="CD:FA:02:07"
                ),
                models.Student(
                    serial_number=2,
                    name="Ghanshyam Auti",
                    card_uid="6B:66:16:06"
                ),
            ]
            db.add_all(sample_students)
            db.commit()
            print("Seeded registered students: Manasi Borole (CD:FA:02:07), Ghanshyam Auti (6B:66:16:06)")
    finally:
        db.close()

# Seed immediately on load
init_seed_data()

def normalize_uid(raw_uid: str) -> str:
    cleaned = raw_uid.strip().upper()
    if " " in cleaned and ":" not in cleaned:
        cleaned = ":".join(cleaned.split())
    cleaned = cleaned.replace("-", ":")
    return cleaned

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_seed_data()
    yield

app = FastAPI(
    title="IoT RFID Attendance System API",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Student Management Endpoints
# --------------------------------------------------------------------------

@app.get("/api/students", response_model=List[schemas.StudentResponse])
def get_students(db: Session = Depends(get_db)):
    return db.query(models.Student).order_by(models.Student.serial_number.asc()).all()

@app.post("/api/students", response_model=schemas.StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(student_in: schemas.StudentCreate, db: Session = Depends(get_db)):
    clean_uid = normalize_uid(student_in.card_uid)
    
    # Check if card_uid already registered
    existing = db.query(models.Student).filter(models.Student.card_uid == clean_uid).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Card UID '{clean_uid}' is already registered to {existing.name} (Sr No: {existing.serial_number})"
        )

    # Check if serial number already exists
    existing_sn = db.query(models.Student).filter(models.Student.serial_number == student_in.serial_number).first()
    if existing_sn:
        raise HTTPException(
            status_code=400,
            detail=f"Student serial number {student_in.serial_number} is already assigned to {existing_sn.name}"
        )

    new_student = models.Student(
        serial_number=student_in.serial_number,
        name=student_in.name.strip(),
        card_uid=clean_uid
    )
    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    return new_student

@app.put("/api/students/{student_id}", response_model=schemas.StudentResponse)
def update_student(student_id: int, student_in: schemas.StudentUpdate, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student_in.card_uid is not None:
        clean_uid = normalize_uid(student_in.card_uid)
        existing = db.query(models.Student).filter(
            models.Student.card_uid == clean_uid,
            models.Student.id != student_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Card UID '{clean_uid}' is already registered to another student")
        student.card_uid = clean_uid

    if student_in.serial_number is not None:
        existing_sn = db.query(models.Student).filter(
            models.Student.serial_number == student_in.serial_number,
            models.Student.id != student_id
        ).first()
        if existing_sn:
            raise HTTPException(status_code=400, detail=f"Serial number {student_in.serial_number} already in use")
        student.serial_number = student_in.serial_number

    if student_in.name is not None and student_in.name.strip():
        student.name = student_in.name.strip()

    db.commit()
    db.refresh(student)
    return student

@app.delete("/api/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
    return None

# --------------------------------------------------------------------------
# Attendance Endpoints
# --------------------------------------------------------------------------

@app.get("/api/attendance", response_model=List[schemas.AttendanceResponse])
def get_attendance(db: Session = Depends(get_db)):
    # Returns latest attendance records first
    return db.query(models.Attendance).order_by(models.Attendance.id.desc()).all()

@app.delete("/api/attendance/{attendance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance(attendance_id: int, db: Session = Depends(get_db)):
    global latest_scan_event
    rec = db.query(models.Attendance).filter(models.Attendance.id == attendance_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    deleted_uid = rec.card_uid
    db.delete(rec)
    db.commit()

    # If the deleted record was currently displayed in latest_scan_event, update it
    if latest_scan_event and latest_scan_event.get("card_uid") == deleted_uid:
        latest_remaining = db.query(models.Attendance).order_by(models.Attendance.id.desc()).first()
        if latest_remaining:
            latest_scan_event = {
                "success": True,
                "attendance_marked": True,
                "already_marked": False,
                "status_type": "MARKED",
                "message": "Attendance marked successfully",
                "card_uid": latest_remaining.card_uid,
                "student": {
                    "serial_number": latest_remaining.student_serial_number,
                    "name": latest_remaining.student_name,
                    "card_uid": latest_remaining.card_uid
                },
                "date": latest_remaining.attendance_date,
                "time": latest_remaining.attendance_time,
                "status": latest_remaining.status,
                "scan_timestamp": f"{latest_remaining.attendance_date} {latest_remaining.attendance_time}",
                "raw_timestamp": latest_remaining.created_at.isoformat() if latest_remaining.created_at else None
            }
        else:
            latest_scan_event = {
                "status_type": "IDLE",
                "message": "RFID Reader Ready",
                "sub_message": "Tap your RFID card"
            }

    return None

@app.get("/api/attendance/latest")
def get_latest_scan():
    global latest_scan_event
    return latest_scan_event or {
        "status_type": "IDLE",
        "message": "RFID Reader Ready",
        "sub_message": "Tap your RFID card"
    }

@app.post("/api/attendance/scan")
def scan_card(scan_in: schemas.ScanRequest, db: Session = Depends(get_db)):
    global latest_scan_event
    raw_uid = scan_in.card_uid
    clean_uid = normalize_uid(raw_uid)

    now = datetime.now()
    current_date = now.strftime("%d-%m-%Y")
    current_time = now.strftime("%I:%M:%S %p")
    timestamp_iso = now.isoformat()

    print("\n" + "="*50)
    print("RFID scan received:")
    print(f"UID: {clean_uid}")

    # Step 1: Search student by card_uid
    student = db.query(models.Student).filter(models.Student.card_uid == clean_uid).first()

    # Case A: Card is NOT registered
    if not student:
        print("Student found: None (Card Not Registered)")
        print("Attendance not marked.")
        print("="*50 + "\n")
        event = {
            "success": False,
            "registered": False,
            "attendance_marked": False,
            "already_marked": False,
            "status_type": "NOT_REGISTERED",
            "card_uid": clean_uid,
            "message": "This RFID card is not registered to any student.",
            "scan_timestamp": f"{current_date} {current_time}",
            "raw_timestamp": timestamp_iso
        }
        latest_scan_event = event
        return {
            "success": False,
            "registered": False,
            "card_uid": clean_uid,
            "message": "This RFID card is not registered to any student."
        }

    # Case B: Student exists - Check if already marked today
    existing_attendance = db.query(models.Attendance).filter(
        models.Attendance.student_id == student.id,
        models.Attendance.attendance_date == current_date
    ).first()

    if existing_attendance:
        print(f"Student found: {student.name} (Serial No: {student.serial_number})")
        print("Result: Attendance already marked today.")
        print(f"Original Time: {existing_attendance.attendance_time}")
        print("="*50 + "\n")
        event = {
            "success": True,
            "attendance_marked": False,
            "already_marked": True,
            "status_type": "ALREADY_MARKED",
            "message": "Attendance already marked today.",
            "card_uid": student.card_uid,
            "student": {
                "serial_number": student.serial_number,
                "name": student.name,
                "card_uid": student.card_uid
            },
            "date": existing_attendance.attendance_date,
            "time": existing_attendance.attendance_time,
            "original_time": existing_attendance.attendance_time,
            "status": existing_attendance.status,
            "scan_timestamp": f"{current_date} {current_time}",
            "raw_timestamp": timestamp_iso
        }
        latest_scan_event = event
        return {
            "success": True,
            "attendance_marked": False,
            "already_marked": True,
            "message": "Attendance already marked today.",
            "student": {
                "serial_number": student.serial_number,
                "name": student.name,
                "card_uid": student.card_uid
            },
            "date": existing_attendance.attendance_date,
            "time": existing_attendance.attendance_time,
            "original_time": existing_attendance.attendance_time,
            "status": existing_attendance.status
        }

    # Case C: Valid student, not yet marked today -> Mark Present
    new_attendance = models.Attendance(
        student_id=student.id,
        student_serial_number=student.serial_number,
        student_name=student.name,
        card_uid=student.card_uid,
        attendance_date=current_date,
        attendance_time=current_time,
        status="Present"
    )
    db.add(new_attendance)
    db.commit()
    db.refresh(new_attendance)

    print(f"Student found: {student.name}")
    print("Attendance marked:")
    print(f"{current_date} {current_time} - Status: Present")
    print("="*50 + "\n")

    event = {
        "success": True,
        "attendance_marked": True,
        "already_marked": False,
        "status_type": "MARKED",
        "message": "Attendance marked successfully",
        "card_uid": student.card_uid,
        "student": {
            "serial_number": student.serial_number,
            "name": student.name,
            "card_uid": student.card_uid
        },
        "date": current_date,
        "time": current_time,
        "status": "Present",
        "scan_timestamp": f"{current_date} {current_time}",
        "raw_timestamp": timestamp_iso
    }
    latest_scan_event = event

    return {
        "success": True,
        "attendance_marked": True,
        "already_marked": False,
        "student": {
            "serial_number": student.serial_number,
            "name": student.name,
            "card_uid": student.card_uid
        },
        "date": current_date,
        "time": current_time,
        "status": "Present"
    }

@app.get("/")
def root():
    return {
        "project": "IoT RFID Attendance System",
        "status": "running",
        "endpoints": {
            "students": "/api/students",
            "attendance": "/api/attendance",
            "latest_scan": "/api/attendance/latest",
            "scan": "/api/attendance/scan"
        }
    }
