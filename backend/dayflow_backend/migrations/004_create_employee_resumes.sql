-- 004_create_employee_resumes.sql
-- Create employee_resumes table for structured employee resumes

CREATE TABLE IF NOT EXISTS employee_resumes (
    employee_id BIGINT PRIMARY KEY,
    about VARCHAR(2000) NULL,
    what_i_love VARCHAR(2000) NULL,
    interests VARCHAR(2000) NULL,
    skills JSON NULL,
    certifications JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
);
