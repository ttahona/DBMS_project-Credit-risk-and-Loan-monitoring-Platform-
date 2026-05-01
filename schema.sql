-- BORROWER TABLE
CREATE TABLE Borrower (
    borrower_id INT PRIMARY KEY,
    name VARCHAR(100),
    phone VARCHAR(20),
    address VARCHAR(255),
    email VARCHAR(100),
    dob DATE,
    pan_no VARCHAR(20)
);

-- BRANCH TABLE
CREATE TABLE Branch (
    branch_id INT PRIMARY KEY,
    branch_name VARCHAR(100),
    location VARCHAR(100)
);

-- RISK_BUCKET TABLE
CREATE TABLE Risk_Bucket (
    bucket_id INT PRIMARY KEY,
    bucket_name VARCHAR(50)
);

-- LOAN TABLE
CREATE TABLE Loan (
    loan_id INT PRIMARY KEY,
    borrower_id INT,
    branch_id INT,
    bucket_id INT,
    amount FLOAT,
    interest_rate FLOAT,
    start_date DATE,
    loan_type VARCHAR(50),
    tenure_months INT,
    status VARCHAR(50),
    FOREIGN KEY (borrower_id) REFERENCES Borrower(borrower_id),
    FOREIGN KEY (branch_id) REFERENCES Branch(branch_id),
    FOREIGN KEY (bucket_id) REFERENCES Risk_Bucket(bucket_id)
);

-- PAYMENT TABLE
CREATE TABLE Payment (
    payment_id INT PRIMARY KEY,
    loan_id INT,
    payment_date DATE,
    amount_paid FLOAT,
    payment_mode VARCHAR(50),
    FOREIGN KEY (loan_id) REFERENCES Loan(loan_id)
);

-- EMI_SCHEDULE TABLE
CREATE TABLE EMI_Schedule (
    emi_id INT PRIMARY KEY,
    loan_id INT,
    emi_number INT,
    due_date DATE,
    amount_due FLOAT,
    status VARCHAR(50),
    FOREIGN KEY (loan_id) REFERENCES Loan(loan_id)
);

-- PAYMENT_ALLOCATION TABLE
CREATE TABLE Payment_Allocation (
    allocation_id INT PRIMARY KEY,
    payment_id INT,
    emi_id INT,
    allocated_amount FLOAT,
    FOREIGN KEY (payment_id) REFERENCES Payment(payment_id),
    FOREIGN KEY (emi_id) REFERENCES EMI_Schedule(emi_id)
);

-- AUDIT_LOG TABLE
CREATE TABLE Audit_Log (
    log_id INT PRIMARY KEY,
    table_name VARCHAR(50),
    record_id INT,
    action VARCHAR(50),
    changed_by VARCHAR(50),
    change_date DATE,
    old_value TEXT,
    new_value TEXT
);
