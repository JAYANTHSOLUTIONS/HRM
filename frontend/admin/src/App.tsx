import { createContext, useContext, useEffect, useState } from "react";
import { api, login, signup, type ApiDashboard, type ApiEmployee, type ApiAttendance, type ApiLeaveRequest, type ApiSalary, type ApiUser, type ApiDepartment, type ApiDesignation } from "./api";

// ─── Types ────────────────────────────────────────────────────────────────────

type Page = "dashboard" | "employees" | "employee-detail" | "attendance" | "timeoff" | "salary";
type EmployeeTab = "resume" | "private" | "salary";
type TimeOffStatus = "pending" | "approved" | "rejected";
type AttendanceStatus = "present" | "absent" | "leave" | "holiday";

interface Employee {
  id: number;
  name: string;
  initials: string;
  role: string;
  department: string;
  email: string;
  phone: string;
  joinDate: string;
  status: "active" | "inactive";
  avatarColor: string;
  profilePictureUrl?: string;
}

interface TimeOffRequest {
  id: number;
  employeeId: number;
  type: string;
  from: string;
  to: string;
  days: number;
  reason: string;
  status: TimeOffStatus;
  attachmentPath?: string;
  reviewComment?: string;
}

interface AttendanceRecord {
  date: string;
  employeeId: number;
  status: AttendanceStatus;
  checkIn?: string;
  checkOut?: string;
  hours?: number;
}

interface HRData {
  token: string;
  employees: Employee[];
  attendance: AttendanceRecord[];
  requests: TimeOffRequest[];
  dashboard: ApiDashboard | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
}

const HRDataContext = createContext<HRData | null>(null);

function useHRData() {
  const value = useContext(HRDataContext);
  if (!value) throw new Error("HR data provider is missing");
  return value;
}

function initials(name: string) {
  return name.split(" ").map(part => part[0]).join("").slice(0, 2).toUpperCase();
}

function mapEmployee(employee: ApiEmployee): Employee {
  return {
    id: employee.employee_id,
    name: employee.full_name,
    initials: initials(employee.full_name),
    role: employee.designation?.title ?? "Employee",
    department: employee.department?.department_name ?? "Unassigned",
    email: employee.email ?? "",
    phone: employee.phone ?? "",
    joinDate: employee.joining_date ?? "",
    status: employee.employment_status === "ACTIVE" ? "active" : "inactive",
    avatarColor: ["#1e40af", "#0f766e", "#b45309", "#dc2626", "#065f46"][employee.employee_id % 5],
    profilePictureUrl: employee.profile_picture_url ?? undefined,
  };
}

function mapAttendance(record: ApiAttendance): AttendanceRecord {
  const time = (value: string | null) => value ? new Date(value).toTimeString().slice(0, 5) : undefined;
  return {
    date: record.attendance_date,
    employeeId: record.employee_id,
    status: record.status.toLowerCase() as AttendanceStatus,
    checkIn: time(record.check_in_at),
    checkOut: time(record.check_out_at),
    hours: Number(record.work_hours),
  };
}

function mapLeave(request: ApiLeaveRequest): TimeOffRequest {
  return {
    id: request.leave_request_id,
    employeeId: request.employee_id,
    type: request.leave_type.name,
    from: request.start_date,
    to: request.end_date,
    days: Number(request.number_of_days),
    reason: request.remarks ?? "",
    status: request.status.toLowerCase() as TimeOffStatus,
    attachmentPath: request.attachment_path ?? undefined,
    reviewComment: request.review_comment ?? undefined,
  };
}

function HRDataProvider({ token, onUnauthorized, children }: { token: string; onUnauthorized: () => void; children: React.ReactNode }) {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([]);
  const [requests, setRequests] = useState<TimeOffRequest[]>([]);
  const [dashboard, setDashboard] = useState<ApiDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh() {
    setLoading(true);
    setError("");
    const today = new Date().toISOString().slice(0, 10);
    const results = await Promise.allSettled([
      api.employees(token), api.attendance(today, token), api.leaveRequests(token), api.dashboard(token),
    ]);
    const [employeePage, attendancePage, leavePage, dashboardData] = results;
    if (employeePage.status === "fulfilled") setEmployees(employeePage.value.items.map(mapEmployee));
    if (attendancePage.status === "fulfilled") setAttendance(attendancePage.value.items.map(mapAttendance));
    if (leavePage.status === "fulfilled") setRequests(leavePage.value.items.map(mapLeave));
    if (dashboardData.status === "fulfilled") setDashboard(dashboardData.value);
    const unauthorized = results.some(result => result.status === "rejected" && result.reason instanceof Error && result.reason.message.includes("(401)"));
    if (unauthorized) {
      onUnauthorized();
      return;
    }
    if (results.some(result => result.status === "rejected")) setError("Some live data could not be loaded. Check the backend and try again.");
    setLoading(false);
  }

  useEffect(() => { void refresh(); }, [token, onUnauthorized]);

  return <HRDataContext.Provider value={{ token, employees, attendance, requests, dashboard, loading, error, refresh }}>{children}</HRDataContext.Provider>;
}

// ─── Data ─────────────────────────────────────────────────────────────────────

const EMPLOYEES: Employee[] = [
  { id: 1, name: "Marcus Webb", initials: "MW", role: "Senior Engineer", department: "Engineering", email: "m.webb@dayflow.io", phone: "+1 (555) 012-3456", joinDate: "2021-03-15", status: "active", avatarColor: "#1e40af" },
  { id: 2, name: "Priya Nair", initials: "PN", role: "Product Manager", department: "Product", email: "p.nair@dayflow.io", phone: "+1 (555) 234-5678", joinDate: "2020-07-08", status: "active", avatarColor: "#6d28d9" },
  { id: 3, name: "Joel Ferreira", initials: "JF", role: "UX Designer", department: "Design", email: "j.ferreira@dayflow.io", phone: "+1 (555) 345-6789", joinDate: "2022-01-20", status: "active", avatarColor: "#0f766e" },
  { id: 4, name: "Sandra Okafor", initials: "SO", role: "HR Specialist", department: "HR", email: "s.okafor@dayflow.io", phone: "+1 (555) 456-7890", joinDate: "2019-11-03", status: "active", avatarColor: "#b45309" },
  { id: 5, name: "Derek Cho", initials: "DC", role: "Data Analyst", department: "Analytics", email: "d.cho@dayflow.io", phone: "+1 (555) 567-8901", joinDate: "2023-02-14", status: "active", avatarColor: "#dc2626" },
  { id: 6, name: "Lena Gruber", initials: "LG", role: "Backend Engineer", department: "Engineering", email: "l.gruber@dayflow.io", phone: "+1 (555) 678-9012", joinDate: "2021-09-01", status: "inactive", avatarColor: "#475569" },
  { id: 7, name: "Tariq Hassan", initials: "TH", role: "Marketing Lead", department: "Marketing", email: "t.hassan@dayflow.io", phone: "+1 (555) 789-0123", joinDate: "2022-06-15", status: "active", avatarColor: "#065f46" },
  { id: 8, name: "Yuki Tanaka", initials: "YT", role: "Finance Controller", department: "Finance", email: "y.tanaka@dayflow.io", phone: "+1 (555) 890-1234", joinDate: "2020-04-22", status: "active", avatarColor: "#7c3aed" },
];

const TIME_OFF_REQUESTS: TimeOffRequest[] = [
  { id: 1, employeeId: 1, type: "Annual Leave", from: "2026-08-25", to: "2026-08-29", days: 5, reason: "Family vacation", status: "pending" },
  { id: 2, employeeId: 3, type: "Sick Leave", from: "2026-08-22", to: "2026-08-23", days: 2, reason: "Medical appointment", status: "pending" },
  { id: 3, employeeId: 5, type: "Annual Leave", from: "2026-09-01", to: "2026-09-05", days: 5, reason: "Holiday travel", status: "pending" },
  { id: 4, employeeId: 2, type: "Annual Leave", from: "2026-07-14", to: "2026-07-18", days: 5, reason: "Personal trip", status: "approved" },
  { id: 5, employeeId: 4, type: "Emergency Leave", from: "2026-07-20", to: "2026-07-21", days: 2, reason: "Family emergency", status: "approved" },
  { id: 6, employeeId: 7, type: "Sick Leave", from: "2026-08-05", to: "2026-08-05", days: 1, reason: "Unwell", status: "rejected" },
];

const ATTENDANCE: AttendanceRecord[] = [
  { date: "2025-10-22", employeeId: 1, status: "present", checkIn: "10:00", checkOut: "19:00", hours: 9.0 },
  { date: "2025-10-22", employeeId: 2, status: "present", checkIn: "10:00", checkOut: "19:00", hours: 9.0 },
  { date: "2025-10-22", employeeId: 3, status: "present", checkIn: "10:00", checkOut: "18:30", hours: 8.5 },
  { date: "2025-10-22", employeeId: 4, status: "present", checkIn: "10:00", checkOut: "19:00", hours: 9.0 },
  { date: "2025-10-22", employeeId: 5, status: "present", checkIn: "10:00", checkOut: "19:00", hours: 9.0 },
  { date: "2025-10-22", employeeId: 6, status: "present", checkIn: "09:30", checkOut: "18:30", hours: 9.0 },
  { date: "2025-10-22", employeeId: 7, status: "present", checkIn: "10:00", checkOut: "19:00", hours: 9.0 },
  { date: "2025-10-22", employeeId: 8, status: "present", checkIn: "10:00", checkOut: "19:00", hours: 9.0 },
  { date: "2026-08-22", employeeId: 1, status: "present", checkIn: "08:52", checkOut: "17:38", hours: 8.77 },
  { date: "2026-08-22", employeeId: 2, status: "present", checkIn: "09:05", checkOut: "18:10", hours: 9.08 },
  { date: "2026-08-22", employeeId: 3, status: "leave" },
  { date: "2026-08-22", employeeId: 4, status: "present", checkIn: "08:30", checkOut: "17:00", hours: 8.5 },
  { date: "2026-08-22", employeeId: 5, status: "present", checkIn: "09:20", checkOut: "17:55", hours: 8.58 },
  { date: "2026-08-22", employeeId: 6, status: "absent" },
  { date: "2026-08-22", employeeId: 7, status: "present", checkIn: "08:45", checkOut: "17:30", hours: 8.75 },
  { date: "2026-08-22", employeeId: 8, status: "present", checkIn: "09:00", checkOut: "18:05", hours: 9.08 },
  { date: "2026-08-21", employeeId: 1, status: "present", checkIn: "08:48", checkOut: "17:30", hours: 8.7 },
  { date: "2026-08-21", employeeId: 2, status: "present", checkIn: "09:00", checkOut: "18:00", hours: 9.0 },
  { date: "2026-08-21", employeeId: 3, status: "present", checkIn: "08:55", checkOut: "17:40", hours: 8.75 },
  { date: "2026-08-21", employeeId: 4, status: "absent" },
  { date: "2026-08-21", employeeId: 5, status: "present", checkIn: "09:10", checkOut: "17:50", hours: 8.67 },
  { date: "2026-08-21", employeeId: 6, status: "absent" },
  { date: "2026-08-21", employeeId: 7, status: "present", checkIn: "08:40", checkOut: "17:20", hours: 8.67 },
  { date: "2026-08-21", employeeId: 8, status: "leave" },
];

const SALARY_COMPONENTS = [
  { label: "Base Salary", amount: 7500, type: "earning" },
  { label: "Housing Allowance", amount: 800, type: "earning" },
  { label: "Transport Allowance", amount: 250, type: "earning" },
  { label: "Performance Bonus", amount: 600, type: "earning" },
  { label: "Federal Income Tax", amount: -1240, type: "deduction" },
  { label: "Social Security", amount: -558, type: "deduction" },
  { label: "Health Insurance", amount: -280, type: "deduction" },
  { label: "Retirement (401k)", amount: -375, type: "deduction" },
];

// ─── Feedback Modal (Animated Tick / Cross / Info) ─────────────────────────

export interface FeedbackState {
  type: "success" | "error" | "info";
  title: string;
  message: string;
  details?: string;
}

