-- ============================================================================
-- DAYFLOW HRMS - PRODUCTION DATABASE SCHEMA
-- MySQL 8.0+ | InnoDB | utf8mb4
-- "Every workday, perfectly aligned."
-- ============================================================================
-- This schema is designed from scratch based on Dayflow functional
-- requirements + Excalidraw UI/workflow reference. It does not reuse any
-- prior schema. Timestamps are stored in UTC; convert at the application
-- layer for display.
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET SQL_MODE = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO';

CREATE DATABASE IF NOT EXISTS dayflow_hrms
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_0900_ai_ci;

USE dayflow_hrms;

-- ============================================================================
-- 1. ROLES  (simple RBAC — see design doc §RBAC for rationale)
-- ============================================================================
CREATE TABLE roles (
    role_id      TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role_name    VARCHAR(30) NOT NULL,
    description  VARCHAR(255) NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_roles_name UNIQUE (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Fixed set of application roles: ADMIN, HR, EMPLOYEE';

-- ============================================================================
-- 2. USERS  (authentication identity — separate from HR profile)
-- ============================================================================
CREATE TABLE users (
    user_id                BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    employee_code          VARCHAR(30) NOT NULL,
    email                  VARCHAR(255) NOT NULL,
    password_hash          VARCHAR(255) NOT NULL,
    role_id                TINYINT UNSIGNED NOT NULL,
    is_email_verified      BOOLEAN NOT NULL DEFAULT FALSE,
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts  SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    locked_until           TIMESTAMP NULL DEFAULT NULL,
    last_login_at          TIMESTAMP NULL DEFAULT NULL,
    password_changed_at    TIMESTAMP NULL DEFAULT NULL,
    created_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT uq_users_employee_code UNIQUE (employee_code),
    CONSTRAINT fk_users_role FOREIGN KEY (role_id) REFERENCES roles(role_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Authentication identity. employee_code format: CC + FirstLast initials + Year + Serial, generated server-side.';

CREATE INDEX idx_users_role ON users(role_id);
CREATE INDEX idx_users_active ON users(is_active);

-- ============================================================================
-- 3. EMAIL VERIFICATION TOKENS
-- ============================================================================
CREATE TABLE email_verification_tokens (
    token_id     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT UNSIGNED NOT NULL,
    token_hash   CHAR(64) NOT NULL COMMENT 'SHA-256 hex of the raw token; raw token never stored',
    expires_at   TIMESTAMP NOT NULL,
    used_at      TIMESTAMP NULL DEFAULT NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_evt_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_evt_user FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_evt_user_id ON email_verification_tokens(user_id);
CREATE INDEX idx_evt_expires ON email_verification_tokens(expires_at);

-- ============================================================================
-- 4. PASSWORD RESET TOKENS
-- ============================================================================
CREATE TABLE password_reset_tokens (
    token_id     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT UNSIGNED NOT NULL,
    token_hash   CHAR(64) NOT NULL,
    expires_at   TIMESTAMP NOT NULL,
    used_at      TIMESTAMP NULL DEFAULT NULL,
    attempts     SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    requested_ip VARCHAR(45) NULL,
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_prt_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_prt_user FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_prt_user_id ON password_reset_tokens(user_id);
CREATE INDEX idx_prt_expires ON password_reset_tokens(expires_at);

-- ============================================================================
-- 5. REFRESH / SESSION TOKENS
-- ============================================================================
CREATE TABLE refresh_tokens (
    token_id     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id      BIGINT UNSIGNED NOT NULL,
    token_hash   CHAR(64) NOT NULL,
    issued_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at   TIMESTAMP NOT NULL,
    revoked_at   TIMESTAMP NULL DEFAULT NULL,
    ip_address   VARCHAR(45) NULL,
    user_agent   VARCHAR(255) NULL,
    CONSTRAINT uq_rt_token_hash UNIQUE (token_hash),
    CONSTRAINT fk_rt_user FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_rt_user_active ON refresh_tokens(user_id, revoked_at, expires_at);

-- ============================================================================
-- 6. DEPARTMENTS
-- ============================================================================
CREATE TABLE departments (
    department_id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_departments_name UNIQUE (department_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================================
-- 7. DESIGNATIONS
-- ============================================================================
CREATE TABLE designations (
    designation_id   INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title            VARCHAR(100) NOT NULL,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_designations_title UNIQUE (title)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================================
-- 8. EMPLOYEES  (HR profile, 1:1 with users)
-- ============================================================================
CREATE TABLE employees (
    employee_id       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id           BIGINT UNSIGNED NOT NULL,
    employee_code     VARCHAR(30) NOT NULL,
    first_name        VARCHAR(100) NOT NULL,
    last_name         VARCHAR(100) NOT NULL,
    phone             VARCHAR(20) NULL,
    address           VARCHAR(500) NULL,
    date_of_birth     DATE NULL,
    gender             ENUM('MALE','FEMALE','OTHER','PREFER_NOT_TO_SAY') NULL,
    profile_picture_url VARCHAR(500) NULL,
    department_id     INT UNSIGNED NULL,
    designation_id    INT UNSIGNED NULL,
    manager_id        BIGINT UNSIGNED NULL COMMENT 'Self-referencing FK to employees.employee_id',
    joining_date      DATE NOT NULL,
    employment_status ENUM('ACTIVE','INACTIVE','RESIGNED','TERMINATED') NOT NULL DEFAULT 'ACTIVE',
    employment_type   ENUM('FULL_TIME','PART_TIME','CONTRACT','INTERN') NOT NULL DEFAULT 'FULL_TIME',
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_employees_user_id UNIQUE (user_id),
    CONSTRAINT uq_employees_code UNIQUE (employee_code),
    CONSTRAINT fk_employees_user FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_employees_department FOREIGN KEY (department_id) REFERENCES departments(department_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_employees_designation FOREIGN KEY (designation_id) REFERENCES designations(designation_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_employees_manager FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_employees_department ON employees(department_id);
CREATE INDEX idx_employees_designation ON employees(designation_id);
CREATE INDEX idx_employees_manager ON employees(manager_id);
CREATE INDEX idx_employees_status ON employees(employment_status);
CREATE INDEX idx_employees_name ON employees(last_name, first_name);

-- ============================================================================
-- 9. EMPLOYEE DOCUMENTS  (metadata only; file lives in object storage)
-- ============================================================================
CREATE TABLE employee_documents (
    document_id       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    employee_id       BIGINT UNSIGNED NOT NULL,
    document_type     ENUM('RESUME','ID_PROOF','ADDRESS_PROOF','MEDICAL_CERTIFICATE',
                            'JOINING_DOCUMENT','OTHER') NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    storage_path      VARCHAR(1000) NOT NULL COMMENT 'Object storage key / path, not the file itself',
    mime_type         VARCHAR(100) NOT NULL,
    file_size_bytes   BIGINT UNSIGNED NOT NULL,
    uploaded_by       BIGINT UNSIGNED NOT NULL,
    status            ENUM('ACTIVE','ARCHIVED') NOT NULL DEFAULT 'ACTIVE',
    expiry_date       DATE NULL,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_docs_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_docs_uploaded_by FOREIGN KEY (uploaded_by) REFERENCES users(user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_docs_file_size CHECK (file_size_bytes > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_docs_employee ON employee_documents(employee_id, document_type);

-- ============================================================================
-- 10. HOLIDAYS  (company-wide; extendable for per-location later)
-- ============================================================================
CREATE TABLE holidays (
    holiday_id    INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    holiday_date  DATE NOT NULL,
    name          VARCHAR(150) NOT NULL,
    is_recurring  BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'e.g. yearly national holiday',
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_holidays_date UNIQUE (holiday_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================================
-- 11. ATTENDANCE
-- ============================================================================
CREATE TABLE attendance (
    attendance_id     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    employee_id       BIGINT UNSIGNED NOT NULL,
    attendance_date   DATE NOT NULL,
    check_in_at       TIMESTAMP NULL DEFAULT NULL,
    check_out_at      TIMESTAMP NULL DEFAULT NULL,
    work_hours        DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT 'Backend-calculated only, never trust client value',
    overtime_hours    DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    status            ENUM('PRESENT','ABSENT','HALF_DAY','LEAVE','HOLIDAY','WEEKEND') NOT NULL DEFAULT 'ABSENT',
    is_corrected      BOOLEAN NOT NULL DEFAULT FALSE,
    corrected_by      BIGINT UNSIGNED NULL,
    correction_reason VARCHAR(500) NULL,
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_attendance_employee_date UNIQUE (employee_id, attendance_date),
    CONSTRAINT fk_attendance_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_attendance_corrected_by FOREIGN KEY (corrected_by) REFERENCES users(user_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_attendance_checkout CHECK (check_out_at IS NULL OR check_in_at IS NULL OR check_out_at > check_in_at),
    CONSTRAINT chk_attendance_work_hours CHECK (work_hours >= 0),
    CONSTRAINT chk_attendance_overtime CHECK (overtime_hours >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='At most one row per employee per calendar date, enforced by unique key.';

CREATE INDEX idx_attendance_date ON attendance(attendance_date);
CREATE INDEX idx_attendance_status ON attendance(status);
CREATE INDEX idx_attendance_employee_date ON attendance(employee_id, attendance_date DESC);

-- ============================================================================
-- 12. LEAVE TYPES
-- ============================================================================
CREATE TABLE leave_types (
    leave_type_id       TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name                VARCHAR(50) NOT NULL,
    is_balance_tracked  BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'FALSE for e.g. Unpaid Leave',
    requires_attachment BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'e.g. Sick Leave certificate',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_leave_types_name UNIQUE (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ============================================================================
-- 13. LEAVE BALANCES
-- ============================================================================
CREATE TABLE leave_balances (
    leave_balance_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    employee_id      BIGINT UNSIGNED NOT NULL,
    leave_type_id    TINYINT UNSIGNED NOT NULL,
    leave_year       SMALLINT UNSIGNED NOT NULL,
    allocated_days   DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    used_days        DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_leave_balance_emp_type_year UNIQUE (employee_id, leave_type_id, leave_year),
    CONSTRAINT fk_leave_balance_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_leave_balance_type FOREIGN KEY (leave_type_id) REFERENCES leave_types(leave_type_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_leave_balance_used_nonneg CHECK (used_days >= 0),
    CONSTRAINT chk_leave_balance_allocated_nonneg CHECK (allocated_days >= 0),
    CONSTRAINT chk_leave_balance_used_within_allocated CHECK (used_days <= allocated_days)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_leave_balance_employee_year ON leave_balances(employee_id, leave_year);

-- ============================================================================
-- 14. LEAVE REQUESTS
-- ============================================================================
CREATE TABLE leave_requests (
    leave_request_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    employee_id      BIGINT UNSIGNED NOT NULL,
    leave_type_id    TINYINT UNSIGNED NOT NULL,
    start_date       DATE NOT NULL,
    end_date         DATE NOT NULL,
    number_of_days   DECIMAL(5,2) NOT NULL,
    remarks          VARCHAR(1000) NULL,
    attachment_path  VARCHAR(1000) NULL,
    status           ENUM('PENDING','APPROVED','REJECTED','CANCELLED') NOT NULL DEFAULT 'PENDING',
    submitted_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by      BIGINT UNSIGNED NULL,
    reviewed_at      TIMESTAMP NULL DEFAULT NULL,
    review_comment   VARCHAR(1000) NULL,
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_leave_req_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_leave_req_type FOREIGN KEY (leave_type_id) REFERENCES leave_types(leave_type_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_leave_req_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(user_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_leave_req_dates CHECK (start_date <= end_date),
    CONSTRAINT chk_leave_req_days_positive CHECK (number_of_days > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_leave_req_employee ON leave_requests(employee_id, status);
CREATE INDEX idx_leave_req_status ON leave_requests(status);
CREATE INDEX idx_leave_req_date_range ON leave_requests(start_date, end_date);

-- Trigger-based overlap prevention (INSERT): no two PENDING/APPROVED requests
-- of the same employee may share overlapping dates, regardless of leave type.
DELIMITER $$

CREATE TRIGGER trg_leave_requests_no_overlap_ins
BEFORE INSERT ON leave_requests
FOR EACH ROW
BEGIN
    DECLARE overlap_count INT DEFAULT 0;
    IF NEW.status IN ('PENDING','APPROVED') THEN
        SELECT COUNT(*) INTO overlap_count
        FROM leave_requests
        WHERE employee_id = NEW.employee_id
          AND status IN ('PENDING','APPROVED')
          AND start_date <= NEW.end_date
          AND end_date >= NEW.start_date;
        IF overlap_count > 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Overlapping active leave request exists for this employee and date range';
        END IF;
    END IF;
END$$

CREATE TRIGGER trg_leave_requests_no_overlap_upd
BEFORE UPDATE ON leave_requests
FOR EACH ROW
BEGIN
    DECLARE overlap_count INT DEFAULT 0;
    IF NEW.status IN ('PENDING','APPROVED') THEN
        SELECT COUNT(*) INTO overlap_count
        FROM leave_requests
        WHERE employee_id = NEW.employee_id
          AND leave_request_id <> NEW.leave_request_id
          AND status IN ('PENDING','APPROVED')
          AND start_date <= NEW.end_date
          AND end_date >= NEW.start_date;
        IF overlap_count > 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Overlapping active leave request exists for this employee and date range';
        END IF;
    END IF;
END$$

DELIMITER ;

-- ============================================================================
-- 15. LEAVE REQUEST REVIEWS  (audit trail, supports re-review)
-- ============================================================================
CREATE TABLE leave_request_reviews (
    review_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    leave_request_id  BIGINT UNSIGNED NOT NULL,
    reviewer_user_id  BIGINT UNSIGNED NOT NULL,
    previous_status   ENUM('PENDING','APPROVED','REJECTED','CANCELLED') NOT NULL,
    new_status        ENUM('PENDING','APPROVED','REJECTED','CANCELLED') NOT NULL,
    comment           VARCHAR(1000) NULL,
    reviewed_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lrr_request FOREIGN KEY (leave_request_id) REFERENCES leave_requests(leave_request_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_lrr_reviewer FOREIGN KEY (reviewer_user_id) REFERENCES users(user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_lrr_request ON leave_request_reviews(leave_request_id);

-- ============================================================================
-- 16. SALARY STRUCTURES  (versioned; never overwritten)
-- ============================================================================
CREATE TABLE salary_structures (
    salary_structure_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    employee_id          BIGINT UNSIGNED NOT NULL,
    monthly_wage         DECIMAL(12,2) NOT NULL,
    annual_wage          DECIMAL(14,2) NOT NULL,
    wage_type            ENUM('MONTHLY','ANNUAL','HOURLY') NOT NULL DEFAULT 'MONTHLY',
    effective_from        DATE NOT NULL,
    effective_to          DATE NULL COMMENT 'NULL means currently effective',
    is_current            BOOLEAN NOT NULL DEFAULT TRUE,
    created_by            BIGINT UNSIGNED NOT NULL,
    created_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_salary_struct_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_salary_struct_created_by FOREIGN KEY (created_by) REFERENCES users(user_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_salary_monthly_nonneg CHECK (monthly_wage >= 0),
    CONSTRAINT chk_salary_annual_nonneg CHECK (annual_wage >= 0),
    CONSTRAINT chk_salary_dates CHECK (effective_to IS NULL OR effective_to >= effective_from)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='Full history preserved. Only one row per employee should have is_current=TRUE (enforced at application/transaction level).';

CREATE INDEX idx_salary_struct_employee_current ON salary_structures(employee_id, is_current);
CREATE INDEX idx_salary_struct_employee_effective ON salary_structures(employee_id, effective_from DESC);

-- ============================================================================
-- 17. SALARY COMPONENTS  (belong to a specific salary structure version)
-- ============================================================================
CREATE TABLE salary_components (
    salary_component_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    salary_structure_id  BIGINT UNSIGNED NOT NULL,
    component_name        VARCHAR(100) NOT NULL,
    component_type        ENUM('EARNING','DEDUCTION','EMPLOYER_CONTRIBUTION') NOT NULL,
    calculation_type      ENUM('FIXED','PERCENTAGE') NOT NULL,
    percentage_value       DECIMAL(5,2) NULL COMMENT 'Used when calculation_type = PERCENTAGE',
    fixed_amount           DECIMAL(12,2) NULL COMMENT 'Used when calculation_type = FIXED',
    computed_amount        DECIMAL(12,2) NOT NULL COMMENT 'Backend-calculated resolved amount',
    created_at             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_salary_comp_structure FOREIGN KEY (salary_structure_id) REFERENCES salary_structures(salary_structure_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_salary_comp_computed_nonneg CHECK (computed_amount >= 0),
    CONSTRAINT chk_salary_comp_calc_values CHECK (
        (calculation_type = 'FIXED' AND fixed_amount IS NOT NULL)
        OR (calculation_type = 'PERCENTAGE' AND percentage_value IS NOT NULL)
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_salary_comp_structure ON salary_components(salary_structure_id);

-- ============================================================================
-- 18. AUDIT LOGS  (append-only from the application's perspective)
-- ============================================================================
CREATE TABLE audit_logs (
    audit_log_id   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    actor_user_id  BIGINT UNSIGNED NULL COMMENT 'NULL for system-initiated actions',
    action         VARCHAR(60) NOT NULL COMMENT 'e.g. EMPLOYEE_CREATED, SALARY_UPDATED, LEAVE_APPROVED',
    target_entity  VARCHAR(60) NOT NULL COMMENT 'e.g. employees, leave_requests, salary_structures',
    target_id      BIGINT UNSIGNED NULL,
    old_values     JSON NULL,
    new_values     JSON NULL,
    ip_address     VARCHAR(45) NULL,
    user_agent     VARCHAR(255) NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_actor FOREIGN KEY (actor_user_id) REFERENCES users(user_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_audit_actor ON audit_logs(actor_user_id, created_at DESC);
CREATE INDEX idx_audit_target ON audit_logs(target_entity, target_id);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);

-- ============================================================================
-- 19. NOTIFICATIONS  (lightweight, in-app only for MVP — see design doc §Future)
-- ============================================================================
CREATE TABLE notifications (
    notification_id   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    recipient_user_id  BIGINT UNSIGNED NOT NULL,
    type                VARCHAR(50) NOT NULL,
    title               VARCHAR(200) NOT NULL,
    message             VARCHAR(1000) NOT NULL,
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notifications_recipient FOREIGN KEY (recipient_user_id) REFERENCES users(user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE INDEX idx_notifications_recipient_unread ON notifications(recipient_user_id, is_read, created_at DESC);

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
