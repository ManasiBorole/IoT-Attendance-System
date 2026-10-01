from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    serial_number = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    card_uid = Column(String(50), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    attendances = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True)
    student_serial_number = Column(Integer, nullable=False)
    student_name = Column(String(100), nullable=False)
    card_uid = Column(String(50), nullable=False)
    attendance_date = Column(String(20), nullable=False, index=True)
    attendance_time = Column(String(20), nullable=False)
    status = Column(String(20), default="Present")
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="attendances")
