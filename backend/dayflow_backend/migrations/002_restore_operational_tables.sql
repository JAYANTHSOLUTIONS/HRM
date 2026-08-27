-- Restore tables omitted from a partially initialized Dayflow database.
-- Safe to run when some or all of these tables already exist.
USE dayflow_hrms;

CREATE TABLE IF NOT EXISTS leave_balances (
    leave_balance_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id BIGINT NOT NULL,
    leave_type_id INT NOT NULL,
    leave_year SMALLINT NOT NULL,
    allocated_days DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    used_days DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_leave_balance_emp_type_year (employee_id, leave_type_id, leave_year),
    CONSTRAINT fk_leave_balance_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_leave_balance_type FOREIGN KEY (leave_type_id) REFERENCES leave_types(leave_type_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS leave_requests (
    leave_request_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id BIGINT NOT NULL,
    leave_type_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    number_of_days DECIMAL(5,2) NOT NULL,
    remarks VARCHAR(1000) NULL,
    attachment_path VARCHAR(1000) NULL,
    status ENUM('PENDING','APPROVED','REJECTED','CANCELLED') NOT NULL DEFAULT 'PENDING',
    submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_by BIGINT NULL,
    reviewed_at TIMESTAMP NULL DEFAULT NULL,
    review_comment VARCHAR(1000) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_leave_req_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_leave_req_type FOREIGN KEY (leave_type_id) REFERENCES leave_types(leave_type_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_leave_req_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(user_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS leave_request_reviews (
    review_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    leave_request_id BIGINT NOT NULL,
    reviewer_user_id BIGINT NOT NULL,
    previous_status ENUM('PENDING','APPROVED','REJECTED','CANCELLED') NOT NULL,
    new_status ENUM('PENDING','APPROVED','REJECTED','CANCELLED') NOT NULL,
    comment VARCHAR(1000) NULL,
    reviewed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lrr_request FOREIGN KEY (leave_request_id) REFERENCES leave_requests(leave_request_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_lrr_reviewer FOREIGN KEY (reviewer_user_id) REFERENCES users(user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS salary_structures (
    salary_structure_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    employee_id BIGINT NOT NULL,
    monthly_wage DECIMAL(12,2) NOT NULL,
    annual_wage DECIMAL(14,2) NOT NULL,
    wage_type ENUM('MONTHLY','ANNUAL','HOURLY') NOT NULL DEFAULT 'MONTHLY',
    effective_from DATE NOT NULL,
    effective_to DATE NULL,
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    created_by BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_salary_struct_employee FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_salary_struct_created_by FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS salary_components (
    salary_component_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    salary_structure_id BIGINT NOT NULL,
    component_name VARCHAR(100) NOT NULL,
    component_type ENUM('EARNING','DEDUCTION','EMPLOYER_CONTRIBUTION') NOT NULL,
    calculation_type ENUM('FIXED','PERCENTAGE') NOT NULL,
    percentage_value DECIMAL(5,2) NULL,
    fixed_amount DECIMAL(12,2) NULL,
    computed_amount DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_salary_comp_structure FOREIGN KEY (salary_structure_id) REFERENCES salary_structures(salary_structure_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB;