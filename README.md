# DBMS Project: Credit Risk & Loan Monitoring Platform

A MySQL-based Credit Risk & Loan Monitoring System that simulates a simplified core banking loan management platform.  
It manages borrowers, loans, EMI schedules, payments, delinquency tracking, and portfolio risk analysis using relational database design, triggers, and stored procedures.

---

## 📌 Project Overview

This system is designed to replicate key functionalities of a basic banking loan monitoring system, focusing on credit risk management and repayment tracking. It ensures data consistency, automated processing, and risk-based reporting.

---

## 🚀 Features

### 1️⃣ Borrower & Loan Management
- Maintain complete borrower profiles
- Manage multiple loans per borrower
- Track loan status (Active, Closed, Defaulted, Written-off)

### 2️⃣ Automated EMI & Repayment Scheduling
- Generate installment schedules based on loan terms
- Track due dates, EMI amounts, and payment status

### 3️⃣ Payment Processing & Allocation
- Record loan payments
- Allocate payments to specific EMIs
- Support partial payments and balance updates

### 4️⃣ Delinquency & Risk Classification
- Detect overdue installments automatically
- Classify loans into risk buckets (Current, 30/60/90+ days overdue)

### 5️⃣ Portfolio Analytics & Reporting
- Portfolio at Risk (PAR) reports
- Collection rate analysis
- Branch-wise performance tracking
- Outstanding loan summaries

### 6️⃣ Audit Logging & Data Integrity
- Enforced primary and foreign key constraints
- Trigger-based validations
- Audit logs for tracking changes

---

# 🗂️ Folder Structure

The project is organized into the following directories:

- `docs/` → Contains ER diagram, schema diagram, and documentation files  
- `sql/` → Contains all SQL scripts including schema, triggers, and procedures
