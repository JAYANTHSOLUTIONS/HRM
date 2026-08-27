-- ============================================================================
-- DAYFLOW HRMS - SEED / DEMO DATA
-- Run AFTER dayflow_schema.sql on a fresh database.
-- DEMO CREDENTIALS ARE FOR DEVELOPMENT ONLY — rotate/remove before production.
-- Password hashes below are bcrypt hashes of the plaintext "Password@123"
-- (cost factor 12). Generate real hashes with your backend's password
-- hashing library (e.g. passlib[bcrypt] in FastAPI) — never hardcode in prod.
-- ============================================================================

USE dayflow_hrms;

-- ---------------------------------------------------------------------------
-- ROLES
-- ---------------------------------------------------------------------------
INSERT INTO roles (role_name, description) VALUES
('ADMIN',    'Full system access'),
('HR',       'HR operations and approvals'),
('EMPLOYEE', 'Standard employee self-service access');

-- ---------------------------------------------------------------------------
-- DEPARTMENTS
-- ---------------------------------------------------------------------------
INSERT INTO departments (department_name) VALUES
('Engineering'), ('Human Resources'), ('Sales'), ('Finance'), ('Marketing');

-- ---------------------------------------------------------------------------
-- DESIGNATIONS
-- ---------------------------------------------------------------------------
INSERT INTO designations (title) VALUES
('Software Engineer'), ('Senior Software Engineer'), ('HR Officer'),
('System Administrator'), ('Sales Executive'), ('Marketing Associate'),
('Finance Analyst');

-- ---------------------------------------------------------------------------
-- LEAVE TYPES
-- ---------------------------------------------------------------------------
INSERT INTO leave_types (name, is_balance_tracked, requires_attachment) VALUES
('Paid Leave', TRUE, FALSE),
('Sick Leave', TRUE, TRUE),
('Unpaid Leave', FALSE, FALSE);

-- ---------------------------------------------------------------------------
-- HOLIDAYS (sample, 2026)
-- ---------------------------------------------------------------------------
INSERT INTO holidays (holiday_date, name, is_recurring) VALUES
('2026-01-01', 'New Year''s Day', TRUE),
('2026-01-26', 'Republic Day', TRUE),
('2026-08-15', 'Independence Day', TRUE),
('2026-12-25', 'Christmas', TRUE);

-- ---------------------------------------------------------------------------
-- USERS  (1 Admin, 1 HR, 3 Employees)
-- Employee code format: CC + first+last initials + join year + serial
-- ---------------------------------------------------------------------------
INSERT INTO users (employee_code, email, password_hash, role_id, is_email_verified, is_active, password_changed_at) VALUES
('CCAD20260001', 'admin@dayflow.dev',    '$2b$12$K3Jv8x1qYQe6z0m8vQdG3.h7l6qzWQxYQhF0i0mVh1hVYQx3ZbG9G', 1, TRUE, TRUE, NOW()),
('CCHR20260001', 'hr.officer@dayflow.dev','$2b$12$K3Jv8x1qYQe6z0m8vQdG3.h7l6qzWQxYQhF0i0mVh1hVYQx3ZbG9G', 2, TRUE, TRUE, NOW()),
('CCJD20260001', 'john.doe@dayflow.dev', '$2b$12$K3Jv8x1qYQe6z0m8vQdG3.h7l6qzWQxYQhF0i0mVh1hVYQx3ZbG9G', 3, TRUE, TRUE, NOW()),
('CCAS20260002', 'asha.singh@dayflow.dev','$2b$12$K3Jv8x1qYQe6z0m8vQdG3.h7l6qzWQxYQhF0i0mVh1hVYQx3ZbG9G', 3, TRUE, TRUE, NOW()),
('CCRK20260003', 'ravi.kumar@dayflow.dev','$2b$12$K3Jv8x1qYQe6z0m8vQdG3.h7l6qzWQxYQhF0i0mVh1hVYQx3ZbG9G', 3, TRUE, TRUE, NOW());

