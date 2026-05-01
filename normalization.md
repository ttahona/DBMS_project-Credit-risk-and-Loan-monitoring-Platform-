# Database Normalization – Credit Risk & Loan Monitoring System

## 📌 Objective

The goal of normalization is to organize the database structure to:

* Reduce data redundancy
* Eliminate update anomalies
* Ensure data integrity
* Improve scalability and maintainability

This database has been normalized up to **Third Normal Form (3NF)**.

---

# 🟢 First Normal Form (1NF)

## Rules Applied:

* All attributes are atomic (no multi-valued fields)
* Each table has a primary key
* No repeating groups or nested structures

## Implementation:

* Each entity (Borrower, Loan, Payment, EMI_Schedule, etc.) is stored in a separate table
* Attributes such as `name`, `amount`, `status` store single values only
* Unique identifiers like `borrower_id`, `loan_id`, and `payment_id` are used as primary keys

## Result:

The database structure satisfies 1NF as all fields are atomic and uniquely identifiable.

---

# 🔵 Second Normal Form (2NF)

## Rules Applied:

* Must be in 1NF
* No partial dependency on a composite primary key

## Implementation:

* All tables use **single-column primary keys** (e.g., `loan_id`, `emi_id`)
* No table contains attributes that depend on only part of a key
* The `Payment_Allocation` table avoids composite key issues by using `allocation_id` as a surrogate primary key

## Result:

All non-key attributes fully depend on the entire primary key, ensuring compliance with 2NF.

---

# 🟣 Third Normal Form (3NF)

## Rules Applied:

* Must be in 2NF
* No transitive dependencies (non-key attributes depending on other non-key attributes)

## Key Design Decision:

### Removal of Transitive Dependency in Loan Table

Originally:

* Risk classification (`bucket_id`) was associated with Loan
* However, risk is derived from loan behavior (e.g., overdue days)

This created a transitive dependency:
loan_id → days_past_due → bucket_id

## Solution:

* Removed `bucket_id` from the **Loan** table
* Introduced a separate table: `Loan_Risk_Status`

This ensures:

* Risk classification is handled independently
* Derived data is not redundantly stored
* The schema remains flexible for recalculation of risk over time

## Result:

The schema satisfies 3NF as all attributes depend only on the primary key and not on other non-key attributes.

---

# 🟡 Final Normalized Tables

The following tables exist in the final schema:

* Borrower
* Branch
* Loan
* Risk_Bucket
* Loan_Risk_Status
* EMI_Schedule
* Payment
* Payment_Allocation
* Audit_Log

---

# 🔶 Additional Design Considerations

## Data Integrity

* Foreign key constraints ensure referential integrity
* Relationships between borrower, loan, payment, and EMI are properly enforced

## Scalability

* Separation of risk classification allows dynamic recalculation
* Payment allocation supports partial and multi-instalment payments

## Auditability

* Audit_Log table tracks all changes for transparency and debugging

---

# ✅ Conclusion

The database is successfully normalized up to **Third Normal Form (3NF)**:

* 1NF ensures atomic structure
* 2NF removes partial dependencies
* 3NF eliminates transitive dependencies

This results in a robust, efficient, and scalable database design suitable for real-world **credit risk and loan monitoring systems**.