export function FeedbackModal({ feedback, onClose }: { feedback: FeedbackState; onClose: () => void }) {
  const { type, title, message, details } = feedback;
  return (
    <div className="df-feedback-overlay" onClick={onClose}>
      <div className="df-feedback-modal" onClick={e => e.stopPropagation()}>
        <div className={`df-icon-box ${type}`}>
          <svg className="df-svg-icon" viewBox="0 0 52 52">
            <circle className={`df-circle-path ${type}`} cx="26" cy="26" r="23" fill="none" />
            {type === "success" && (
              <path className="df-tick-path" fill="none" d="M14 27 l7 7 l17 -17" />
            )}
            {type === "error" && (
              <>
                <path className="df-cross-path1" fill="none" d="M16 16 L36 36" />
                <path className="df-cross-path2" fill="none" d="M36 16 L16 36" />
              </>
            )}
            {type === "info" && (
              <>
                <circle cx="26" cy="17" r="2.5" fill="#3B82F6" />
                <path className="df-info-path" fill="none" d="M26 24 L26 36" />
              </>
            )}
          </svg>
        </div>
        <h3 style={{ fontSize: 20, fontWeight: 700, margin: "0 0 8px", color: "var(--df-navy)" }}>{title}</h3>
        <p style={{ fontSize: 14, color: "var(--df-text-muted)", margin: "0 0 16px", lineHeight: 1.5 }}>{message}</p>
        {details && (
          <div style={{
            background: type === "success" ? "#ECFDF5" : type === "error" ? "#FEF2F2" : "#F1F5F9",
            border: `1px solid ${type === "success" ? "#A7F3D0" : type === "error" ? "#FECACA" : "#CBD5E1"}`,
            borderRadius: 8,
            padding: "10px 14px",
            fontSize: 13,
            color: type === "success" ? "#065F46" : type === "error" ? "#991B1B" : "#334155",
            fontWeight: 600,
            marginBottom: 20,
            fontFamily: "monospace",
            wordBreak: "break-all"
          }}>
            {details}
          </div>
        )}
        <button
          className={type === "error" ? "df-btn-secondary w-100 py-2" : "df-btn-primary w-100 py-2"}
          style={{ borderRadius: 8, fontSize: 14, fontWeight: 600, cursor: "pointer" }}
          onClick={onClose}
        >
          {type === "success" ? "Done" : type === "error" ? "Close" : "OK"}
        </button>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function Avatar({ emp, size = 32 }: { emp: Employee; size?: number }) {
  return (
    <div
      className="df-avatar"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.37,
        background: emp.avatarColor + "22",
        color: emp.avatarColor,
        border: `1.5px solid ${emp.avatarColor}44`,
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: "50%"
      }}
    >
      {emp.profilePictureUrl ? (
        <img
          src={`http://localhost:8000${emp.profilePictureUrl}`}
          alt={emp.name}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        emp.initials
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: AttendanceStatus | TimeOffStatus }) {
  const map: Record<string, { cls: string; icon: string; label: string }> = {
    present:  { cls: "df-badge-present",  icon: "bi-check-circle-fill", label: "Present" },
    absent:   { cls: "df-badge-absent",   icon: "bi-x-circle-fill",     label: "Absent" },
    leave:    { cls: "df-badge-leave",    icon: "bi-calendar-event-fill",label: "On Leave" },
    holiday:  { cls: "df-badge-leave",    icon: "bi-sun-fill",           label: "Holiday" },
    pending:  { cls: "df-badge-pending",  icon: "bi-hourglass-split",    label: "Pending" },
    approved: { cls: "df-badge-approved", icon: "bi-check-circle-fill",  label: "Approved" },
    rejected: { cls: "df-badge-rejected", icon: "bi-x-circle-fill",      label: "Rejected" },
  };
  const { cls, icon, label } = map[status] ?? map.absent;
  return (
    <span className={`df-badge ${cls}`}>
      <i className={`bi ${icon}`} style={{ fontSize: 11 }} />
      {label}
    </span>
  );
}

function formatDate(d: string) {
  return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

function timeToFraction(t: string) {
  const [h, m] = t.split(":").map(Number);
  return (h * 60 + m - 7 * 60) / (12 * 60); // 07:00–19:00 window
}

// ─── Pages ────────────────────────────────────────────────────────────────────

function Dashboard({ onNav }: { onNav: (p: Page, id?: number) => void }) {
  const { employees, attendance, requests, dashboard } = useHRData();
  const today = new Date().toISOString().slice(0, 10);
  const activeCount = dashboard?.active_employees ?? employees.filter(e => e.status === "active").length;
  const todayAtt = attendance.filter(a => a.date === today);
  const presentToday = todayAtt.filter(a => a.status === "present").length;
  const pendingLeave = dashboard?.pending_leave_requests ?? requests.filter(r => r.status === "pending").length;
  const avgHours = (todayAtt.filter(a => a.hours).reduce((s, a) => s + (a.hours ?? 0), 0) /
    todayAtt.filter(a => a.hours).length).toFixed(1);

  return (
    <div className="df-page">
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h1 className="df-section-title">Good morning, Sarah</h1>
          <p className="df-section-sub mt-1">Friday, 22 August 2026 · Here's what's on your plate today.</p>
        </div>
        <button className="df-btn-primary" onClick={() => onNav("employees")}>
          <i className="bi bi-person-plus-fill" /> Add Employee
        </button>
      </div>

      {/* Stat cards */}
      <div className="row g-3 mb-4">
        {[
          { label: "Total Employees", value: activeCount, sub: "1 inactive", icon: "bi-people-fill", color: "#2563EB", onClick: () => onNav("employees") },
          { label: "Present Today", value: dashboard?.present_today ?? presentToday, sub: `of ${employees.length} expected`, icon: "bi-person-check-fill", color: "#059669", onClick: () => onNav("attendance") },
          { label: "On Leave Today", value: dashboard?.on_leave_today ?? todayAtt.filter(a => a.status === "leave").length, sub: "approved requests", icon: "bi-calendar-event-fill", color: "#7C3AED", onClick: () => onNav("timeoff") },
          { label: "Pending Approvals", value: pendingLeave, sub: "time-off requests", icon: "bi-hourglass-split", color: "#D97706", onClick: () => onNav("timeoff") },
        ].map(c => (
          <div key={c.label} className="col-6 col-xl-3">
            <div className="df-stat-card" style={{ cursor: "pointer" }} onClick={c.onClick}>
              <div className="d-flex align-items-start justify-content-between">
                <span className="df-stat-label">{c.label}</span>
                <div style={{
                  width: 36, height: 36, borderRadius: 8,
                  background: c.color + "18",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: c.color, fontSize: 17,
                }}>
                  <i className={`bi ${c.icon}`} />
                </div>
              </div>
              <div className="df-stat-value tabnum mt-1">{c.value}</div>
              <div className="df-stat-sub">{c.sub}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="row g-3">
        {/* Today's attendance summary */}
        <div className="col-12 col-lg-7">
          <div className="df-card p-0">
            <div className="d-flex align-items-center justify-content-between px-4 pt-4 pb-3" style={{ borderBottom: "1px solid var(--df-border)" }}>
              <div className="df-section-title" style={{ fontSize: 15 }}>Today's Attendance</div>
              <button className="df-btn-secondary" style={{ padding: "5px 12px" }} onClick={() => onNav("attendance")}>
                <i className="bi bi-arrow-right" /> View all
              </button>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="df-table df-table-compact">
                <thead>
                  <tr>
                    <th>Employee</th>
                    <th>Status</th>
                    <th>Check-in</th>
                    <th>Check-out</th>
                    <th>Timeline</th>
                    <th className="tabnum">Hours</th>
                  </tr>
                </thead>
                <tbody>
                  {todayAtt.map(a => {
                    const emp = employees.find(e => e.id === a.employeeId);
                    if (!emp) return null;
                    const fillLeft = a.checkIn ? timeToFraction(a.checkIn) * 100 : 0;
                    const fillRight = a.checkOut ? timeToFraction(a.checkOut) * 100 : 0;
                    return (
                      <tr key={a.employeeId} style={{ cursor: "pointer" }} onClick={() => onNav("employee-detail", a.employeeId)}>
                        <td>
                          <div className="d-flex align-items-center gap-2">
                            <Avatar emp={emp} size={28} />
                            <div>
                              <div style={{ fontWeight: 600, fontSize: 13 }}>{emp.name}</div>
                              <div style={{ fontSize: 11, color: "var(--df-text-muted)" }}>{emp.department}</div>
                            </div>
                          </div>
                        </td>
                        <td><StatusBadge status={a.status} /></td>
                        <td className="tabnum" style={{ color: a.checkIn ? "var(--df-navy)" : "var(--df-text-sub)" }}>{a.checkIn ?? "—"}</td>
                        <td className="tabnum" style={{ color: a.checkOut ? "var(--df-navy)" : "var(--df-text-sub)" }}>{a.checkOut ?? "—"}</td>
                        <td>
                          {a.checkIn ? (
                            <div className="df-timeline-bar" style={{ width: 90 }}>
                              <div className="df-timeline-fill" style={{ left: `${fillLeft}%`, right: `${100 - fillRight}%` }} />
                            </div>
                          ) : (
                            <span style={{ color: "var(--df-text-sub)", fontSize: 12 }}>—</span>
                          )}
                        </td>
                        <td className="tabnum" style={{ fontWeight: 600 }}>{a.hours ? a.hours.toFixed(1) : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Pending approvals */}
        <div className="col-12 col-lg-5">
          <div className="df-card" style={{ height: "100%" }}>
            <div className="d-flex align-items-center justify-content-between px-4 pt-4 pb-3" style={{ borderBottom: "1px solid var(--df-border)" }}>
              <div className="df-section-title" style={{ fontSize: 15 }}>Pending Approvals</div>
              <span className="df-badge df-badge-pending">{pendingLeave} new</span>
            </div>
            <div className="p-3">
              {requests.filter(r => r.status === "pending").length === 0 ? (
                <div className="df-empty">
                  <i className="bi bi-inbox df-empty-icon" />
                  <p className="df-empty-title">No pending requests</p>
                  <p className="df-empty-sub">All time-off requests have been reviewed.</p>
                </div>
              ) : (
                requests.filter(r => r.status === "pending").map(r => {
                  const emp = employees.find(e => e.id === r.employeeId);
                  if (!emp) return null;
                  return (
                    <div key={r.id} className="d-flex align-items-start gap-3 p-3 mb-2 rounded" style={{ background: "var(--df-surface)", border: "1px solid var(--df-border)" }}>
                      <Avatar emp={emp} size={34} />
                      <div className="flex-fill" style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>{emp.name}</div>
                        <div style={{ fontSize: 12, color: "var(--df-text-muted)" }}>{r.type} · {r.days}d · {formatDate(r.from)} – {formatDate(r.to)}</div>
                      </div>
                      <button className="df-btn-approve" onClick={() => onNav("timeoff")} title="Review"><i className="bi bi-arrow-right" /></button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function EmployeeList({ onNav }: { onNav: (p: Page, id?: number) => void }) {
  const { employees, token, refresh } = useHRData();
  const [search, setSearch] = useState("");
  const [dept, setDept] = useState("All");
  const [showInvite, setShowInvite] = useState(false);
  const [departments, setDepartments] = useState<ApiDepartment[]>([]);
  const [designations, setDesignations] = useState<ApiDesignation[]>([]);
  const [inviteError, setInviteError] = useState("");
  const [inviteMessage, setInviteMessage] = useState("");
  const [inviteBusy, setInviteBusy] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);
  const depts = ["All", ...Array.from(new Set(employees.map(e => e.department)))];
  const filtered = employees.filter(e =>
    (dept === "All" || e.department === dept) &&
    (e.name.toLowerCase().includes(search.toLowerCase()) || e.role.toLowerCase().includes(search.toLowerCase()))
  );

  useEffect(() => {
    if (!showInvite) return;
    void Promise.all([api.departments(token), api.designations(token)])
      .then(([departmentPage, designationPage]) => {
        setDepartments(departmentPage.items.filter(item => item.is_active));
        setDesignations(designationPage.items.filter(item => item.is_active));
      })
      .catch(error => setInviteError(error instanceof Error ? error.message : "Unable to load reference data"));
  }, [showInvite, token]);

  async function submitInvite(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setInviteBusy(true);
    setInviteError("");
    setInviteMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const result = await api.inviteEmployee({
        email: String(form.get("email")),
        first_name: String(form.get("first_name")),
        last_name: String(form.get("last_name")),
        role: String(form.get("role")) as "HR" | "ADMIN",
        joining_date: String(form.get("joining_date")),
        department_id: Number(form.get("department_id")) || undefined,
        designation_id: Number(form.get("designation_id")) || undefined,
      }, token);
      await refresh();
      setShowInvite(false);
      setFeedback({
        type: "success",
        title: "Invitation Sent!",
        message: result.message || "Invitation email with credentials has been sent.",
        details: `Employee Code: ${result.employee_code}`,
      });
      event.currentTarget.reset();
    } catch (error) {
      setFeedback({
        type: "error",
        title: "Invitation Failed",
        message: error instanceof Error ? error.message : "Unable to invite employee",
      });
    } finally {
      setInviteBusy(false);
    }
  }

  return (
    <div className="df-page">
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h1 className="df-section-title">Employees</h1>
          <p className="df-section-sub mt-1">{employees.filter(e => e.status === "active").length} active · {employees.filter(e => e.status === "inactive").length} inactive</p>
        </div>
        <button className="df-btn-primary" onClick={() => { setShowInvite(true); setInviteError(""); setInviteMessage(""); }}><i className="bi bi-person-plus-fill" /> Add Employee</button>
      </div>

      <div className="d-flex gap-2 mb-3 flex-wrap">
        <div className="position-relative">
          <i className="bi bi-search position-absolute" style={{ left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--df-text-muted)", fontSize: 13 }} />
          <input className="df-input" placeholder="Search employees..." value={search} onChange={e => setSearch(e.target.value)} style={{ paddingLeft: 32, width: 240 }} />
        </div>
        <select className="df-input" value={dept} onChange={e => setDept(e.target.value)} style={{ width: "auto" }}>
          {depts.map(d => <option key={d}>{d}</option>)}
        </select>
      </div>

      <div className="df-table-wrap">
        <table className="df-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Department</th>
              <th>Role</th>
              <th>Email</th>
              <th>Join Date</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="df-empty">
                    <i className="bi bi-person-x df-empty-icon" />
                    <p className="df-empty-title">No employees found</p>
                    <p className="df-empty-sub">Try adjusting your search or department filter.</p>
                  </div>
                </td>
              </tr>
            ) : filtered.map(emp => (
              <tr key={emp.id} style={{ cursor: "pointer" }} onClick={() => onNav("employee-detail", emp.id)}>
                <td>
                  <div className="d-flex align-items-center gap-2">
                    <Avatar emp={emp} size={32} />
                    <span style={{ fontWeight: 600 }}>{emp.name}</span>
                  </div>
                </td>
                <td style={{ color: "var(--df-text-muted)" }}>{emp.department}</td>
                <td>{emp.role}</td>
                <td style={{ color: "var(--df-text-muted)", fontSize: 13 }}>{emp.email}</td>
                <td className="tabnum" style={{ color: "var(--df-text-muted)", fontSize: 13 }}>{formatDate(emp.joinDate)}</td>
                <td>
                  <span className={`df-badge ${emp.status === "active" ? "df-badge-present" : "df-badge-absent"}`}>
                    <i className={`bi ${emp.status === "active" ? "bi-circle-fill" : "bi-circle"}`} style={{ fontSize: 7 }} />
                    {emp.status === "active" ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <button className="df-btn-secondary" style={{ padding: "4px 10px", fontSize: 12 }} onClick={e => { e.stopPropagation(); onNav("employee-detail", emp.id); }}>
                    <i className="bi bi-eye" /> View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showInvite && (
        <div className="df-modal-overlay" onClick={() => setShowInvite(false)}>
          <div className="df-modal-content p-4" onClick={event => event.stopPropagation()}>
            <div className="d-flex align-items-center justify-content-between mb-3 pb-2 border-bottom">
              <div>
                <h2 className="df-section-title mb-1" style={{ fontSize: 18 }}>Add Employee</h2>
                <p className="df-section-sub mb-0">Invite a team member to Dayflow.</p>
              </div>
              <button className="btn-close" onClick={() => setShowInvite(false)} aria-label="Close" />
            </div>
            {inviteError && <div className="alert alert-danger py-2">{inviteError}</div>}
            {inviteMessage && <div className="alert alert-success py-2">{inviteMessage}</div>}
            <form onSubmit={submitInvite}>
              <div className="d-flex gap-2">
                <div className="flex-fill"><label className="form-label">First name</label><input className="df-input w-100 mb-3" name="first_name" required /></div>
                <div className="flex-fill"><label className="form-label">Last name</label><input className="df-input w-100 mb-3" name="last_name" required /></div>
              </div>
              <label className="form-label">Work email</label>
              <input className="df-input w-100 mb-3" name="email" type="email" required />
              <div className="d-flex gap-2">
                <div className="flex-fill"><label className="form-label">Role</label><select className="df-input w-100 mb-3" name="role" defaultValue="HR"><option value="HR">HR</option><option value="ADMIN">Admin</option></select></div>
                <div className="flex-fill"><label className="form-label">Joining date</label><input className="df-input w-100 mb-3" name="joining_date" type="date" required /></div>
              </div>
              <div className="d-flex gap-2">
                <div className="flex-fill"><label className="form-label">Department</label><select className="df-input w-100 mb-3" name="department_id" defaultValue=""><option value="">Unassigned</option>{departments.map(item => <option key={item.department_id} value={item.department_id}>{item.department_name}</option>)}</select></div>
                <div className="flex-fill"><label className="form-label">Designation</label><select className="df-input w-100 mb-3" name="designation_id" defaultValue=""><option value="">Unassigned</option>{designations.map(item => <option key={item.designation_id} value={item.designation_id}>{item.title}</option>)}</select></div>
              </div>
              <div className="d-flex justify-content-end gap-2 mt-3 pt-3 border-top"><button type="button" className="df-btn-secondary" onClick={() => setShowInvite(false)}>Cancel</button><button className="df-btn-primary" disabled={inviteBusy}>{inviteBusy ? "Sending..." : "Send invitation"}</button></div>
            </form>
          </div>
        </div>
      )}
      {feedback && <FeedbackModal feedback={feedback} onClose={() => setFeedback(null)} />}
    </div>
  );
}

interface SkillItem {
  id: string;
  name: string;
}

interface CertificationItem {
  id: string;
  title: string;
  issuer: string;
  issueDate: string;
}

interface ResumeDetails {
  about: string;
  whatILove: string;
  interests: string;
  skills: SkillItem[];
  certifications: CertificationItem[];
}

const INITIAL_RESUME_DATA: Record<number, ResumeDetails> = {
  1: {
    about: "Senior Full-Stack Engineer with 6+ years of experience designing and scaling web applications, microservices, and distributed systems. Dedicated to writing clean, maintainable code and building seamless user experiences.",
    whatILove: "Solving complex technical challenges alongside an incredible team. I thrive on translating ambitious product requirements into performant, elegant code that directly impacts our users.",
    interests: "Open-source contributions, technical blogging, competitive chess, marathon running, and experimenting with vintage synthesizer audio hardware.",
    skills: [
      { id: "s1", name: "React / Next.js" },
      { id: "s2", name: "TypeScript" },
      { id: "s3", name: "Python / FastAPI" },
      { id: "s4", name: "Node.js & Express" },
      { id: "s5", name: "PostgreSQL & Redis" },
      { id: "s6", name: "Docker & Kubernetes" },
      { id: "s7", name: "REST & GraphQL APIs" },
      { id: "s8", name: "CI/CD Pipelines" },
    ],
    certifications: [
      { id: "c1", title: "AWS Certified Solutions Architect – Associate", issuer: "Amazon Web Services", issueDate: "2024-03" },
      { id: "c2", title: "Certified Scrum Developer (CSD)", issuer: "Scrum Alliance", issueDate: "2023-09" },
      { id: "c3", title: "Meta Front-End Developer Certificate", issuer: "Meta / Coursera", issueDate: "2022-11" },
    ]
  },
  2: {
    about: "Experienced Product Manager with 5+ years driving end-to-end product lifecycles across SaaS platforms, mobile apps, and enterprise tools.",
    whatILove: "Turning complex user pain points into simple, intuitive product experiences and launching high-impact feature releases.",
    interests: "Product analytics, UX prototyping, photography, podcasting, and hiking national parks.",
    skills: [
      { id: "s1", name: "Product Strategy" },
      { id: "s2", name: "Agile & Scrum" },
      { id: "s3", name: "User Research" },
      { id: "s4", name: "Mixpanel & Analytics" },
      { id: "s5", name: "Figma Wireframing" },
    ],
    certifications: [
      { id: "c1", title: "Certified Product Manager (CPM)", issuer: "AIPMM", issueDate: "2023-05" },
      { id: "c2", title: "Professional Scrum Product Owner I", issuer: "Scrum.org", issueDate: "2022-08" },
    ]
  },
  3: {
    about: "Lead UX/UI Designer focused on building human-centric digital interfaces, design systems, and seamless user journeys.",
    whatILove: "Crafting beautiful micro-interactions, cohesive typography, and intuitive design components.",
    interests: "Design tokens, UI animation, digital painting, and modern interior architecture.",
    skills: [
      { id: "s1", name: "Figma & Design Systems" },
      { id: "s2", name: "UI/UX Architecture" },
      { id: "s3", name: "User Research" },
      { id: "s4", name: "Framer Motion" },
    ],
    certifications: [
      { id: "c1", title: "Google UX Design Certificate", issuer: "Google", issueDate: "2023-01" },
      { id: "c2", title: "Nielsen Norman Group UX Master", issuer: "NN/g", issueDate: "2024-02" },
    ]
  },
  4: {
    about: "People-first HR Specialist with a focus on talent acquisition, employee onboarding, company culture, and workplace compliance.",
    whatILove: "Helping team members thrive and grow in their careers while building an inclusive, supportive workplace.",
    interests: "Organizational psychology, career mentoring, community volunteering, and sourdough baking.",
    skills: [
      { id: "s1", name: "Talent Acquisition" },
      { id: "s2", name: "HRIS & ATS Management" },
      { id: "s3", name: "Employee Engagement" },
      { id: "s4", name: "Labor Law & Compliance" },
    ],
    certifications: [
      { id: "c1", title: "SHRM Certified Professional (SHRM-CP)", issuer: "SHRM", issueDate: "2022-06" },
      { id: "c2", title: "HRCI Professional in Human Resources", issuer: "HRCI", issueDate: "2021-10" },
    ]
  },
  5: {
    about: "Data Analyst skilled in transforming raw data streams into actionable business insights through SQL, Python, and dashboards.",
    whatILove: "Uncovering hidden trends in business metrics and telling compelling stories with data visualization.",
    interests: "Machine learning, statistics puzzles, fantasy football analytics, and cycling.",
    skills: [
      { id: "s1", name: "SQL & Data Warehousing" },
      { id: "s2", name: "Python (Pandas, NumPy)" },
      { id: "s3", name: "Tableau & PowerBI" },
      { id: "s4", name: "A/B Testing & Statistics" },
    ],
    certifications: [
      { id: "c1", title: "Google Data Analytics Certificate", issuer: "Google", issueDate: "2023-07" },
      { id: "c2", title: "Tableau Desktop Specialist", issuer: "Tableau", issueDate: "2023-11" },
    ]
  },
  6: {
    about: "Backend Engineer specializing in distributed databases, microservices architecture, and high-throughput server systems.",
    whatILove: "Designing robust server architecture that handles millions of requests seamlessly with low latency.",
    interests: "Go, Rust, distributed algorithms, retro gaming, and mechanical puzzles.",
    skills: [
      { id: "s1", name: "Go & Python" },
      { id: "s2", name: "Kafka & RabbitMQ" },
      { id: "s3", name: "PostgreSQL & Redis" },
    ],
    certifications: [
      { id: "c1", title: "Certified Kubernetes Administrator (CKA)", issuer: "CNCF", issueDate: "2023-04" },
    ]
  },
  7: {
    about: "Growth Marketing Lead with expertise in multi-channel campaign strategy, SEO/SEM, brand positioning, and content marketing.",
    whatILove: "Executing data-driven marketing experiments that accelerate customer acquisition and brand growth.",
    interests: "Growth hacking, copywriting, podcast production, tennis, and coffee brewing.",
    skills: [
      { id: "s1", name: "Growth Strategy & Funnels" },
      { id: "s2", name: "SEO / SEM & Google Ads" },
      { id: "s3", name: "Content Marketing" },
    ],
    certifications: [
      { id: "c1", title: "Google Ads Search Certification", issuer: "Google", issueDate: "2023-08" },
      { id: "c2", title: "HubSpot Inbound Marketing Certified", issuer: "HubSpot", issueDate: "2022-09" },
    ]
  },
  8: {
    about: "Finance Controller with over 7 years managing enterprise financial planning, budget forecasting, and payroll compliance.",
    whatILove: "Optimizing financial workflows and providing clear, strategic fiscal guidance that ensures operational efficiency.",
    interests: "Financial modeling, personal finance coaching, chess, and acoustic guitar.",
    skills: [
      { id: "s1", name: "Financial Forecasting" },
      { id: "s2", name: "Budgeting & Cost Control" },
      { id: "s3", name: "QuickBooks & ERP Systems" },
    ],
    certifications: [
      { id: "c1", title: "Certified Public Accountant (CPA)", issuer: "AICPA", issueDate: "2021-04" },
    ]
  }
};

function EmployeeDetail({ empId, onBack, initialTab = "resume" }: { empId: number; onBack: () => void; initialTab?: EmployeeTab }) {
  const { employees, token } = useHRData();
  const [tab, setTab] = useState<EmployeeTab>(initialTab);
  const emp = employees.find(e => e.id === empId) ?? employees[0];
  const [salary, setSalary] = useState<ApiSalary | null>(null);

  useEffect(() => {
    void api.salary(empId, token).then(setSalary).catch(() => setSalary(null));
  }, [empId, token]);

  useEffect(() => {
    setTab(initialTab);
  }, [empId, initialTab]);

  // Resume state mapping
  const [resumeMap, setResumeMap] = useState<Record<number, ResumeDetails>>(INITIAL_RESUME_DATA);
  const currentResume = resumeMap[empId] || {
    about: "",
    whatILove: "",
    interests: "",
    skills: [],
    certifications: [],
  };

  // Modals state
  const [editModalField, setEditModalField] = useState<"about" | "whatILove" | "interests" | "all" | null>(null);
  const [aboutInput, setAboutInput] = useState("");
  const [whatILoveInput, setWhatILoveInput] = useState("");
  const [interestsInput, setInterestsInput] = useState("");

  const [showSkillModal, setShowSkillModal] = useState(false);
  const [newSkillName, setNewSkillName] = useState("");

  const [showCertModal, setShowCertModal] = useState(false);
  const [newCertTitle, setNewCertTitle] = useState("");
  const [newCertIssuer, setNewCertIssuer] = useState("");
  const [newCertDate, setNewCertDate] = useState("");

  // Salary Info State
  const [monthWage, setMonthWage] = useState<number>(50000);
  
  // Persist working days & break time in localStorage per employee
  const [workingDaysWeek, setWorkingDaysWeek] = useState<number>(() => {
    const saved = localStorage.getItem(`working_days_emp_${empId}`);
    return saved ? Number(saved) : 5;
  });
  const [breakTimeHours, setBreakTimeHours] = useState<number>(() => {
    const saved = localStorage.getItem(`break_time_emp_${empId}`);
    return saved ? Number(saved) : 1;
  });
  
  const [pfPct, setPfPct] = useState<number>(12);
  const [profTaxVal, setProfTaxVal] = useState<number>(200);

  useEffect(() => {
    const savedDays = localStorage.getItem(`working_days_emp_${empId}`);
    setWorkingDaysWeek(savedDays ? Number(savedDays) : 5);
    const savedBreak = localStorage.getItem(`break_time_emp_${empId}`);
    setBreakTimeHours(savedBreak ? Number(savedBreak) : 1);
  }, [empId]);

  useEffect(() => {
    if (!salary) return;
    setMonthWage(Number(salary.monthly_wage));
    
    const employeePf = salary.components.find(component => component.name.toLowerCase().includes("provident") || component.name.toLowerCase() === "pf");
    if (employeePf) {
      const basic = Number(salary.monthly_wage) * 0.50;
      if (basic > 0) {
        setPfPct(Math.round((Number(employeePf.computed_amount) * 100 / basic) * 100) / 100);
      }
    }
    
    const profTax = salary.components.find(component => component.name.toLowerCase().includes("professional tax") || component.name.toLowerCase() === "pt");
    if (profTax) {
      setProfTaxVal(Number(profTax.fixed_amount ?? profTax.computed_amount));
    }
  }, [salary]);

  // Automatic Salary Calculations based on image
  const yearlyWage = monthWage * 12;
  const basicVal = monthWage * 0.50;
  const basicPctStr = "50.00 %";

  const hraVal = basicVal * 0.50;
  const hraPctStr = "50.00 % of Basic";

  const stdVal = monthWage * 0.15;
  const stdPctStr = "15.00 %";

  const perfVal = basicVal * 0.0933;
  const perfPctStr = "9.33 % of Basic";

  const ltaVal = basicVal * 0.0933;
  const ltaPctStr = "9.33 % of Basic";

  const fixedVal = Math.max(0, monthWage - (basicVal + hraVal + stdVal + perfVal + ltaVal));
  const fixedPctVal = monthWage > 0 ? (fixedVal / monthWage) * 100 : 0;
  const fixedPctStr = `${fixedPctVal.toFixed(2)} %`;

  const employeePfVal = basicVal * (pfPct / 100);
  const employerPfVal = basicVal * (pfPct / 100);
  const totalDeductionsVal = employeePfVal + profTaxVal;
  const netSalaryVal = monthWage - totalDeductionsVal;

  const [savingSalary, setSavingSalary] = useState(false);
  const [salaryFeedback, setSalaryFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  async function handleSaveSalary() {
    setSavingSalary(true);
    setSalaryFeedback(null);
    try {
      const todayIso = new Date().toISOString().split("T")[0];
      const payload = {
        monthly_wage: monthWage,
        wage_type: "MONTHLY",
        effective_from: salary?.effective_from || todayIso,
        components: [
          { name: "Basic Salary", type: "EARNING", calculation_type: "PERCENTAGE", percentage: 50 },
          { name: "House Rent Allowance", type: "EARNING", calculation_type: "PERCENTAGE", percentage: 25 },
          { name: "Standard Allowance", type: "EARNING", calculation_type: "PERCENTAGE", percentage: 15 },
          { name: "Performance Bonus", type: "EARNING", calculation_type: "FIXED", fixed_amount: Math.round(perfVal * 100) / 100 },
          { name: "Leave Travel Allowance", type: "EARNING", calculation_type: "FIXED", fixed_amount: Math.round(ltaVal * 100) / 100 },
          { name: "Fixed Allowance", type: "EARNING", calculation_type: "FIXED", fixed_amount: Math.round(fixedVal * 100) / 100 },
          { name: "Employee PF", type: "DEDUCTION", calculation_type: "FIXED", fixed_amount: Math.round(employeePfVal * 100) / 100 },
          { name: "Employer PF", type: "EMPLOYER_CONTRIBUTION", calculation_type: "FIXED", fixed_amount: Math.round(employerPfVal * 100) / 100 },
          { name: "Professional Tax", type: "DEDUCTION", calculation_type: "FIXED", fixed_amount: profTaxVal },
        ],
      };
      const updated = await api.updateSalary(empId, payload, token);
      setSalary(updated);
      setSalaryFeedback({ type: "success", message: "Salary structure updated and saved successfully!" });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to update salary structure";
      setSalaryFeedback({ type: "error", message: msg });
    } finally {
      setSavingSalary(false);
    }
  }


  function openAboutModal(field: "about" | "whatILove" | "interests" | "all" = "all") {
    setEditModalField(field);
    setAboutInput(currentResume.about);
    setWhatILoveInput(currentResume.whatILove);
    setInterestsInput(currentResume.interests);
  }

  function handleSaveAbout() {
    setResumeMap(prev => ({
      ...prev,
      [empId]: {
        ...currentResume,
        about: aboutInput,
        whatILove: whatILoveInput,
        interests: interestsInput,
      }
    }));
    setEditModalField(null);
  }

  function handleAddSkill(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!newSkillName.trim()) return;
    const newSkill: SkillItem = {
      id: "s_" + Date.now(),
      name: newSkillName.trim(),
    };
    setResumeMap(prev => ({
      ...prev,
      [empId]: {
        ...currentResume,
        skills: [...currentResume.skills, newSkill],
      }
    }));
    setNewSkillName("");
    setShowSkillModal(false);
  }

  function handleRemoveSkill(skillId: string) {
    setResumeMap(prev => ({
      ...prev,
      [empId]: {
        ...currentResume,
        skills: currentResume.skills.filter(s => s.id !== skillId),
      }
    }));
  }

  function handleAddCert(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!newCertTitle.trim()) return;
    const newCert: CertificationItem = {
      id: "c_" + Date.now(),
      title: newCertTitle.trim(),
      issuer: newCertIssuer.trim() || "Independent",
      issueDate: newCertDate.trim() || new Date().toISOString().substring(0, 7),
    };
    setResumeMap(prev => ({
      ...prev,
      [empId]: {
        ...currentResume,
        certifications: [...currentResume.certifications, newCert],
      }
    }));
    setNewCertTitle("");
    setNewCertIssuer("");
    setNewCertDate("");
    setShowCertModal(false);
  }

  function handleRemoveCert(certId: string) {
    setResumeMap(prev => ({
      ...prev,
      [empId]: {
        ...currentResume,
        certifications: currentResume.certifications.filter(c => c.id !== certId),
      }
    }));
  }

  return (
    <div className="df-page">
      <div className="d-flex align-items-center gap-3 mb-4">
        <button className="df-btn-secondary" onClick={onBack} style={{ padding: "5px 10px" }}>
          <i className="bi bi-arrow-left" />
        </button>
        <div className="d-flex align-items-center gap-3">
          <Avatar emp={emp} size={44} />
          <div>
            <h1 className="df-section-title" style={{ fontSize: 18 }}>{emp.name}</h1>
            <p className="df-section-sub mt-0">{emp.role} · {emp.department}</p>
          </div>
        </div>
        <div className="ms-auto">
          <StatusBadge status={emp.status === "active" ? "present" : "absent"} />
        </div>
      </div>

      <div className="df-card">
        <div className="df-tabs px-3">
          {([
            { key: "resume", label: "Resume", icon: "bi-person-lines-fill" },
            { key: "private", label: "Private Info", icon: "bi-shield-lock-fill" },
            { key: "salary", label: "Salary Info", icon: "bi-cash-stack" },
          ] as { key: EmployeeTab; label: string; icon: string }[]).map(t => (
            <button key={t.key} className={`df-tab ${tab === t.key ? "active" : ""}`} onClick={() => setTab(t.key)}>
              <i className={`bi ${t.icon}`} style={{ fontSize: 13 }} /> {t.label}
            </button>
          ))}
        </div>

        <div className="p-4">
          {tab === "resume" && (
            <div>
              {/* Work details summary ribbon */}
              <div className="p-3 mb-4 rounded-3 d-flex flex-wrap align-items-center justify-content-between gap-3" style={{ background: "var(--df-surface)", border: "1px solid var(--df-border)" }}>
                <div className="d-flex align-items-center gap-4 flex-wrap">
                  <div>
                    <span style={{ fontSize: 11, color: "var(--df-text-muted)", fontWeight: 600, display: "block" }}>Department</span>
                    <span style={{ fontWeight: 600, color: "var(--df-navy)" }}><i className="bi bi-building me-1 text-primary" /> {emp.department}</span>
                  </div>
                  <div>
                    <span style={{ fontSize: 11, color: "var(--df-text-muted)", fontWeight: 600, display: "block" }}>Role</span>
                    <span style={{ fontWeight: 600, color: "var(--df-navy)" }}><i className="bi bi-briefcase me-1 text-primary" /> {emp.role}</span>
                  </div>
                  <div>
                    <span style={{ fontSize: 11, color: "var(--df-text-muted)", fontWeight: 600, display: "block" }}>Email</span>
                    <span style={{ fontWeight: 500, color: "var(--df-navy)" }}><i className="bi bi-envelope me-1 text-primary" /> {emp.email}</span>
                  </div>
                  <div>
                    <span style={{ fontSize: 11, color: "var(--df-text-muted)", fontWeight: 600, display: "block" }}>Phone</span>
                    <span style={{ fontWeight: 500, color: "var(--df-navy)" }}><i className="bi bi-telephone me-1 text-primary" /> {emp.phone}</span>
                  </div>
                  <div>
                    <span style={{ fontSize: 11, color: "var(--df-text-muted)", fontWeight: 600, display: "block" }}>Join Date</span>
                    <span style={{ fontWeight: 500, color: "var(--df-navy)" }}><i className="bi bi-calendar3 me-1 text-primary" /> {formatDate(emp.joinDate)}</span>
                  </div>
                </div>
              </div>

              {/* Main Resume 2-Column Mockup Layout */}
              <div className="row g-4">
                {/* Left Column: About, What I love about my job, My interests and hobbies */}
                <div className="col-lg-7 col-md-12">
                  <div className="df-resume-box">
                    {/* About */}
                    <div className="d-flex align-items-center justify-content-between">
                      <h3 className="df-resume-box-title mb-0">About</h3>
                      <button className="df-edit-icon-btn" title="Edit About" onClick={() => openAboutModal("about")}>
                        <i className="bi bi-pencil" />
                      </button>
                    </div>
                    <p className="df-resume-text mb-4 mt-2">
                      {currentResume.about || "No description provided. Click pencil to add."}
                    </p>

                    {/* What I love about my job */}
                    <div className="d-flex align-items-center justify-content-between pt-2 border-top">
                      <h4 className="df-resume-subtitle">What I love about my job</h4>
                      <button className="df-edit-icon-btn" title="Edit What I Love" onClick={() => openAboutModal("whatILove")}>
                        <i className="bi bi-pencil" />
                      </button>
                    </div>
                    <p className="df-resume-text mb-4 mt-1">
                      {currentResume.whatILove || "No preferences specified. Click pencil to add."}
                    </p>

                    {/* My interests and hobbies */}
                    <div className="d-flex align-items-center justify-content-between pt-2 border-top">
                      <h4 className="df-resume-subtitle">My interests and hobbies</h4>
                      <button className="df-edit-icon-btn" title="Edit Interests and Hobbies" onClick={() => openAboutModal("interests")}>
                        <i className="bi bi-pencil" />
                      </button>
                    </div>
                    <p className="df-resume-text mt-1">
                      {currentResume.interests || "No interests specified. Click pencil to add."}
                    </p>
                  </div>
                </div>

                {/* Right Column: Skills and Certification */}
                <div className="col-lg-5 col-md-12 d-flex flex-column gap-4">
                  {/* Skills Box */}
                  <div className="df-resume-box">
                    <div className="df-resume-box-title">
                      <span>Skills</span>
                      <span className="badge bg-light text-dark border" style={{ fontSize: 11 }}>
                        {currentResume.skills.length}
                      </span>
                    </div>

                    <div className="d-flex flex-wrap gap-2 mb-4" style={{ minHeight: 70 }}>
                      {currentResume.skills.length === 0 ? (
                        <span className="text-muted" style={{ fontSize: 13, fontStyle: "italic" }}>No skills added yet.</span>
                      ) : (
                        currentResume.skills.map(s => (
                          <span key={s.id} className="df-skill-chip">
                            {s.name}
                            <button className="df-skill-chip-delete" title="Remove" onClick={() => handleRemoveSkill(s.id)}>
                              <i className="bi bi-x" />
                            </button>
                          </span>
                        ))
                      )}
                    </div>

                    <button className="df-add-btn" onClick={() => setShowSkillModal(true)}>
                      <i className="bi bi-plus-lg" /> + Add Skills
                    </button>
                  </div>

                  {/* Certification Box */}
                  <div className="df-resume-box">
                    <div className="df-resume-box-title">
                      <span>Certification</span>
                      <span className="badge bg-light text-dark border" style={{ fontSize: 11 }}>
                        {currentResume.certifications.length}
                      </span>
                    </div>

                    <div className="mb-4" style={{ minHeight: 70 }}>
                      {currentResume.certifications.length === 0 ? (
                        <span className="text-muted" style={{ fontSize: 13, fontStyle: "italic" }}>No certifications added yet.</span>
                      ) : (
                        currentResume.certifications.map(c => (
                          <div key={c.id} className="df-cert-item">
                            <div className="d-flex gap-3 align-items-start">
                              <div style={{ width: 32, height: 32, borderRadius: 6, background: "var(--df-blue-light)", color: "var(--df-blue)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 15, flexShrink: 0, marginTop: 2 }}>
                                <i className="bi bi-award-fill" />
                              </div>
                              <div>
                                <div style={{ fontWeight: 600, fontSize: 13, color: "var(--df-navy)" }}>{c.title}</div>
                                <div style={{ fontSize: 11, color: "var(--df-text-muted)", marginTop: 2 }}>
                                  {c.issuer} {c.issueDate ? `· ${c.issueDate}` : ""}
                                </div>
                              </div>
                            </div>
                            <button className="df-edit-icon-btn text-danger ms-2" title="Remove" onClick={() => handleRemoveCert(c.id)}>
                              <i className="bi bi-trash" />
                            </button>
                          </div>
                        ))
                      )}
                    </div>

                    <button className="df-add-btn" onClick={() => setShowCertModal(true)}>
                      <i className="bi bi-plus-lg" /> + Add Certification
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {tab === "private" && (
            <div className="row g-4">
              <div className="col-md-6">
                <p className="mb-3" style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--df-text-muted)" }}>Personal Information</p>
                {[
                  { label: "Full Name", value: emp.name },
                  { label: "National ID", value: "••••••••7892" },
                  { label: "Date of Birth", value: "14 Mar 1989" },
                  { label: "Nationality", value: "United States" },
                  { label: "Emergency Contact", value: "Jamie Webb · +1 (555) 099-1234" },
                ].map(f => (
                  <div key={f.label} className="mb-3" style={{ paddingBottom: 12, borderBottom: "1px solid var(--df-border)" }}>
                    <div style={{ fontSize: 11, color: "var(--df-text-muted)", fontWeight: 600, marginBottom: 2 }}>{f.label}</div>
                    <div style={{ fontWeight: 500 }}>{f.value}</div>
                  </div>
                ))}
              </div>
              <div className="col-md-6">
                <p className="mb-3" style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.07em", textTransform: "uppercase", color: "var(--df-text-muted)" }}>Banking & Payroll</p>
                {[
                  { label: "Bank Name", value: "Chase Bank" },
                  { label: "Account Number", value: "••••••••3421" },
                  { label: "Routing Number", value: "••••••021" },
                  { label: "Tax ID (SSN)", value: "•••-••-8812" },
                  { label: "Pay Schedule", value: "Monthly · End of month" },
                ].map(f => (
                  <div key={f.label} className="mb-3" style={{ paddingBottom: 12, borderBottom: "1px solid var(--df-border)" }}>
                    <div style={{ fontSize: 11, color: "var(--df-text-muted)", fontWeight: 600, marginBottom: 2 }}>{f.label}</div>
                    <div style={{ fontWeight: 500 }}>{f.value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === "salary" && (
            <div>
              {/* Admin Only Notice Banner */}
              <div className="df-admin-banner">
                <div className="d-flex align-items-center gap-2">
                  <i className="bi bi-shield-lock-fill text-primary" style={{ fontSize: 18 }} />
                  <div>
                    <span style={{ fontWeight: 700, fontSize: 13, color: "var(--df-navy)" }}>Admin Access View</span>
                    <span style={{ fontSize: 12, color: "var(--df-text-muted)", marginLeft: 8 }}>
                      Salary Info tab should only be visible to Admin
                    </span>
                  </div>
                </div>
                <span className="badge bg-primary px-2 py-1" style={{ fontSize: 11 }}>Admin Privilege Required</span>
              </div>

              {salaryFeedback && (
                <div className={`alert ${salaryFeedback.type === "success" ? "alert-success" : "alert-danger"} py-2 px-3 small mb-4`}>
                  {salaryFeedback.message}
                </div>
              )}

              {/* Top Header Card: Month Wage, Yearly Wage, Working Days, Break Time */}
              <div className="df-salary-header-card">
                <div className="row g-4 align-items-center">
                  <div className="col-md-6 border-end">
                    <div className="d-flex align-items-center justify-content-between mb-3">
                      <span style={{ fontWeight: 600, color: "var(--df-navy)" }}>Month Wage</span>
                      <div className="df-salary-input-group">
                        <input
                          type="number"
                          className="df-salary-num-input"
                          value={monthWage}
                          onChange={e => setMonthWage(Math.max(0, Number(e.target.value)))}
                        />
                        <span className="text-muted" style={{ fontSize: 13 }}>/ Month</span>
                      </div>
                    </div>
                    <div className="d-flex align-items-center justify-content-between">
                      <span style={{ fontWeight: 600, color: "var(--df-navy)" }}>Yearly wage</span>
                      <div className="df-salary-input-group">
                        <span className="df-salary-num-input text-end d-inline-block" style={{ background: "#f1f5f9" }}>
                          {yearlyWage.toLocaleString("en-IN")}
                        </span>
                        <span className="text-muted" style={{ fontSize: 13 }}>/ Yearly</span>
                      </div>
                    </div>
                  </div>

                  <div className="col-md-6 ps-md-4">
                    <div className="d-flex align-items-center justify-content-between mb-3">
                      <span style={{ fontWeight: 600, color: "var(--df-navy)" }}>No of working days in a week:</span>
                      <div className="df-salary-input-group">
                        <input
                          type="number"
                          className="df-salary-num-input"
                          style={{ width: 90 }}
                          value={workingDaysWeek}
                          onChange={e => {
                            const v = Number(e.target.value);
                            setWorkingDaysWeek(v);
                            localStorage.setItem(`working_days_emp_${empId}`, String(v));
                          }}
                        />
                      </div>
                    </div>
                    <div className="d-flex align-items-center justify-content-between">
                      <span style={{ fontWeight: 600, color: "var(--df-navy)" }}>Break Time:</span>
                      <div className="df-salary-input-group">
                        <input
                          type="number"
                          className="df-salary-num-input"
                          style={{ width: 90 }}
                          value={breakTimeHours}
                          onChange={e => {
                            const v = Number(e.target.value);
                            setBreakTimeHours(v);
                            localStorage.setItem(`break_time_emp_${empId}`, String(v));
                          }}
                        />
                        <span className="text-muted" style={{ fontSize: 13 }}>hr / day</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Two Column Breakdown */}
              <div className="row g-4">
                {/* Left Column: Salary Components */}
                <div className="col-lg-7 col-md-12">
                  <div className="df-salary-component-card">
                    <h3 className="df-section-title mb-4" style={{ fontSize: 16 }}>Salary Components</h3>

                    {/* Basic Salary */}
                    <div className="df-salary-comp-item">
                      <div className="df-salary-comp-header">
                        <span className="df-salary-comp-title">Basic Salary</span>
                        <div className="d-flex align-items-center gap-2">
                          <span className="df-salary-comp-val">₹{basicVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                          <span className="df-salary-comp-pct">{basicPctStr}</span>
                        </div>
                      </div>
                      <div className="df-salary-comp-sub">
                        Define Basic salary from company cost compute it based on monthly Wages
                      </div>
                    </div>

                    {/* HRA */}
                    <div className="df-salary-comp-item">
                      <div className="df-salary-comp-header">
                        <span className="df-salary-comp-title">House Rent Allowance</span>
                        <div className="d-flex align-items-center gap-2">
                          <span className="df-salary-comp-val">₹{hraVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                          <span className="df-salary-comp-pct">{hraPctStr}</span>
                        </div>
                      </div>
                      <div className="df-salary-comp-sub">
                        House Rent Allowance provided to employees
                      </div>
                    </div>

                    {/* Standard Allowance */}
                    <div className="df-salary-comp-item">
                      <div className="df-salary-comp-header">
                        <span className="df-salary-comp-title">Standard Allowance</span>
                        <div className="d-flex align-items-center gap-2">
                          <span className="df-salary-comp-val">₹{stdVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                          <span className="df-salary-comp-pct">{stdPctStr}</span>
                        </div>
                      </div>
                      <div className="df-salary-comp-sub">
                        Standard allowance is a predictable, fixed amount provided to employee
                      </div>
                    </div>

                    {/* Performance Bonus */}
                    <div className="df-salary-comp-item">
                      <div className="df-salary-comp-header">
                        <span className="df-salary-comp-title">Performance Bonus</span>
                        <div className="d-flex align-items-center gap-2">
                          <span className="df-salary-comp-val">₹{perfVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                          <span className="df-salary-comp-pct">{perfPctStr}</span>
                        </div>
                      </div>
                      <div className="df-salary-comp-sub">
                        Variable amount paid during payroll, depends on company performance
                      </div>
                    </div>

                    {/* LTA */}
                    <div className="df-salary-comp-item">
                      <div className="df-salary-comp-header">
                        <span className="df-salary-comp-title">Leave Travel Allowance</span>
                        <div className="d-flex align-items-center gap-2">
                          <span className="df-salary-comp-val">₹{ltaVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                          <span className="df-salary-comp-pct">{ltaPctStr}</span>
                        </div>
                      </div>
                      <div className="df-salary-comp-sub">
                        LTA is paid by the company to employees to cover their travel expenses
                      </div>
                    </div>

                    {/* Fixed Allowance */}
                    <div className="df-salary-comp-item">
                      <div className="df-salary-comp-header">
                        <span className="df-salary-comp-title">Fixed Allowance</span>
                        <div className="d-flex align-items-center gap-2">
                          <span className="df-salary-comp-val">₹{fixedVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                          <span className="df-salary-comp-pct">{fixedPctStr}</span>
                        </div>
                      </div>
                      <div className="df-salary-comp-sub">
                        Fixed allowance portion of wages is determined after calculating all salary components
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Column: Provident Fund & Tax Deductions */}
                <div className="col-lg-5 col-md-12 d-flex flex-column gap-4">
                  {/* Provident Fund (PF) Contribution */}
                  <div className="df-salary-component-card">
                    <h3 className="df-section-title mb-4" style={{ fontSize: 16 }}>Provident Fund (PF) Contribution</h3>

                    {/* Employee PF */}
                    <div className="df-salary-comp-item">
                      <div className="df-salary-comp-header">
                        <span className="df-salary-comp-title">Employee Contribution</span>
                        <div className="d-flex align-items-center gap-2">
                          <span className="df-salary-comp-val">₹{employeePfVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                          <input
                            type="number"
                            className="df-salary-num-input"
                            style={{ width: 65, padding: "2px 6px", fontSize: 12 }}
                            value={pfPct}
                            onChange={e => setPfPct(Number(e.target.value))}
                          />
                          <span style={{ fontSize: 12, fontWeight: 600 }}>%</span>
                        </div>
                      </div>
                      <div className="df-salary-comp-sub">
                        PF is calculated based on the basic salary
                      </div>
                    </div>

                    {/* Employer PF */}
                    <div className="df-salary-comp-item">
                      <div className="df-salary-comp-header">
                        <span className="df-salary-comp-title">Employer Contribution</span>
                        <div className="d-flex align-items-center gap-2">
                          <span className="df-salary-comp-val">₹{employerPfVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                          <span className="df-salary-comp-pct">{pfPct.toFixed(2)} %</span>
                        </div>
                      </div>
                      <div className="df-salary-comp-sub">
                        PF is calculated based on the basic salary
                      </div>
                    </div>
                  </div>

                  {/* Tax Deductions */}
                  <div className="df-salary-component-card">
                    <h3 className="df-section-title mb-4" style={{ fontSize: 16 }}>Tax Deductions</h3>

                    {/* Professional Tax */}
                    <div className="df-salary-comp-item">
                      <div className="df-salary-comp-header">
                        <span className="df-salary-comp-title">Professional Tax</span>
                        <div className="d-flex align-items-center gap-2">
                          <input
                            type="number"
                            className="df-salary-num-input"
                            style={{ width: 90, padding: "3px 8px" }}
                            value={profTaxVal}
                            onChange={e => setProfTaxVal(Number(e.target.value))}
                          />
                          <span className="df-salary-comp-val">.00 ₹ / month</span>
                        </div>
                      </div>
                      <div className="df-salary-comp-sub">
                        Professional Tax deducted from the Gross salary
                      </div>
                    </div>
                  </div>

                  {/* Take-Home Pay Summary Box */}
                  <div className="p-4 rounded-3 text-white" style={{ background: "var(--df-navy)", border: "1px solid var(--df-navy-mid)" }}>
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <span style={{ fontSize: 13, color: "var(--df-text-sub)" }}>Monthly Wage</span>
                      <span className="tabnum" style={{ fontWeight: 600, fontSize: 15 }}>₹{monthWage.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div className="d-flex justify-content-between align-items-center mb-3 pb-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                      <span style={{ fontSize: 13, color: "#fca5a5" }}>Deductions (PF + Professional Tax)</span>
                      <span className="tabnum" style={{ fontWeight: 600, fontSize: 15, color: "#fca5a5" }}>−₹{totalDeductionsVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div className="d-flex justify-content-between align-items-center mb-4">
                      <div>
                        <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--df-text-sub)", display: "block" }}>Net Monthly Salary</span>
                        <span style={{ fontWeight: 800, fontSize: 20, color: "#4ade80" }} className="tabnum">₹{netSalaryVal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                      </div>
                      <span className="badge bg-success bg-opacity-25 text-success border border-success px-3 py-2">Auto Calculated</span>
                    </div>

                    <button
                      className="df-btn-primary w-100 py-2.5 fw-bold d-flex align-items-center justify-content-center gap-2"
                      style={{ background: "#10b981", borderColor: "#10b981" }}
                      disabled={savingSalary}
                      onClick={handleSaveSalary}
                    >
                      {savingSalary ? (
                        <>
                          <span className="spinner-border spinner-border-sm" />
                          Saving...
                        </>
                      ) : (
                        <>
                          <i className="bi bi-cloud-arrow-up-fill" />
                          Save Salary Structure
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Edit About Modal */}
      {editModalField && (
        <div className="df-modal-overlay" onClick={() => setEditModalField(null)}>
          <div className="df-modal-content p-4" onClick={e => e.stopPropagation()}>
            <div className="d-flex align-items-center justify-content-between mb-3 pb-2 border-bottom">
              <h3 className="df-section-title mb-0" style={{ fontSize: 16 }}>Edit Resume Information</h3>
              <button className="btn-close" onClick={() => setEditModalField(null)} />
            </div>

            {(editModalField === "all" || editModalField === "about") && (
              <div className="mb-3">
                <label className="form-label" style={{ fontSize: 12, fontWeight: 600 }}>About</label>
                <textarea
                  className="form-control df-input w-100"
                  rows={3}
                  value={aboutInput}
                  onChange={e => setAboutInput(e.target.value)}
                  placeholder="Tell us about yourself and your background..."
                />
              </div>
            )}

            {(editModalField === "all" || editModalField === "whatILove") && (
              <div className="mb-3">
                <label className="form-label" style={{ fontSize: 12, fontWeight: 600 }}>What I love about my job</label>
                <textarea
                  className="form-control df-input w-100"
                  rows={3}
                  value={whatILoveInput}
                  onChange={e => setWhatILoveInput(e.target.value)}
                  placeholder="Share what drives and motivates you..."
                />
              </div>
            )}

            {(editModalField === "all" || editModalField === "interests") && (
              <div className="mb-3">
                <label className="form-label" style={{ fontSize: 12, fontWeight: 600 }}>My interests and hobbies</label>
                <textarea
                  className="form-control df-input w-100"
                  rows={3}
                  value={interestsInput}
                  onChange={e => setInterestsInput(e.target.value)}
                  placeholder="Personal interests, hobbies, activities..."
                />
              </div>
            )}

            <div className="d-flex justify-content-end gap-2 mt-4 pt-2 border-top">
              <button className="df-btn-secondary" onClick={() => setEditModalField(null)}>Cancel</button>
              <button className="df-btn-primary" onClick={handleSaveAbout}>Save Changes</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Skill Modal */}
      {showSkillModal && (
        <div className="df-modal-overlay" onClick={() => setShowSkillModal(false)}>
          <div className="df-modal-content p-4" onClick={e => e.stopPropagation()}>
            <div className="d-flex align-items-center justify-content-between mb-3 pb-2 border-bottom">
              <h3 className="df-section-title mb-0" style={{ fontSize: 16 }}>Add New Skill</h3>
              <button className="btn-close" onClick={() => setShowSkillModal(false)} />
            </div>

            <form onSubmit={handleAddSkill}>
              <div className="mb-3">
                <label className="form-label" style={{ fontSize: 12, fontWeight: 600 }}>Skill Name</label>
                <input
                  type="text"
                  className="form-control df-input w-100"
                  value={newSkillName}
                  onChange={e => setNewSkillName(e.target.value)}
                  placeholder="e.g. React, Docker, Project Management, SQL"
                  autoFocus
                />
              </div>

              <div className="d-flex justify-content-end gap-2 mt-4 pt-2 border-top">
                <button type="button" className="df-btn-secondary" onClick={() => setShowSkillModal(false)}>Cancel</button>
                <button type="submit" className="df-btn-primary" disabled={!newSkillName.trim()}>Add Skill</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add Certification Modal */}
      {showCertModal && (
        <div className="df-modal-overlay" onClick={() => setShowCertModal(false)}>
          <div className="df-modal-content p-4" onClick={e => e.stopPropagation()}>
            <div className="d-flex align-items-center justify-content-between mb-3 pb-2 border-bottom">
              <h3 className="df-section-title mb-0" style={{ fontSize: 16 }}>Add Certification</h3>
              <button className="btn-close" onClick={() => setShowCertModal(false)} />
            </div>

            <form onSubmit={handleAddCert}>
              <div className="mb-3">
                <label className="form-label" style={{ fontSize: 12, fontWeight: 600 }}>Certification Title *</label>
                <input
                  type="text"
                  className="form-control df-input w-100"
                  value={newCertTitle}
                  onChange={e => setNewCertTitle(e.target.value)}
                  placeholder="e.g. AWS Certified Solutions Architect"
                  required
                  autoFocus
                />
              </div>

              <div className="mb-3">
                <label className="form-label" style={{ fontSize: 12, fontWeight: 600 }}>Issuing Organization</label>
                <input
                  type="text"
                  className="form-control df-input w-100"
                  value={newCertIssuer}
                  onChange={e => setNewCertIssuer(e.target.value)}
                  placeholder="e.g. Amazon Web Services, Google, Scrum Alliance"
                />
              </div>

              <div className="mb-3">
                <label className="form-label" style={{ fontSize: 12, fontWeight: 600 }}>Issue Date / Year</label>
                <input
                  type="text"
                  className="form-control df-input w-100"
                  value={newCertDate}
                  onChange={e => setNewCertDate(e.target.value)}
                  placeholder="e.g. 2024-03"
                />
              </div>

              <div className="d-flex justify-content-end gap-2 mt-4 pt-2 border-top">
                <button type="button" className="df-btn-secondary" onClick={() => setShowCertModal(false)}>Cancel</button>
                <button type="submit" className="df-btn-primary" disabled={!newCertTitle.trim()}>Add Certification</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

function formatHoursMinutes(decimalHours?: number): { workHours: string; extraHours: string } {
  if (!decimalHours || decimalHours <= 0) return { workHours: "—", extraHours: "00:00" };

  const totalMins = Math.round(decimalHours * 60);
  const hrs = Math.floor(totalMins / 60);
  const mins = totalMins % 60;
  const workHours = `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;

  // Extra hours beyond standard 8 hours
  const extraMins = Math.max(0, totalMins - 480);
  const eHrs = Math.floor(extraMins / 60);
  const eMins = extraMins % 60;
  const extraHours = `${String(eHrs).padStart(2, '0')}:${String(eMins).padStart(2, '0')}`;

  return { workHours, extraHours };
}

function Attendance() {
  const { employees, attendance, token } = useHRData();
  const today = new Date().toISOString().slice(0, 10);
  const dates = [today];
  const [selectedDate, setSelectedDate] = useState(today);
  const [searchTerm, setSearchTerm] = useState("");
  const [viewMode, setViewMode] = useState<"Day" | "Week">("Day");
  const [loadedRecords, setLoadedRecords] = useState<AttendanceRecord[]>([]);

  useEffect(() => {
    let cancelled = false;
    void api.attendance(selectedDate, token)
      .then(page => { if (!cancelled) setLoadedRecords(page.items.map(mapAttendance)); })
      .catch(() => { if (!cancelled) setLoadedRecords([]); });
    return () => { cancelled = true; };
  }, [selectedDate, token]);

  const records = (loadedRecords.length ? loadedRecords : attendance).filter(a => a.date === selectedDate);

  function shift(dir: -1 | 1) {
    const idx = dates.indexOf(selectedDate);
    const next = idx + dir;
    if (next >= 0 && next < dates.length) setSelectedDate(dates[next]);
  }

  // Filter employees by search term
  const filteredEmployees = employees.filter(emp =>
    emp.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    emp.department.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="df-page">
      {/* Header & Searchbar matching wireframe mockup */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <div className="d-flex align-items-center gap-2">
            <h1 className="df-section-title">Attendance</h1>
            <span className="badge bg-primary bg-opacity-10 text-primary border border-primary-subtle" style={{ fontSize: 11 }}>
              For Admin/HR Officer
            </span>
          </div>
          <p className="df-section-sub mt-1">Daily employee check-in, check-out, work hours & extra hours log</p>
        </div>

        {/* Searchbar */}
        <div className="d-flex align-items-center gap-2">
          <div className="position-relative" style={{ width: 260 }}>
            <i className="bi bi-search position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" />
            <input
              type="text"
              className="df-input w-100 ps-5"
              placeholder="Searchbar"
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Date Navigation & View Controls: <- -> Date v Day */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4 p-3 rounded-3" style={{ background: "var(--df-card)", border: "1px solid var(--df-border)" }}>
        <div className="d-flex align-items-center gap-2">
          {/* <- Button */}
          <button
            className="df-btn-secondary"
            style={{ padding: "6px 14px", fontWeight: 600 }}
            onClick={() => shift(-1)}
            disabled={selectedDate === dates[dates.length - 1]}
            title="Previous Date"
          >
            &lt;-
          </button>

          {/* -> Button */}
          <button
            className="df-btn-secondary"
            style={{ padding: "6px 14px", fontWeight: 600 }}
            onClick={() => shift(1)}
            disabled={selectedDate === dates[0]}
            title="Next Date"
          >
            -&gt;
          </button>

          {/* Date v Dropdown */}
          <div className="d-flex align-items-center gap-1 ms-2">
            <input
              type="date"
              className="df-input"
              style={{ padding: "5px 10px", fontSize: 13, fontWeight: 600 }}
              value={selectedDate}
              onChange={e => setSelectedDate(e.target.value)}
            />
          </div>

          {/* Day View Filter Button */}
          <button
            className={`btn btn-sm ${viewMode === "Day" ? "btn-dark" : "btn-outline-secondary"} ms-2`}
            onClick={() => setViewMode("Day")}
            style={{ fontWeight: 600, fontSize: 13, padding: "5px 16px" }}
          >
            Day
          </button>
        </div>

        <div className="d-flex align-items-center gap-3">
          <span style={{ fontSize: 13, color: "var(--df-text-muted)", fontWeight: 500 }}>
            Standard Shift: 8.0 hrs/day
          </span>
        </div>
      </div>

      {/* Main Table List View matching wireframe layout */}
      <div className="df-card p-0 overflow-hidden">
        {/* Date Banner Header e.g. "22,October 2025" */}
        <div className="px-4 py-3 bg-light border-bottom d-flex align-items-center justify-content-between">
          <span style={{ fontFamily: "'Plus Jakarta Sans', sans-serif", fontWeight: 700, fontSize: 16, color: "var(--df-navy)" }}>
            {new Date(selectedDate).toLocaleDateString("en-US", { day: "2-digit", month: "long", year: "numeric" }).replace(/^(\d+)\s/, "$1,")}
          </span>
          <span className="badge bg-secondary" style={{ fontSize: 11 }}>
            {filteredEmployees.length} Employee Records
          </span>
        </div>

        <div className="table-responsive">
          <table className="df-table df-table-compact align-middle">
            <thead>
              <tr style={{ background: "#f8fafc" }}>
                <th style={{ minWidth: 200, paddingLeft: 24 }}>Emp</th>
                <th style={{ minWidth: 120 }}>Check In</th>
                <th style={{ minWidth: 120 }}>Check Out</th>
                <th style={{ minWidth: 120 }}>Work Hours</th>
                <th style={{ minWidth: 120, paddingRight: 24 }}>Extra hours</th>
              </tr>
            </thead>
            <tbody>
              {filteredEmployees.map(emp => {
                const rec = records.find(r => r.employeeId === emp.id);
                const checkInStr = rec?.checkIn ?? "—";
                const checkOutStr = rec?.checkOut ?? "—";

                const calcHours = rec?.hours ?? 0;
                const { workHours, extraHours } = formatHoursMinutes(calcHours);

                return (
                  <tr key={emp.id}>
                    <td style={{ paddingLeft: 24 }}>
                      <div className="d-flex align-items-center gap-3">
                        <Avatar emp={emp} size={32} />
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13, color: "var(--df-navy)" }}>{emp.name}</div>
                          <div style={{ fontSize: 11, color: "var(--df-text-muted)" }}>{emp.role} · {emp.department}</div>
                        </div>
                      </div>
                    </td>
                    <td className="tabnum" style={{ fontWeight: 500, fontSize: 14 }}>
                      {checkInStr}
                    </td>
                    <td className="tabnum" style={{ fontWeight: 500, fontSize: 14 }}>
                      {checkOutStr}
                    </td>
                    <td className="tabnum" style={{ fontWeight: 600, fontSize: 14, color: "var(--df-navy)" }}>
                      {workHours}
                    </td>
                    <td className="tabnum" style={{ paddingRight: 24 }}>
                      <span className={`badge ${extraHours !== "00:00" ? "bg-success-subtle text-success border border-success-subtle" : "bg-light text-muted border"}`} style={{ fontSize: 13, fontWeight: 600, padding: "4px 10px" }}>
                        {extraHours}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function TimeOff() {
  const { employees, requests: loadedRequests, refresh, token } = useHRData();
  const [requests, setRequests] = useState<TimeOffRequest[]>([]);
  const [filter, setFilter] = useState<"all" | TimeOffStatus>("all");
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  // Leave approval states
  const [reviewRequest, setReviewRequest] = useState<{ id: number; decision: "approved" | "rejected" } | null>(null);
  const [reviewComment, setReviewComment] = useState("");

  useEffect(() => setRequests(loadedRequests), [loadedRequests]);

  function startReview(id: number, decision: "approved" | "rejected") {
    setReviewRequest({ id, decision });
    setReviewComment("");
  }

  async function submitDecision() {
    if (!reviewRequest) return;
    const { id, decision } = reviewRequest;
    try {
      await api.reviewLeave(id, decision === "approved" ? "approve" : "reject", reviewComment || null, token);
      await refresh();
      setFeedback({
        type: "success",
        title: decision === "approved" ? "Leave Approved!" : "Leave Rejected",
        message: `The leave request has been successfully ${decision}.`,
      });
      setReviewRequest(null);
    } catch (error) {
      setFeedback({
        type: "error",
        title: "Update Failed",
        message: error instanceof Error ? error.message : "Unable to update request",
      });
    }
  }

  async function downloadAttachment(path: string, fileName: string) {
    try {
      const url = path.startsWith("http") ? path : `http://localhost:8000${path}`;
      const response = await fetch(url, {
        headers: {
          "Authorization": `Bearer ${token}`
        }
      });
      if (!response.ok) throw new Error("Could not download attachment");
      const blob = await response.blob();
      const blobUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = fileName || "attachment";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to download attachment");
    }
  }

  const filtered = requests.filter(r => filter === "all" || r.status === filter);
  const pending = requests.filter(r => r.status === "pending").length;

  return (
    <div className="df-page">
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h1 className="df-section-title">Time Off</h1>
          <p className="df-section-sub mt-1">{pending} request{pending !== 1 ? "s" : ""} awaiting review</p>
        </div>
      </div>

      <div className="d-flex gap-2 mb-3">
        {([
          { key: "all", label: "All" },
          { key: "pending", label: "Pending" },
          { key: "approved", label: "Approved" },
          { key: "rejected", label: "Rejected" },
        ] as { key: typeof filter; label: string }[]).map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)} className={filter === f.key ? "df-btn-primary" : "df-btn-secondary"} style={{ padding: "6px 14px" }}>
            {f.label}
            <span className="tabnum" style={{ marginLeft: 5, fontSize: 11, opacity: 0.75 }}>
              {requests.filter(r => f.key === "all" || r.status === f.key).length}
            </span>
          </button>
        ))}
      </div>

      <div className="df-table-wrap">
        <table className="df-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Type</th>
              <th>Period</th>
              <th className="tabnum">Days</th>
              <th>Reason</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="df-empty">
                    <i className="bi bi-inbox df-empty-icon" />
                    <p className="df-empty-title">No requests here</p>
                    <p className="df-empty-sub">No time-off requests match this filter.</p>
                  </div>
                </td>
              </tr>
            ) : filtered.map(r => {
              const emp = employees.find(e => e.id === r.employeeId);
              if (!emp) return null;
              return (
                <tr key={r.id}>
                  <td>
                    <div className="d-flex align-items-center gap-2">
                      <Avatar emp={emp} size={30} />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 13 }}>{emp.name}</div>
                        <div style={{ fontSize: 11, color: "var(--df-text-muted)" }}>{emp.department}</div>
                      </div>
                    </div>
                  </td>
                  <td style={{ fontWeight: 500 }}>{r.type}</td>
                  <td className="tabnum" style={{ fontSize: 13, color: "var(--df-text-muted)" }}>
                    {formatDate(r.from)} – {formatDate(r.to)}
                  </td>
                  <td className="tabnum" style={{ fontWeight: 700 }}>{r.days}</td>
                  <td style={{ color: "var(--df-text)", maxWidth: 200, fontSize: 13 }}>
                    <div className="fw-semibold text-muted">{r.reason}</div>
                    {r.attachmentPath && (
                      <button
                        className="btn btn-link p-0 d-inline-flex align-items-center gap-1 text-primary border-0 bg-transparent"
                        style={{ fontSize: 12, textDecoration: "none", marginTop: 4 }}
                        onClick={() => downloadAttachment(r.attachmentPath!, `${emp.name.replace(/\s+/g, "_")}_${r.type}_certificate`)}
                      >
                        <i className="bi bi-file-earmark-arrow-down" />
                        Download Certificate
                      </button>
                    )}
                  </td>
                  <td>
                    <StatusBadge status={r.status} />
                    {r.reviewComment && (
                      <div style={{ fontSize: 11, color: "var(--df-text-muted)", marginTop: 4, maxWidth: 150, fontStyle: "italic" }}>
                        "{r.reviewComment}"
                      </div>
                    )}
                  </td>
                  <td>
                    {r.status === "pending" ? (
                      <div className="d-flex gap-2">
                        <button className="df-btn-approve" onClick={() => startReview(r.id, "approved")}>
                          <i className="bi bi-check-lg" /> Approve
                        </button>
                        <button className="df-btn-reject" onClick={() => startReview(r.id, "rejected")}>
                          <i className="bi bi-x-lg" /> Reject
                        </button>
                      </div>
                    ) : (
                      <span style={{ fontSize: 12, color: "var(--df-text-sub)" }}>—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {feedback && <FeedbackModal feedback={feedback} onClose={() => setFeedback(null)} />}

      {/* Review Dialog */}
      {reviewRequest && (
        <div className="df-modal-overlay" style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1050 }}>
          <div className="df-card p-4" style={{ width: 450, background: "#fff", borderRadius: 12, border: "1px solid var(--df-border)" }}>
            <h3 style={{ fontSize: 18, fontWeight: 700, color: "var(--df-navy)", marginBottom: 16 }}>
              {reviewRequest.decision === "approved" ? "Approve Leave Request" : "Reject Leave Request"}
            </h3>
            <div className="mb-3">
              <label style={{ fontSize: 13, fontWeight: 600, color: "var(--df-text)", marginBottom: 6, display: "block" }}>
                Add Comment / Remarks (optional)
              </label>
              <textarea
                className="df-input w-100"
                rows={3}
                placeholder="Enter comments for the employee..."
                value={reviewComment}
                onChange={e => setReviewComment(e.target.value)}
                style={{ padding: 10, fontSize: 13 }}
              />
            </div>
            <div className="d-flex justify-content-end gap-2">
              <button className="df-btn-secondary px-3 py-2" onClick={() => setReviewRequest(null)}>Cancel</button>
              <button
                className={reviewRequest.decision === "approved" ? "df-btn-primary px-3 py-2" : "df-btn-reject px-3 py-2"}
                onClick={submitDecision}
                style={{ border: "none" }}
              >
                Confirm {reviewRequest.decision === "approved" ? "Approval" : "Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Payroll / Salary Page ───────────────────────────────────────────────────

function AdminSalaryPage({ onNav }: { onNav: (p: Page, id?: number, defaultTab?: EmployeeTab) => void }) {
  const { token, employees } = useHRData();
  const [salariesMap, setSalariesMap] = useState<Record<number, ApiSalary>>({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    setLoading(true);
    api.allSalaries(token)
      .then(res => {
        const map: Record<number, ApiSalary> = {};
        if (res?.items) {
          res.items.forEach(s => { map[s.employee_id] = s; });
        }
        setSalariesMap(map);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token]);

  const filtered = employees.filter(e =>
    e.name.toLowerCase().includes(search.toLowerCase()) ||
    e.department.toLowerCase().includes(search.toLowerCase()) ||
    e.role.toLowerCase().includes(search.toLowerCase())
  );

  const configuredCount = Object.keys(salariesMap).length;
  const totalMonthlyCost = Object.values(salariesMap).reduce((sum, s) => sum + Number(s.monthly_wage), 0);
  const totalAnnualCost = totalMonthlyCost * 12;
  const avgMonthlyWage = configuredCount > 0 ? totalMonthlyCost / configuredCount : 0;

  return (
    <div className="df-container py-4">
      {/* Page Header */}
      <div className="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h1 className="df-page-title mb-1" style={{ fontSize: 24, fontWeight: 700, color: "var(--df-navy)" }}>Payroll & Salary Management</h1>
          <p className="df-page-sub mb-0" style={{ color: "var(--df-text-muted)", fontSize: 14 }}>
            Overview of employee compensation, salary structures, and payroll control
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="row g-3 mb-4">
        <div className="col-md-3 col-sm-6">
          <div className="df-card p-3" style={{ background: "#fff", borderRadius: 12, border: "1px solid var(--df-border)" }}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--df-text-muted)" }}>Total Monthly Payroll</span>
              <div className="p-2 rounded-2" style={{ background: "rgba(37,99,235,0.1)", color: "#2563eb" }}>
                <i className="bi bi-cash-stack" style={{ fontSize: 18 }} />
              </div>
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: "var(--df-navy)" }} className="tabnum">
              ₹{totalMonthlyCost.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: 11, color: "var(--df-text-muted)", marginTop: 4 }}>Active configured structures</div>
          </div>
        </div>

        <div className="col-md-3 col-sm-6">
          <div className="df-card p-3" style={{ background: "#fff", borderRadius: 12, border: "1px solid var(--df-border)" }}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--df-text-muted)" }}>Annual Payroll Budget</span>
              <div className="p-2 rounded-2" style={{ background: "rgba(16,185,129,0.1)", color: "#10b981" }}>
                <i className="bi bi-piggy-bank" style={{ fontSize: 18 }} />
              </div>
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: "var(--df-navy)" }} className="tabnum">
              ₹{totalAnnualCost.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: 11, color: "var(--df-text-muted)", marginTop: 4 }}>Annual total compensation</div>
          </div>
        </div>

        <div className="col-md-3 col-sm-6">
          <div className="df-card p-3" style={{ background: "#fff", borderRadius: 12, border: "1px solid var(--df-border)" }}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--df-text-muted)" }}>Configured Employees</span>
              <div className="p-2 rounded-2" style={{ background: "rgba(245,158,11,0.1)", color: "#f59e0b" }}>
                <i className="bi bi-people" style={{ fontSize: 18 }} />
              </div>
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: "var(--df-navy)" }}>
              {configuredCount} / {employees.length}
            </div>
            <div style={{ fontSize: 11, color: "var(--df-text-muted)", marginTop: 4 }}>Salary structures active</div>
          </div>
        </div>

        <div className="col-md-3 col-sm-6">
          <div className="df-card p-3" style={{ background: "#fff", borderRadius: 12, border: "1px solid var(--df-border)" }}>
            <div className="d-flex align-items-center justify-content-between mb-2">
              <span style={{ fontSize: 13, fontWeight: 600, color: "var(--df-text-muted)" }}>Average Monthly Wage</span>
              <div className="p-2 rounded-2" style={{ background: "rgba(139,92,246,0.1)", color: "#8b5cf6" }}>
                <i className="bi bi-graph-up-arrow" style={{ fontSize: 18 }} />
              </div>
            </div>
            <div style={{ fontSize: 22, fontWeight: 700, color: "var(--df-navy)" }} className="tabnum">
              ₹{avgMonthlyWage.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <div style={{ fontSize: 11, color: "var(--df-text-muted)", marginTop: 4 }}>Avg per configured employee</div>
          </div>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="df-card p-3 mb-4" style={{ background: "#fff", borderRadius: 12, border: "1px solid var(--df-border)" }}>
        <div className="row g-3 align-items-center">
          <div className="col-md-6">
            <div className="position-relative">
              <i className="bi bi-search position-absolute top-50 start-0 translate-middle-y ms-3 text-muted" />
              <input
                className="df-input w-100 ps-5"
                placeholder="Search by employee name, role, or department..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Employee Payroll Table */}
      <div className="df-card overflow-hidden" style={{ background: "#fff", borderRadius: 12, border: "1px solid var(--df-border)" }}>
        <table className="df-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Department</th>
              <th>Role</th>
              <th>Wage Type</th>
              <th className="tabnum">Monthly Wage</th>
              <th className="tabnum">Yearly Wage</th>
              <th>Status</th>
              <th className="text-end">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8}>
                  <div className="df-empty py-5 text-center">
                    <i className="bi bi-inbox df-empty-icon mb-2" style={{ fontSize: 32 }} />
                    <p className="df-empty-title fw-bold mb-1">No employees found</p>
                    <p className="df-empty-sub text-muted">No employee matches your search criteria.</p>
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map(emp => {
                const s = salariesMap[emp.id];
                const monthlyWage = s ? Number(s.monthly_wage) : 50000;
                const yearlyWage = monthlyWage * 12;
                return (
                  <tr key={emp.id}>
                    <td>
                      <div className="d-flex align-items-center gap-2">
                        <Avatar emp={emp} size={32} />
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13, color: "var(--df-navy)" }}>{emp.name}</div>
                          <div style={{ fontSize: 11, color: "var(--df-text-muted)" }}>{emp.email}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ fontSize: 13, fontWeight: 500 }}>{emp.department}</td>
                    <td style={{ fontSize: 13, color: "var(--df-text-muted)" }}>{emp.role}</td>
                    <td>
                      <span className="badge bg-light text-dark border px-2 py-1" style={{ fontSize: 11 }}>
                        {s ? s.wage_type : "MONTHLY"}
                      </span>
                    </td>
                    <td className="tabnum fw-bold text-dark" style={{ fontSize: 14 }}>
                      ₹{monthlyWage.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td className="tabnum text-muted" style={{ fontSize: 13 }}>
                      ₹{yearlyWage.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </td>
                    <td>
                      <span className={`badge ${s ? "bg-success-subtle text-success border border-success-subtle" : "bg-secondary-subtle text-secondary border border-secondary-subtle"} px-2 py-1`} style={{ fontSize: 11 }}>
                        {s ? "Configured" : "Default"}
                      </span>
                    </td>
                    <td className="text-end">
                      <button
                        className="df-btn-secondary py-1 px-3"
                        style={{ fontSize: 12 }}
                        onClick={() => onNav("employee-detail", emp.id, "salary")}
                      >
                        <i className="bi bi-pencil-square me-1" />
                        Manage Salary
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Navbar ───────────────────────────────────────────────────────────────────

function Navbar({ page, onNav }: { page: Page; onNav: (p: Page) => void }) {
  const links: { key: Page; label: string; icon: string }[] = [
    { key: "dashboard", label: "Dashboard", icon: "bi-speedometer2" },
    { key: "employees", label: "Employees", icon: "bi-people-fill" },
    { key: "attendance", label: "Attendance", icon: "bi-clock-fill" },
    { key: "timeoff", label: "Time Off", icon: "bi-calendar-check-fill" },
    { key: "salary", label: "Payroll", icon: "bi-cash-stack" },
  ];

  const activePage = page === "employee-detail" ? "employees" : page;

  return (
    <nav className="df-navbar">
      <a className="df-logo" onClick={() => onNav("dashboard")} style={{ cursor: "pointer" }}>
        <div className="df-logo-mark">D</div>
        <span>Dayflow</span>
      </a>

      {links.map(l => (
        <button key={l.key} className={`df-nav-link ${activePage === l.key ? "active" : ""}`} onClick={() => onNav(l.key)}>
          <i className={`bi ${l.icon}`} style={{ fontSize: 15 }} />
          <span className="label">{l.label}</span>
        </button>
      ))}

      <div className="ms-auto d-flex align-items-center gap-3">
        <button className="df-nav-link" style={{ padding: "6px 10px" }}>
          <i className="bi bi-bell" style={{ fontSize: 16 }} />
          <span style={{ position: "absolute", top: 10, right: 8, width: 7, height: 7, background: "#f59e0b", borderRadius: "50%", border: "1.5px solid var(--df-navy)" }} />
        </button>
        <div className="d-flex align-items-center gap-2" style={{ cursor: "pointer", padding: "4px 8px", borderRadius: 8, transition: "background 0.15s" }}
          onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.08)")}
          onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
          <div style={{ width: 30, height: 30, borderRadius: "50%", background: "#2563EB", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'Plus Jakarta Sans'", fontWeight: 700, fontSize: 12, color: "white" }}>SO</div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: "white", lineHeight: 1.2 }}>Sandra Okafor</div>
            <div style={{ fontSize: 10, color: "rgba(255,255,255,0.5)", lineHeight: 1.2 }}>HR Admin</div>
          </div>
          <i className="bi bi-chevron-down" style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", marginLeft: 2 }} />
        </div>
      </div>
    </nav>
  );
}

function DataStatus() {
  const { loading, error, refresh } = useHRData();
  if (!loading && !error) return null;
  return (
    <div className={`alert ${error ? "alert-warning" : "alert-info"} rounded-0 border-0 mb-0 d-flex align-items-center justify-content-between`} role="status">
      <span>{loading ? "Loading live HR data..." : error}</span>
      {!loading && <button className="btn btn-sm btn-outline-dark" onClick={() => void refresh()}>Retry</button>}
    </div>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }: { onLogin: (token: string, refreshToken: string, user: ApiUser) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [designationId, setDesignationId] = useState("");
  const [joiningDate, setJoiningDate] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<FeedbackState | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      if (mode === "register") {
        const result = await signup({ first_name: firstName, last_name: lastName, email, password, department_id: Number(departmentId), designation_id: Number(designationId), joining_date: joiningDate });
        setFeedback({
          type: "success",
          title: "Account Created!",
          message: result.message || "Your account has been successfully registered. You may now sign in.",
        });
        setMode("login");
      } else {
        const session = await login(email, password);
        onLogin(session.access_token, session.refresh_token, session.user);
      }
    } catch (loginError) {
      const errMsg = loginError instanceof Error ? loginError.message : "Unable to sign in";
      setError(errMsg);
      setFeedback({
        type: "error",
        title: mode === "login" ? "Sign In Failed" : "Registration Failed",
        message: errMsg,
      });
    } finally {
      setBusy(false);
    }
  }

  return <div className="d-flex align-items-center justify-content-center min-vh-100" style={{ background: "var(--df-surface)" }}>
    <form className="df-card p-4" style={{ width: "min(420px, calc(100% - 32px))" }} onSubmit={submit}>
      <div className="df-logo mb-4" style={{ background: "var(--df-navy)", width: "fit-content", padding: "8px 12px", borderRadius: 8 }}><div className="df-logo-mark">D</div><span>Dayflow</span></div>
      <h1 className="df-section-title">{mode === "login" ? "Admin sign in" : "Register an account"}</h1>
      <p className="df-section-sub mb-4">{mode === "login" ? "Use your Dayflow account to continue." : "Create a Dayflow account to request access."}</p>
      {error && <div className="alert alert-danger py-2" role="alert">{error}</div>}
      {message && <div className="alert alert-success py-2" role="alert">{message}</div>}
      {mode === "register" && <div className="d-flex gap-2">
        <div className="flex-fill"><label className="form-label">First name</label><input className="df-input w-100 mb-3" required value={firstName} onChange={event => setFirstName(event.target.value)} /></div>
        <div className="flex-fill"><label className="form-label">Last name</label><input className="df-input w-100 mb-3" required value={lastName} onChange={event => setLastName(event.target.value)} /></div>
      </div>}
      <label className="form-label">Email</label>
      <input className="df-input w-100 mb-3" type="email" required value={email} onChange={event => setEmail(event.target.value)} />
      <label className="form-label">Password</label>
      <input className="df-input w-100 mb-4" type="password" required value={password} onChange={event => setPassword(event.target.value)} />
      {mode === "register" && <>
        <div className="d-flex gap-2"><div className="flex-fill"><label className="form-label">Department ID</label><input className="df-input w-100 mb-3" type="number" min="1" required value={departmentId} onChange={event => setDepartmentId(event.target.value)} /></div><div className="flex-fill"><label className="form-label">Designation ID</label><input className="df-input w-100 mb-3" type="number" min="1" required value={designationId} onChange={event => setDesignationId(event.target.value)} /></div></div>
        <label className="form-label">Joining date</label><input className="df-input w-100 mb-4" type="date" required value={joiningDate} onChange={event => setJoiningDate(event.target.value)} />
      </>}
      <button className="df-btn-primary w-100 justify-content-center" disabled={busy}>{busy ? "Please wait..." : mode === "login" ? "Sign in" : "Register"}</button>
      <button type="button" className="df-btn-secondary w-100 justify-content-center mt-2" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); setMessage(""); }}>{mode === "login" ? "Create an account" : "Back to sign in"}</button>
    </form>
    {feedback && <FeedbackModal feedback={feedback} onClose={() => setFeedback(null)} />}
  </div>;
}

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedEmpId, setSelectedEmpId] = useState<number>(1);
  const [initialDetailTab, setInitialDetailTab] = useState<EmployeeTab>("resume");
  const [session, setSession] = useState<{ token: string; refreshToken: string; user: ApiUser } | null>(() => {
    const stored = localStorage.getItem("dayflow_session");
    return stored ? JSON.parse(stored) : null;
  });

  function handleLogin(token: string, refreshToken: string, user: ApiUser) {
    if (!["ADMIN", "HR"].includes(user.role.toUpperCase())) {
      throw new Error("This admin portal is available only to Admin and HR accounts.");
    }
    const nextSession = { token, refreshToken, user };
    localStorage.setItem("dayflow_session", JSON.stringify(nextSession));
    setSession(nextSession);
  }

  function nav(p: Page, id?: number, defaultTab: EmployeeTab = "resume") {
    if (p === "employee-detail" && id) {
      setSelectedEmpId(id);
      setInitialDetailTab(defaultTab);
    }
    setPage(p);
  }

  function handleUnauthorized() {
    localStorage.removeItem("dayflow_session");
    setSession(null);
  }

  if (!session) return <LoginScreen onLogin={handleLogin} />;
  return <HRDataProvider token={session.token} onUnauthorized={handleUnauthorized}>
    <div style={{ minHeight: "100vh", background: "var(--df-surface)" }}>
      <Navbar page={page} onNav={p => nav(p)} />
      <DataStatus />
      <main>
        {page === "dashboard" && <Dashboard onNav={nav} />}
        {page === "employees" && <EmployeeList onNav={nav} />}
        {page === "employee-detail" && <EmployeeDetail empId={selectedEmpId} onBack={() => setPage("employees")} initialTab={initialDetailTab} />}
        {page === "attendance" && <Attendance />}
        {page === "timeoff" && <TimeOff />}
        {page === "salary" && <AdminSalaryPage onNav={nav} />}
      </main>
    </div>
  </HRDataProvider>;
}