-- ---------------------------------------------------------------------------
-- EMPLOYEES  (manager_id set after initial insert, since John is Asha/Ravi's manager)
-- ---------------------------------------------------------------------------
INSERT INTO employees (user_id, employee_code, first_name, last_name, phone, address, date_of_birth, gender,
                        department_id, designation_id, manager_id, joining_date, employment_status, employment_type)
VALUES
(1, 'CCAD20260001', 'System', 'Admin',  '9999900001', 'Chennai, TN', '1990-01-01', 'PREFER_NOT_TO_SAY', 2, 4, NULL, '2026-01-01', 'ACTIVE', 'FULL_TIME'),
(2, 'CCHR20260001', 'Priya',  'Ramesh', '9999900002', 'Chennai, TN', '1992-05-14', 'FEMALE', 2, 3, NULL, '2026-01-05', 'ACTIVE', 'FULL_TIME'),
(3, 'CCJD20260001', 'John',   'Doe',    '9999900003', 'Bengaluru, KA', '1994-03-21', 'MALE', 1, 2, NULL, '2026-01-10', 'ACTIVE', 'FULL_TIME'),
(4, 'CCAS20260002', 'Asha',   'Singh',  '9999900004', 'Bengaluru, KA', '1996-07-09', 'FEMALE', 1, 1, 3, '2026-02-01', 'ACTIVE', 'FULL_TIME'),
(5, 'CCRK20260003', 'Ravi',   'Kumar',  '9999900005', 'Hyderabad, TS', '1995-11-30', 'MALE', 1, 1, 3, '2026-02-15', 'ACTIVE', 'FULL_TIME');

-- ---------------------------------------------------------------------------
-- LEAVE BALANCES (2026, per employee)
-- ---------------------------------------------------------------------------
INSERT INTO leave_balances (employee_id, leave_type_id, leave_year, allocated_days, used_days) VALUES
(3, 1, 2026, 24, 2), (3, 2, 2026, 7, 0),
(4, 1, 2026, 24, 5), (4, 2, 2026, 7, 2),
(5, 1, 2026, 24, 0), (5, 2, 2026, 7, 1);

-- ---------------------------------------------------------------------------
-- ATTENDANCE (sample days for Asha, employee_id=4)
-- ---------------------------------------------------------------------------
INSERT INTO attendance (employee_id, attendance_date, check_in_at, check_out_at, work_hours, status) VALUES
(4, '2026-08-18', '2026-08-18 09:32:00', '2026-08-18 18:41:00', 9.15, 'PRESENT'),
(4, '2026-08-19', '2026-08-19 09:10:00', '2026-08-19 18:05:00', 8.92, 'PRESENT'),
(4, '2026-08-20', NULL, NULL, 0.00, 'LEAVE'),
(4, '2026-08-21', '2026-08-21 09:45:00', '2026-08-21 14:30:00', 4.75, 'HALF_DAY');

-- ---------------------------------------------------------------------------
-- LEAVE REQUESTS
-- ---------------------------------------------------------------------------
INSERT INTO leave_requests (employee_id, leave_type_id, start_date, end_date, number_of_days, remarks, status, submitted_at)
VALUES
(4, 1, '2026-08-20', '2026-08-20', 1, 'Family function', 'APPROVED', '2026-08-15 10:00:00'),
(5, 2, '2026-08-25', '2026-08-26', 2, 'Fever', 'PENDING', '2026-08-22 08:30:00');

UPDATE leave_requests SET reviewed_by = 2, reviewed_at = '2026-08-16 09:00:00', review_comment = 'Approved'
WHERE employee_id = 4 AND status = 'APPROVED';

INSERT INTO leave_request_reviews (leave_request_id, reviewer_user_id, previous_status, new_status, comment, reviewed_at)
SELECT leave_request_id, 2, 'PENDING', 'APPROVED', 'Approved', '2026-08-16 09:00:00'
FROM leave_requests WHERE employee_id = 4 AND status = 'APPROVED';

-- ---------------------------------------------------------------------------
-- SALARY STRUCTURES + COMPONENTS (current, for John Doe, employee_id=3)
-- ---------------------------------------------------------------------------
INSERT INTO salary_structures (employee_id, monthly_wage, annual_wage, wage_type, effective_from, is_current, created_by)
VALUES (3, 60000.00, 720000.00, 'MONTHLY', '2026-01-10', TRUE, 1);

SET @ss_id = LAST_INSERT_ID();

INSERT INTO salary_components (salary_structure_id, component_name, component_type, calculation_type, percentage_value, fixed_amount, computed_amount)
VALUES
(@ss_id, 'Basic Salary',          'EARNING',              'PERCENTAGE', 50.00, NULL,      30000.00),
(@ss_id, 'House Rent Allowance',  'EARNING',              'PERCENTAGE', 50.00, NULL,      15000.00),
(@ss_id, 'Standard Allowance',    'EARNING',              'FIXED',      NULL,  4166.00,    4166.00),
(@ss_id, 'Leave Travel Allowance','EARNING',              'FIXED',      NULL,  3333.00,    3333.00),
(@ss_id, 'Employee PF',           'DEDUCTION',            'PERCENTAGE', 12.00, NULL,       3600.00),
(@ss_id, 'Employer PF',           'EMPLOYER_CONTRIBUTION', 'PERCENTAGE', 12.00, NULL,       3600.00),
(@ss_id, 'Professional Tax',      'DEDUCTION',            'FIXED',      NULL,   200.00,      200.00);

-- ---------------------------------------------------------------------------
-- AUDIT LOG SAMPLES
-- ---------------------------------------------------------------------------
INSERT INTO audit_logs (actor_user_id, action, target_entity, target_id, old_values, new_values, ip_address) VALUES
(2, 'LEAVE_APPROVED', 'leave_requests', 1, JSON_OBJECT('status','PENDING'), JSON_OBJECT('status','APPROVED'), '10.0.0.5'),
(1, 'SALARY_CREATED', 'salary_structures', @ss_id, NULL, JSON_OBJECT('monthly_wage', 60000.00), '10.0.0.2');
