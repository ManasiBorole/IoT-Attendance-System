import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app, Base, engine, normalize_uid
import database
import models

client = TestClient(app)

def test_system():
    # Clear attendance table so test is idempotent
    db = next(database.get_db())
    db.query(models.Attendance).delete()
    db.commit()
    db.close()

    print("--- 1. Testing Root Endpoint ---")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print("Root response:", res.json())

    print("\n--- 2. Testing Students Endpoint & Seed Data ---")
    res = client.get("/api/students")
    assert res.status_code == 200
    students = res.json()
    print("Found students:", len(students))
    for s in students:
        print(f"  - [{s['serial_number']}] {s['name']} (UID: {s['card_uid']})")
    assert len(students) >= 2, "Expected at least 2 seeded students"
    s1 = next(s for s in students if s["card_uid"] == "CD:FA:02:07")
    s2 = next(s for s in students if s["card_uid"] == "6B:66:16:06")
    s1_name = s1["name"]
    s2_name = s2["name"]

    print(f"\n--- 3. Testing Scan for Student 1 ({s1_name}: CD:FA:02:07) ---")
    res = client.post("/api/attendance/scan", json={"card_uid": "cd:fa:02:07"})
    assert res.status_code == 200
    data = res.json()
    print("Scan result 1:", data)
    assert data["success"] is True
    assert data["attendance_marked"] is True
    assert data["student"]["name"] == s1_name
    assert data["status"] == "Present"

    print(f"\n--- 4. Testing Duplicate Scan on Same Day ({s1_name}) ---")
    res = client.post("/api/attendance/scan", json={"card_uid": "CD:FA:02:07"})
    assert res.status_code == 200
    dup_data = res.json()
    print("Duplicate scan result:", dup_data)
    assert dup_data["success"] is True
    assert dup_data["attendance_marked"] is False
    assert dup_data["already_marked"] is True
    assert dup_data["student"]["name"] == s1_name

    print(f"\n--- 5. Testing Scan for Student 2 ({s2_name}: 6B:66:16:06) ---")
    res = client.post("/api/attendance/scan", json={"card_uid": "6b 66 16 06"})  # test space format normalization
    assert res.status_code == 200
    data2 = res.json()
    print("Scan result 2:", data2)
    assert data2["success"] is True
    assert data2["attendance_marked"] is True
    assert data2["student"]["name"] == s2_name

    print("\n--- 6. Testing Unknown Card Scan ---")
    res = client.post("/api/attendance/scan", json={"card_uid": "AA:99:88:77"})
    assert res.status_code == 200
    unk_data = res.json()
    print("Unknown scan result:", unk_data)
    assert unk_data["success"] is False
    assert unk_data["registered"] is False
    assert unk_data["message"] == "This RFID card is not registered to any student."

    print("\n--- 7. Testing /api/attendance/latest ---")
    res = client.get("/api/attendance/latest")
    assert res.status_code == 200
    latest = res.json()
    print("Latest scan event:", latest)
    assert latest["status_type"] == "NOT_REGISTERED"

    print("\n--- 8. Testing /api/attendance Records ---")
    res = client.get("/api/attendance")
    assert res.status_code == 200
    records = res.json()
    print(f"Attendance records count: {len(records)}")
    for r in records:
        print(f"  - Record #{r['id']}: {r['student_name']} (Sr: {r['student_serial_number']}) at {r['attendance_date']} {r['attendance_time']}")
    assert len(records) == 2, f"Expected exactly 2 attendance records, found {len(records)}"

    print("\n--- 9. Testing Add New Student ---")
    res = client.post("/api/students", json={
        "serial_number": 3,
        "name": "Amit Deshmukh",
        "card_uid": "11:22:33:44"
    })
    assert res.status_code == 201
    new_s = res.json()
    print("Created student:", new_s)

    print("\n--- 10. Testing Edit Student ---")
    res = client.put(f"/api/students/{new_s['id']}", json={
        "name": "Amit S. Deshmukh"
    })
    assert res.status_code == 200
    updated_s = res.json()
    print("Updated student:", updated_s)
    assert updated_s["name"] == "Amit S. Deshmukh"

    print("\n--- 11. Testing Delete Student ---")
    res = client.delete(f"/api/students/{new_s['id']}")
    assert res.status_code == 204
    print("Deleted successfully")

    print(f"\n--- 12. Testing Delete {s1_name}'s Attendance Record ---")
    # Fetch current attendance records
    att_res = client.get("/api/attendance")
    records = att_res.json()
    manasi_att = next(r for r in records if r["student_name"] == s1_name)
    del_res = client.delete(f"/api/attendance/{manasi_att['id']}")
    assert del_res.status_code == 204
    print(f"Deleted {s1_name}'s attendance record #{manasi_att['id']}")

    # Verify student 1 disappears from attendance records
    att_res2 = client.get("/api/attendance")
    records2 = att_res2.json()
    assert not any(r["student_name"] == s1_name for r in records2), f"{s1_name} should disappear from attendance"
    print(f"Verified: {s1_name} disappeared from Attendance Records")

    # Verify student 1 remains in Registered Students
    stu_res = client.get("/api/students")
    students = stu_res.json()
    assert any(s["name"] == s1_name and s["card_uid"] == "CD:FA:02:07" for s in students), f"{s1_name} must remain in Registered Students"
    print(f"Verified: {s1_name} remains in Registered Students")

    print(f"\n--- 13. Testing Delete {s2_name}'s Attendance Record ---")
    ghanshyam_att = next(r for r in records2 if r["student_name"] == s2_name)
    del_res2 = client.delete(f"/api/attendance/{ghanshyam_att['id']}")
    assert del_res2.status_code == 204
    print(f"Deleted {s2_name}'s attendance record #{ghanshyam_att['id']}")

    # Verify student 2 disappears from attendance records
    att_res3 = client.get("/api/attendance")
    records3 = att_res3.json()
    assert len(records3) == 0, "Attendance records should now be empty"
    print(f"Verified: {s2_name} disappeared from Attendance Records (now 0 records)")

    # Verify student 2 remains in Registered Students
    stu_res2 = client.get("/api/students")
    students2 = stu_res2.json()
    assert any(s["name"] == s2_name and s["card_uid"] == "6B:66:16:06" for s in students2), f"{s2_name} must remain in Registered Students"
    print(f"Verified: {s2_name} remains in Registered Students")

    print(f"\n--- 14. Testing Scan {s1_name}'s Card Again After Deletion ---")
    scan_again = client.post("/api/attendance/scan", json={"card_uid": "CD:FA:02:07"})
    assert scan_again.status_code == 200
    res_data = scan_again.json()
    print("Scan again result:", res_data)
    assert res_data["success"] is True
    assert res_data["attendance_marked"] is True
    assert res_data["student"]["name"] == s1_name

    # Verify new record appears in attendance table
    att_res4 = client.get("/api/attendance")
    records4 = att_res4.json()
    assert len(records4) == 1
    assert records4[0]["student_name"] == s1_name
    print(f"Verified: {s1_name}'s attendance is created again normally!")

    print("\nALL BACKEND UNIT & INTEGRATION TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_system()
