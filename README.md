# AI Data Quality Validator

An enterprise proof of concept demonstrating how AI-assisted schema mapping, automated data validation, and executive reporting can streamline financial data quality workflows while keeping sensitive data within a controlled cloud environment.

---

## Overview

Financial institutions routinely receive loan portfolio data from external vendors in inconsistent JSON formats. Before the data can be trusted for reporting and analytics, analysts must manually map vendor fields to an enterprise database schema, validate records against business rules, clean malformed values, and document data quality issues.

This project demonstrates how an organization could use Zerve to automate much of that process while keeping analysts focused on records that require human judgment. AI is used where it provides value through semantic schema mapping and executive insight generation, while deterministic Python logic performs repeatable validation and transformation.

---

## Business Problem

Although AI can significantly reduce manual data preparation, many regulated organizations cannot upload sensitive financial data to public AI services or third-party conversion tools because of security, privacy, and compliance requirements.

This proof of concept demonstrates how Zerve's self-hosted deployment model can support AI-assisted data quality workflows while allowing organizations to maintain control of sensitive data within their own AWS environment.

---

## Workflow

The workflow performs the following steps:

1. Seed a SQLite loan portfolio database with representative financial data.
2. Load records using a configurable date range.
3. Define the target enterprise SQL schema and business rules.
4. Perform AI-assisted semantic schema mapping with confidence scoring.
5. Generate a schema mapping review table.
6. Clean and transform incoming data.
7. Validate business rules and detect data quality issues.
8. Produce an Executive Data Quality Dashboard.
9. Build structured AI context from validation results.
10. Generate an AI-assisted executive narrative summarizing data quality findings and recommendations.

---

## Key Features

- AI-assisted semantic schema mapping
- Automated data validation and transformation
- Business rule enforcement
- Duplicate record detection
- Executive Data Quality Dashboard
- AI-generated executive insights
- SQL-ready output dataset
- SQLite relational database backend

---

## Dataset

The project uses a representative loan portfolio dataset containing **205 records** stored in a SQLite database.

Example fields include:

- LOAN_ID
- BORROWER_NAME
- CURRENT_UPB
- INTEREST_RATE
- LOAN_STATUS
- ORIGINATION_DATE
- NEXT_PAYMENT_DATE
- PROPERTY_STATE
- SERVICER
- CREDIT_SCORE

To simulate real-world enterprise data quality challenges, the dataset intentionally includes:

- Duplicate loan IDs
- Missing required fields
- Invalid interest rates
- Malformed balances
- Mixed date formats
- Invalid state codes
- Out-of-range credit scores
- Vendor field names that differ from the enterprise schema

---

## Outputs

The workflow produces:

- AI Schema Mapping Report
- Data Validation Summary
- Executive Data Quality Dashboard
- SQL-ready validated dataset
- AI-generated executive narrative with recommendations

---

## Technologies

- Python
- SQLite
- Pandas
- Matplotlib
- Zerve
- GitHub

---

## Project Structure

```
0. Seed Loan Portfolio Database
1. Data Ingestion – Vendor JSON & SQL Schema
2. AI Schema Mapping Engine
3. Mapping Report Table
4. Data Validation & Transformation
5. Data Quality Report
6. AI Executive Insights
7. Executive Insights Narrative
```

---

## Project Purpose

Rather than demonstrating predictive modeling, this project focuses on solving a practical enterprise data quality problem. It illustrates how AI can be integrated into a secure analytics workflow to automate repetitive data preparation tasks while maintaining transparency, governance, and auditability.

The result is a proof of concept that reduces manual analyst effort, improves data quality, and produces executive-ready reporting without relying on sensitive production data.
