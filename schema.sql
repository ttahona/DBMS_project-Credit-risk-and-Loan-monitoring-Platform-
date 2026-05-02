-- USER TABLE
CREATE TABLE User (
    user_id CHAR(16) PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(10) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ADMIN TABLE
CREATE TABLE Admin (
    admin_id CHAR(16) PRIMARY KEY,
    user_id CHAR(16) NOT NULL,
    name VARCHAR(100),
    FOREIGN KEY (user_id) REFERENCES User(user_id)
);

-- BRANCH TABLE
CREATE TABLE Branch (
    branch_id INT PRIMARY KEY AUTO_INCREMENT,
    branch_name VARCHAR(100),
    location VARCHAR(100)
);

-- BORROWER TABLE
CREATE TABLE Borrower (
    borrower_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id CHAR(16),
    name VARCHAR(100),
    phone VARCHAR(20),
    address VARCHAR(255),
    email VARCHAR(100),
    dob DATE,
    pan_no VARCHAR(20),
    branch_id INT,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (branch_id) REFERENCES Branch(branch_id)
);

-- STAFF TABLE
CREATE TABLE Staff (
    staff_id CHAR(16) PRIMARY KEY,
    user_id CHAR(16) NOT NULL,
    name VARCHAR(100),
    branch_id INT,
    FOREIGN KEY (user_id) REFERENCES User(user_id),
    FOREIGN KEY (branch_id) REFERENCES Branch(branch_id)
);

-- RISK_BUCKET TABLE
CREATE TABLE Risk_Bucket (
    bucket_id INT PRIMARY KEY,
    bucket_name VARCHAR(50)
);

-- LOAN TABLE
CREATE TABLE Loan (
    loan_id INT PRIMARY KEY AUTO_INCREMENT,
    borrower_id INT,
    branch_id INT,
    approved_by CHAR(16),
    amount FLOAT,
    interest_rate FLOAT,
    start_date DATE,
    loan_type VARCHAR(50),
    tenure_months INT,
    status VARCHAR(50),
    FOREIGN KEY (borrower_id) REFERENCES Borrower(borrower_id),
    FOREIGN KEY (branch_id) REFERENCES Branch(branch_id),
    FOREIGN KEY (approved_by) REFERENCES Staff(staff_id)
);

-- PAYMENT TABLE
CREATE TABLE Payment (
    payment_id INT PRIMARY KEY AUTO_INCREMENT,
    loan_id INT,
    payment_date DATE,
    amount_paid FLOAT,
    payment_mode VARCHAR(50),
    FOREIGN KEY (loan_id) REFERENCES Loan(loan_id)
);

-- EMI_SCHEDULE TABLE
CREATE TABLE EMI_Schedule (
    emi_id INT PRIMARY KEY AUTO_INCREMENT,
    loan_id INT,
    emi_number INT,
    due_date DATE,
    amount_due FLOAT,
    status VARCHAR(50),
    FOREIGN KEY (loan_id) REFERENCES Loan(loan_id)
);

-- PAYMENT_ALLOCATION TABLE
CREATE TABLE Payment_Allocation (
    allocation_id INT PRIMARY KEY AUTO_INCREMENT,
    payment_id INT,
    emi_id INT,
    allocated_amount FLOAT,
    FOREIGN KEY (payment_id) REFERENCES Payment(payment_id),
    FOREIGN KEY (emi_id) REFERENCES EMI_Schedule(emi_id)
);

-- LOAN_RISK_STATUS TABLE
CREATE TABLE Loan_Risk_Status (
    risk_id INT PRIMARY KEY AUTO_INCREMENT,
    loan_id INT UNIQUE,
    bucket_id INT,
    assessed_date DATE,
    FOREIGN KEY (loan_id) REFERENCES Loan(loan_id),
    FOREIGN KEY (bucket_id) REFERENCES Risk_Bucket(bucket_id)
);

-- AUDIT_LOG TABLE
CREATE TABLE Audit_Log (
    log_id INT PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(50),
    record_id INT,
    action VARCHAR(50),
    changed_by VARCHAR(50),
    change_date DATE,
    old_value TEXT,
    new_value TEXT
);

-- RISK_BUCKET SEED DATA
INSERT INTO Risk_Bucket (bucket_id, bucket_name) VALUES
    (1, 'Current'),
    (2, '30+ Days'),
    (3, '60+ Days'),
    (4, '90+ Days');
