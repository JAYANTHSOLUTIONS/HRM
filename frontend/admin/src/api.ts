const API_BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");

export interface ApiUser {
  user_id: number;
  employee_id: number;
  employee_code: string;
  full_name: string;
  email: string;
  role: string;
}

export interface ApiEmployee {
  employee_id: number;
  employee_code: string;
  full_name: string;
  first_name?: string;
  last_name?: string;
  email: string | null;
  phone?: string | null;
  department: { department_id: number; department_name: string } | null;
  designation: { designation_id: number; title: string } | null;
  employment_status: string;
  employment_type: string;
  joining_date?: string;
  profile_picture_url?: string | null;
}

export interface ApiAttendance {
  attendance_id: number;
  employee_id: number;
  employee_name: string | null;
  attendance_date: string;
  check_in_at: string | null;
  check_out_at: string | null;
  work_hours: number;
  overtime_hours: number;
  status: string;
  is_corrected: boolean;
}

export interface ApiLeaveRequest {
  leave_request_id: number;
  employee_id: number;
  employee_name: string | null;
  leave_type: { name: string };
  start_date: string;
  end_date: string;
  number_of_days: number;
  remarks: string | null;
  attachment_path: string | null;
  status: string;
  review_comment: string | null;
}

export interface ApiDashboard {
  total_employees: number;
  active_employees: number;
  present_today: number;
  absent_today: number;
  on_leave_today: number;
  pending_leave_requests: number;
  recent_activity: unknown[];
}

export interface ApiSalary {
  salary_structure_id: number;
  employee_id: number;
  monthly_wage: number;
  annual_wage: number;
  wage_type: string;
  effective_from: string;
  effective_to: string | null;
  is_current: boolean;
  components: Array<{
    name: string;
    type: string;
    calculation_type: string;
    percentage: number | null;
    fixed_amount: number | null;
    computed_amount: number;
  }>;
}

export interface ApiDepartment {
  department_id: number;
  department_name: string;
  is_active: boolean;
}

export interface ApiDesignation {
  designation_id: number;
  title: string;
  is_active: boolean;
}

interface Page<T> { items: T[]; total_items: number; }

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.error?.message ?? body.detail ?? message;
    } catch { /* keep the HTTP status message */ }
    throw new Error(response.status === 401 ? `AUTHENTICATION_REQUIRED (401): ${message}` : message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  return request<{ access_token: string; refresh_token: string; user: ApiUser }>("/auth/login", {
    method: "POST", body: JSON.stringify({ email, password }),
  });
}

export async function signup(payload: {
  first_name: string; last_name: string; email: string; password: string;
  department_id: number; designation_id: number; joining_date: string;
}) {
  return request<{ message: string }>("/auth/signup", { method: "POST", body: JSON.stringify(payload) });
}

export const api = {
  employees: (token: string) => request<Page<ApiEmployee>>("/employees?page_size=100", {}, token),
  employee: (id: number, token: string) => request<ApiEmployee>(`/employees/${id}`, {}, token),
  departments: (token: string) => request<{ items: ApiDepartment[] }>("/departments", {}, token),
  designations: (token: string) => request<{ items: ApiDesignation[] }>("/designations", {}, token),
  inviteEmployee: (payload: {
    email: string; first_name: string; last_name: string; role: "HR" | "ADMIN";
    department_id?: number; designation_id?: number; joining_date: string;
  }, token: string) => request<{ employee_code: string; message: string }>("/admin/users/invite", {
    method: "POST", body: JSON.stringify(payload),
  }, token),
  dashboard: (token: string) => request<ApiDashboard>("/dashboard/admin", {}, token),
  attendance: (date: string, token: string) => request<Page<ApiAttendance>>(`/attendance?date=${date}&page_size=100`, {}, token),
  leaveRequests: (token: string) => request<Page<ApiLeaveRequest>>("/leave/requests?page_size=100", {}, token),
  reviewLeave: (id: number, decision: "approve" | "reject", comment: string | null, token: string) => request<ApiLeaveRequest>(`/leave/requests/${id}/${decision}`, {
    method: "POST", body: JSON.stringify({ comment }),
  }, token),
  salary: (id: number, token: string) => request<ApiSalary>(`/salary/${id}`, {}, token),
  updateSalary: (id: number, payload: {
    monthly_wage: number;
    wage_type?: string;
    effective_from: string;
    components: Array<{
      name: string;
      type: string;
      calculation_type: string;
      percentage?: number | null;
      fixed_amount?: number | null;
    }>;
  }, token: string) => request<ApiSalary>(`/salary/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  }, token),
  allSalaries: (token: string) => request<{ items: ApiSalary[] }>("/salary", {}, token),
  logout: (refreshToken: string, token: string) => request<void>("/auth/logout", {
    method: "POST", body: JSON.stringify({ refresh_token: refreshToken }),
  }, token),
};

export { API_BASE };
