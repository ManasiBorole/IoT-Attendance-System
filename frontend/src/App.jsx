import React, { useState, useEffect, useRef } from "react";
import "./App.css";
const API_BASE = import.meta.env.VITE_API_BASE_URL || `http://${window.location.hostname || "localhost"}:8000`;

export default function App() {
  const [students, setStudents] = useState([]);
  const [attendance, setAttendance] = useState([]);
  const [latestScan, setLatestScan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modal State for Add / Edit Student
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingStudent, setEditingStudent] = useState(null);
  const [formData, setFormData] = useState({ serial_number: "", name: "", card_uid: "" });
  const [formError, setFormError] = useState("");

  const prevScanTimestampRef = useRef("");

  // Fetch all registered students
  const fetchStudents = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/students`);
      if (res.ok) {
        const data = await res.json();
        setStudents(data);
      }
    } catch (err) {
      console.error("Error fetching students:", err);
    }
  };

  // Fetch all attendance records
  const fetchAttendance = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/attendance`);
      if (res.ok) {
        const data = await res.json();
        setAttendance(data);
      }
    } catch (err) {
      console.error("Error fetching attendance:", err);
    }
  };

  // Poll latest scan
  const fetchLatestScan = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/attendance/latest`);
      if (res.ok) {
        const data = await res.json();
        setLatestScan(data);

        // If a new scan occurred, refresh the attendance table
        const scanKey = data.raw_timestamp || data.scan_timestamp || "";
        if (scanKey && scanKey !== prevScanTimestampRef.current) {
          prevScanTimestampRef.current = scanKey;
          fetchAttendance();
        }
      }
    } catch (err) {
      console.error("Error polling latest scan:", err);
    }
  };

  // Initial load and polling setup
  useEffect(() => {
    const init = async () => {
      setLoading(true);
      await Promise.all([fetchStudents(), fetchAttendance(), fetchLatestScan()]);
      setLoading(false);
    };
    init();

    // Poll latest scan every 1.5 seconds
    const interval = setInterval(() => {
      fetchLatestScan();
    }, 1500);

    return () => clearInterval(interval);
  }, []);

  // Handle Modal Open
  const handleOpenAddModal = (initialUid = "") => {
    // Propose next serial number
    const maxSn = students.reduce((max, s) => Math.max(max, Number(s.serial_number) || 0), 0);
    setEditingStudent(null);
    setFormData({
      serial_number: maxSn + 1,
      name: "",
      card_uid: initialUid || ""
    });
    setFormError("");
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (student) => {
    setEditingStudent(student);
    setFormData({
      serial_number: student.serial_number,
      name: student.name,
      card_uid: student.card_uid
    });
    setFormError("");
    setIsModalOpen(true);
  };

  // Handle Student Submit
  const handleSaveStudent = async (e) => {
    e.preventDefault();
    setFormError("");

    if (!formData.serial_number || !formData.name.trim() || !formData.card_uid.trim()) {
      setFormError("All fields are required.");
      return;
    }

    try {
      const payload = {
        serial_number: parseInt(formData.serial_number, 10),
        name: formData.name.trim(),
        card_uid: formData.card_uid.trim()
      };

      let res;
      if (editingStudent) {
        res = await fetch(`${API_BASE}/api/students/${editingStudent.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      } else {
        res = await fetch(`${API_BASE}/api/students`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
      }

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to save student");
      }

      setIsModalOpen(false);
      await fetchStudents();
    } catch (err) {
      setFormError(err.message);
    }
  };

  // Handle Delete Student
  const handleDeleteStudent = async (id, name) => {
    if (window.confirm(`Are you sure you want to delete student "${name}"?`)) {
      try {
        const res = await fetch(`${API_BASE}/api/students/${id}`, { method: "DELETE" });
        if (res.ok) {
          await fetchStudents();
          await fetchAttendance();
        }
      } catch (err) {
        alert("Failed to delete student: " + err.message);
      }
    }
  };

  // Handle Delete Attendance Record
  const handleDeleteAttendance = async (attendanceId) => {
    try {
      setAttendance((prev) => prev.filter((r) => r.id !== attendanceId));
      const res = await fetch(`${API_BASE}/api/attendance/${attendanceId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        await fetchAttendance();
        await fetchLatestScan();
      } else {
        await fetchAttendance();
      }
    } catch (err) {
      console.error("Failed to delete attendance record:", err);
      await fetchAttendance();
    }
  };

  return (
    <div className="app-container">
      {/* HEADER */}
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9" />
              <path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5" />
              <circle cx="12" cy="12" r="2" />
              <path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5" />
              <path d="M19.1 4.9C23 8.8 23 15.2 19.1 19.1" />
            </svg>
          </div>
          <div>
            <h1 className="brand-title">RFID Attendance System</h1>
            <p className="brand-subtitle">ESP32 + RC522 Hardware Integration</p>
          </div>
        </div>

        <div className="header-status">
          <span className="status-dot"></span>
          <span>RFID Reader Ready</span>
        </div>
      </header>

      {/* SECTION 3: LATEST SCAN DISPLAY (At the top of attendance section) */}
      <section className="scan-card-wrapper">
        {(!latestScan || latestScan.status_type === "IDLE") && (
          <div className="scan-card idle">
            <div className="scan-card-header">
              <div className="scan-badge-title">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4.9 19.1C1 15.2 1 8.8 4.9 4.9" />
                  <path d="M7.8 16.2c-2.3-2.3-2.3-6.1 0-8.5" />
                  <circle cx="12" cy="12" r="2" />
                  <path d="M16.2 7.8c2.3 2.3 2.3 6.1 0 8.5" />
                  <path d="M19.1 4.9C23 8.8 23 15.2 19.1 19.1" />
                </svg>
                <span>RFID Reader Ready</span>
              </div>
            </div>
            <div className="scan-content">
              <p style={{ color: "var(--text-muted)", fontSize: "1.05rem", fontWeight: 500 }}>
                Tap your RFID card on the reader to mark attendance.
              </p>
            </div>
          </div>
        )}

        {latestScan && latestScan.status_type === "MARKED" && (
          <div className="scan-card marked">
            <div className="scan-card-header">
              <div className="scan-badge-title">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>✓ ATTENDANCE MARKED</span>
              </div>
              <span className="scan-time-badge">{latestScan.scan_timestamp}</span>
            </div>
            <div className="scan-content">
              <div className="student-hero-name">{latestScan.student?.name}</div>
              <div className="scan-details-grid">
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Student Name</div>
                  <div className="scan-detail-value">{latestScan.student?.name}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Serial No.</div>
                  <div className="scan-detail-value">{latestScan.student?.serial_number}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Card UID</div>
                  <div className="scan-detail-value uid">{latestScan.student?.card_uid}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Date</div>
                  <div className="scan-detail-value">{latestScan.date}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Time</div>
                  <div className="scan-detail-value">{latestScan.time}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Status</div>
                  <div className="scan-detail-value">
                    <span className="badge-present">Present</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {latestScan && latestScan.status_type === "ALREADY_MARKED" && (
          <div className="scan-card already_marked">
            <div className="scan-card-header">
              <div className="scan-badge-title">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>✓ ATTENDANCE ALREADY MARKED</span>
              </div>
              <span className="scan-time-badge">{latestScan.scan_timestamp}</span>
            </div>
            <div className="scan-content">
              <div className="student-hero-name">{latestScan.student?.name}</div>
              <div className="scan-details-grid">
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Student Name</div>
                  <div className="scan-detail-value">{latestScan.student?.name}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Serial No.</div>
                  <div className="scan-detail-value">{latestScan.student?.serial_number}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Card UID</div>
                  <div className="scan-detail-value uid">{latestScan.student?.card_uid}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Date</div>
                  <div className="scan-detail-value">{latestScan.date}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Original Time</div>
                  <div className="scan-detail-value">{latestScan.original_time || latestScan.time}</div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Status</div>
                  <div className="scan-detail-value">
                    <span className="badge-present">Present</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {latestScan && latestScan.status_type === "NOT_REGISTERED" && (
          <div className="scan-card not_registered">
            <div className="scan-card-header">
              <div className="scan-badge-title">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
                <span>✗ CARD NOT REGISTERED</span>
              </div>
              <span className="scan-time-badge">{latestScan.scan_timestamp}</span>
            </div>
            <div className="scan-content">
              <div className="scan-details-grid">
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Detected Card UID</div>
                  <div className="scan-detail-value uid" style={{ color: "var(--danger)" }}>
                    {latestScan.card_uid}
                  </div>
                </div>
                <div className="scan-detail-item">
                  <div className="scan-detail-label">Message</div>
                  <div className="scan-detail-value" style={{ fontSize: "0.95rem", color: "var(--danger-text)" }}>
                    This RFID card is not registered to any student.
                  </div>
                </div>
                <div className="scan-detail-item" style={{ display: "flex", alignItems: "center" }}>
                  <button
                    className="btn-primary"
                    style={{ width: "100%", justifyContent: "center" }}
                    onClick={() => handleOpenAddModal(latestScan.card_uid)}
                  >
                    + Register This Card
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* DASHBOARD GRID: SECTION 1 (STUDENT LIST) & SECTION 2 (ATTENDANCE RECORDS) */}
      <div className="dashboard-grid">
        {/* SECTION 1: STUDENT LIST */}
        <section className="section-panel">
          <div className="section-header">
            <div className="section-title">
              <span>Section 1: Registered Students</span>
              <span className="count-badge">{students.length}</span>
            </div>
            <button className="btn-primary" onClick={() => handleOpenAddModal()}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              <span>Add Student</span>
            </button>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: "80px" }}>Sr. No.</th>
                  <th>Student Name</th>
                  <th>RFID Card UID</th>
                  <th style={{ width: "120px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {students.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="empty-state">
                      No students registered yet. Click "Add Student" to create one.
                    </td>
                  </tr>
                ) : (
                  students.map((s) => (
                    <tr key={s.id}>
                      <td><strong>{s.serial_number}</strong></td>
                      <td style={{ fontWeight: 600 }}>{s.name}</td>
                      <td>
                        <code className="mono">{s.card_uid}</code>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <div className="actions-cell" style={{ justifyContent: "flex-end" }}>
                          <button
                            className="btn-sm-outline"
                            title="Edit Student"
                            onClick={() => handleOpenEditModal(s)}
                          >
                            Edit
                          </button>
                          <button
                            className="btn-sm-danger"
                            title="Delete Student"
                            onClick={() => handleDeleteStudent(s.id, s.name)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* SECTION 2: ATTENDANCE RECORDS */}
        <section className="section-panel">
          <div className="section-header">
            <div className="section-title">
              <span>Section 2: Attendance Records</span>
              <span className="count-badge">{attendance.length}</span>
            </div>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
              Auto-updates when card is scanned
            </span>
          </div>

          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Student Sr. No.</th>
                  <th>Student Name</th>
                  <th>Card UID</th>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Status</th>
                  <th style={{ width: "80px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {attendance.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="empty-state">
                      No attendance records for today. Scan an RFID card to mark attendance.
                    </td>
                  </tr>
                ) : (
                  attendance.map((rec, index) => (
                    <tr key={rec.id} className={index === 0 ? "newest-row" : ""}>
                      <td><strong>{rec.student_serial_number}</strong></td>
                      <td style={{ fontWeight: 600 }}>{rec.student_name}</td>
                      <td>
                        <code className="mono">{rec.card_uid}</code>
                      </td>
                      <td>{rec.attendance_date}</td>
                      <td>{rec.attendance_time}</td>
                      <td>
                        <span className="badge-present">{rec.status}</span>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <button
                          className="btn-sm-danger"
                          title="Delete Attendance Record"
                          onClick={() => handleDeleteAttendance(rec.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* ADD / EDIT STUDENT MODAL */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">
                {editingStudent ? "Edit Student" : "Add New Student"}
              </h2>
              <button className="modal-close" onClick={() => setIsModalOpen(false)}>
                &times;
              </button>
            </div>

            <form onSubmit={handleSaveStudent} className="modal-form">
              {formError && <div className="form-error">{formError}</div>}

              <div className="form-group">
                <label>Student Serial Number</label>
                <input
                  type="number"
                  className="form-input"
                  required
                  placeholder="e.g. 1"
                  value={formData.serial_number}
                  onChange={(e) => setFormData({ ...formData, serial_number: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Student Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  required
                  placeholder="e.g. Rahul Patil"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>RFID Card UID</label>
                <input
                  type="text"
                  className="form-input mono"
                  required
                  placeholder="e.g. 6B:66:16:06"
                  value={formData.card_uid}
                  onChange={(e) => setFormData({ ...formData, card_uid: e.target.value.toUpperCase() })}
                />
                <span className="form-help">Enter hex UID separated by colons or spaces (e.g. 6B:66:16:06)</span>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  {editingStudent ? "Save Changes" : "Register Student"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
