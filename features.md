# 🚀 Features - Credit Risk & Loan Monitoring Platform

This document explains the key functionalities of the Credit Risk & Loan Monitoring System.

---

## 1️⃣ Borrower & Loan Management
- Store and manage detailed borrower profiles
- Support multiple loans per borrower
- Track loan status such as Active, Closed, Defaulted, and Written-off
- Maintain relational integrity between borrowers and loans

---

## 2️⃣ EMI & Repayment Scheduling
- Automatically generate EMI schedules based on loan amount, interest rate, and tenure
- Maintain installment-wise tracking of due dates and payment status
- Ensure structured repayment flow for each loan

---

## 3️⃣ Payment Processing System
- Record all loan payments made by borrowers
- Allocate payments to specific EMI installments
- Support partial payments and update remaining balances automatically
- Maintain accurate repayment history

---

## 4️⃣ Delinquency & Risk Classification
- Identify overdue EMIs based on due dates
- Classify loans into risk categories:
  - Current
  - 30+ days overdue
  - 60+ days overdue
  - 90+ days overdue
- Helps simulate real-world credit risk monitoring

---

## 5️⃣ Portfolio Analytics & Reporting
- Generate Portfolio at Risk (PAR) reports
- Track total outstanding loans and repayments
- Analyze collection efficiency
- Support branch-wise or borrower-wise performance insights

---

## 6️⃣ Audit Logging & Data Integrity
- Enforce primary and foreign key constraints
- Use triggers to maintain automatic updates
- Maintain audit logs for important database operations
- Ensure consistency and reliability of data

---
