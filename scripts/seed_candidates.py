"""
Database Seed Script: 20 Realistic Fictional Candidate Records
Target: Talent Pool / Candidate Screening System

Creates exactly 20 diverse, realistic Indian tech professional profiles:
- Freshers (0 - 1y)
- 1-2 years experience
- 3-5 years experience
- 6-8 years experience
- 8+ years experience

For each candidate, safely and idempotently persists:
- Candidate record (demographics, skills, salary, notice, locations, education)
- Linked Mail record (simulating received application email)
- Linked Application record (with role, expected CTC, question answers)
- Linked Resume record (with full realistic resume text content and hash)

Usage:
  python scripts/seed_candidates.py
"""

import asyncio
import hashlib
import os
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.models import Application, Candidate, Mail, Resume


CANDIDATE_DATA: List[Dict[str, Any]] = [
    # -------------------------------------------------------------------------
    # 1. Freshers (0 - 1 years)
    # -------------------------------------------------------------------------
    {
        "role_category": "QA Automation Engineer",
        "full_name": "Aarav Nair",
        "email": "aarav.nair.qa@talentseed.dev",
        "phone": "+91 98450 11021",
        "headline": "QA Automation Engineer | Python, Selenium & API Automation Specialist",
        "current_company": "LTIMindtree",
        "experience_years": Decimal("0.5"),
        "current_ctc_lpa": Decimal("4.50"),
        "expected_ctc_lpa": Decimal("6.50"),
        "notice_raw": "Immediate",
        "notice_days_max": 0,
        "location": "Chennai, Tamil Nadu",
        "preferred_locations": ["Chennai", "Bengaluru", "Remote"],
        "education": "B.Tech in Information Technology, Anna University, Chennai (2025)",
        "skills": ["Selenium", "Python", "PyTest", "Postman", "Git", "SQL", "TestNG", "JIRA"],
        "job_title": "QA Automation Engineer",
        "answers": [
            {"question": "Are you comfortable writing test automation scripts in Python?", "answer": "Yes, extensive experience with PyTest and Selenium WebDriver."},
            {"question": "What is your earliest joining date?", "answer": "Immediate joining available."}
        ],
        "resume_text": """AARAV NAIR
Email: aarav.nair.qa@talentseed.dev | Phone: +91 98450 11021 | Location: Chennai, Tamil Nadu

PROFESSIONAL SUMMARY
Quality Assurance Automation Engineer with strong foundation in test automation frameworks, Python, Selenium WebDriver, and REST API testing. Passionate about software reliability, CI test automation, and regression test suites.

TECHNICAL SKILLS
- Automation Tools: Selenium WebDriver, PyTest, Postman, TestNG
- Languages: Python, Core Java, SQL
- API Testing: Postman, REST Assured, JSON validation
- Version Control & Tools: Git, GitHub, JIRA, Jenkins

EXPERIENCE
LTIMindtree | Associate QA Engineer Intern (Jul 2025 – Present)
- Developed and maintained automated regression test suites using Selenium WebDriver and PyTest, reducing manual execution time by 40%.
- Created automated API test collections in Postman for validating JSON payload schemas and status codes across 25+ microservices.
- Logged and tracked 60+ critical and major defects in JIRA, working closely with backend developers to ensure timely bug fixes.
- Integrated automated tests into daily Jenkins build pipelines for continuous test reporting.

ACADEMIC PROJECTS
- E-Commerce Test Automation Suite: End-to-end Python/PyTest automation framework for shopping portal with HTML reports and cross-browser execution.
- Student Portal API Test Suite: Automated Postman Newman collection verifying JWT auth, profile updates, and role-based access control.

EDUCATION
- B.Tech in Information Technology | Anna University, Chennai (2021 – 2025) | CGPA: 8.4/10
"""
    },
    {
        "role_category": "Data Analyst",
        "full_name": "Sneha Ranganathan",
        "email": "sneha.ranganathan.da@talentseed.dev",
        "phone": "+91 98450 11022",
        "headline": "Associate Data Analyst | SQL, Power BI & Exploratory Data Analysis",
        "current_company": "Mu Sigma",
        "experience_years": Decimal("0.8"),
        "current_ctc_lpa": Decimal("5.00"),
        "expected_ctc_lpa": Decimal("7.50"),
        "notice_raw": "15 Days",
        "notice_days_max": 15,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Hyderabad"],
        "education": "B.Sc in Statistics & Computer Science, St. Joseph's University, Bengaluru (2025)",
        "skills": ["SQL", "Python", "Pandas", "Power BI", "Tableau", "Excel", "Data Cleaning", "Statistics"],
        "job_title": "Data Analyst",
        "answers": [
            {"question": "How proficient are you in writing complex SQL queries and window functions?", "answer": "Very proficient in subqueries, CTEs, self-joins, and window analytical functions."},
            {"question": "Which visualization tools have you used in production?", "answer": "Power BI and Tableau dashboards for executive KPI reporting."}
        ],
        "resume_text": """SNEHA RANGANATHAN
Email: sneha.ranganathan.da@talentseed.dev | Phone: +91 98450 11022 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Detail-oriented Data Analyst with 9+ months of hands-on experience in exploratory data analysis, business intelligence dashboards, SQL query optimization, and statistical modeling using Python and Power BI.

TECHNICAL SKILLS
- Query Languages: SQL (PostgreSQL, MySQL, SQL Server)
- Analytics & Scripting: Python (Pandas, NumPy, Matplotlib, Seaborn)
- BI & Visualization: Power BI, Tableau, Advanced Excel (Power Query, DAX)
- Concepts: Descriptive Statistics, Hypothesis Testing, Cohort Analysis

EXPERIENCE
Mu Sigma | Trainee Decision Scientist (Aug 2025 – Present)
- Formulated complex SQL queries involving multi-table joins, CTEs, and window functions to extract transaction metrics for retail clients.
- Built 8 interactive Power BI dashboards tracking monthly revenue, customer churn, and regional sales performance.
- Automated weekly data scrubbing and normalization pipelines using Python Pandas, saving 6 hours of manual spreadsheet work per week.
- Conducted cohort retention analyses to identify customer drop-off points during onboarding.

PROJECTS
- Retail Customer Segmentation: Analyzed 200,000 transaction records using Python RFM analysis and visualized buying patterns in Tableau.
- Healthcare Appointment No-Show Analysis: Statistical correlation analysis identifying key variables predicting patient cancellations.

EDUCATION
- B.Sc in Statistics & Computer Science | St. Joseph's University, Bengaluru (2022 – 2025) | CGPA: 8.8/10
"""
    },
    {
        "role_category": "UI/Frontend Developer",
        "full_name": "Rohan Deshmukh",
        "email": "rohan.deshmukh.ui@talentseed.dev",
        "phone": "+91 98450 11023",
        "headline": "Frontend Developer | React, Tailwind CSS & Responsive Web Design",
        "current_company": "Persistent Systems",
        "experience_years": Decimal("1.0"),
        "current_ctc_lpa": Decimal("5.50"),
        "expected_ctc_lpa": Decimal("8.00"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Pune, Maharashtra",
        "preferred_locations": ["Pune", "Mumbai", "Remote"],
        "education": "B.E. in Computer Engineering, Pune Institute of Computer Technology (PICT) (2024)",
        "skills": ["HTML5", "CSS3", "JavaScript", "React", "Tailwind CSS", "Redux Toolkit", "Figma", "Git"],
        "job_title": "UI / Frontend Developer",
        "answers": [
            {"question": "Do you have experience translating Figma wireframes into pixel-perfect responsive layouts?", "answer": "Yes, I regularly convert Figma design tokens and component specs into Tailwind/React components."},
            {"question": "Are you comfortable with modern React hooks and state management?", "answer": "Yes, comfortable with Redux Toolkit, Context API, and custom hooks."}
        ],
        "resume_text": """ROHAN DESHMUKH
Email: rohan.deshmukh.ui@talentseed.dev | Phone: +91 98450 11023 | Location: Pune, Maharashtra

PROFESSIONAL SUMMARY
Creative and user-centric Frontend Developer with 1 year of experience building responsive, accessible, and high-performance web applications using React, Tailwind CSS, and modern JavaScript (ES6+).

TECHNICAL SKILLS
- Frontend Core: HTML5, CSS3, JavaScript (ES6+), TypeScript Basics
- Frameworks & Libraries: React.js, Redux Toolkit, React Router, Tailwind CSS
- Design Tools: Figma, Zeplin, Adobe XD
- Testing & Tooling: Jest, React Testing Library, Vite, npm, Git

EXPERIENCE
Persistent Systems | Junior Frontend Engineer (Jul 2024 – Present)
- Implemented 15+ reusable React UI components conforming to internal design system guidelines and WCAG 2.1 accessibility standards.
- Re-architected legacy CSS stylesheets into atomic Tailwind CSS utilities, improving Lighthouse performance score from 68 to 92.
- Integrated RESTful endpoints into stateful React components using Axios and React Query for asynchronous data caching.
- Collaborated with UX designers to translate interactive Figma prototypes into production-ready web pages.

PROJECTS
- SaaS Billing Dashboard: Responsive billing portal featuring dynamic pricing tiers, invoices preview, and dark mode toggling.
- Developer Portfolio & Blog: Fast-loading static blog built with React and Vite with Markdown parsing and syntax highlighting.

EDUCATION
- B.E. in Computer Engineering | Pune Institute of Computer Technology (PICT) (2020 – 2024) | First Class with Distinction
"""
    },
    {
        "role_category": "Software Engineer",
        "full_name": "Divya Varma",
        "email": "divya.varma.swe@talentseed.dev",
        "phone": "+91 98450 11024",
        "headline": "Associate Software Engineer | Core CS, Algorithms & Python Systems",
        "current_company": "Wipro",
        "experience_years": Decimal("1.0"),
        "current_ctc_lpa": Decimal("5.20"),
        "expected_ctc_lpa": Decimal("7.50"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Kochi, Kerala",
        "preferred_locations": ["Kochi", "Bengaluru", "Trivandrum"],
        "education": "B.Tech in Computer Science, NIT Calicut (2024)",
        "skills": ["Python", "C++", "Data Structures", "Algorithms", "PostgreSQL", "Linux", "REST APIs", "Git"],
        "job_title": "Software Engineer",
        "answers": [
            {"question": "How comfortable are you with algorithms and asynchronous Python programming?", "answer": "Strong algorithmic background from competitive programming and 1 year writing production async Python."},
            {"question": "Are you willing to work in a hybrid model in Bengaluru or Kochi?", "answer": "Yes, willing to relocate to Bengaluru or work in Kochi."}
        ],
        "resume_text": """DIVYA VARMA
Email: divya.varma.swe@talentseed.dev | Phone: +91 98450 11024 | Location: Kochi, Kerala

PROFESSIONAL SUMMARY
Analytical Software Engineer with a solid foundation in computer science fundamentals, data structures, algorithms, and modular software design. Experienced in Python backends, database query optimization, and REST API development.

TECHNICAL SKILLS
- Programming: Python, C++, SQL, Bash scripting
- Backend & Frameworks: FastAPI, Flask, SQLAlchemy
- Databases: PostgreSQL, SQLite
- Fundamentals: Operating Systems, Computer Networks, Object-Oriented Design, Linux

EXPERIENCE
Wipro | Software Engineer (Aug 2024 – Present)
- Engineered backend data transformation utilities in Python processing 500,000+ daily records from insurance client feeds.
- Optimized slow PostgreSQL queries and created strategic indexing, reducing batch data processing latency by 35%.
- Implemented unit and integration tests achieving 88% code coverage using PyTest.
- Authored internal technical documentation and API specifications using OpenAPI (Swagger).

PROJECTS
- Distributed Key-Value Store: Lightweight in-memory distributed store with Raft consensus written in Python.
- Algorithmic Trading Backtester: Event-driven historical market simulation engine calculating Sharpe ratio and max drawdown.

EDUCATION
- B.Tech in Computer Science and Engineering | National Institute of Technology (NIT) Calicut (2020 – 2024) | CGPA: 8.7/10
"""
    },

    # -------------------------------------------------------------------------
    # 2. 1–2 Years Experience
    # -------------------------------------------------------------------------
    {
        "role_category": "React Developer",
        "full_name": "Aditya Kulkarni",
        "email": "aditya.kulkarni.react@talentseed.dev",
        "phone": "+91 98450 11025",
        "headline": "React Developer | TypeScript, Next.js & Modern Frontend Architecture",
        "current_company": "Zomato",
        "experience_years": Decimal("2.0"),
        "current_ctc_lpa": Decimal("9.00"),
        "expected_ctc_lpa": Decimal("13.00"),
        "notice_raw": "15 Days",
        "notice_days_max": 15,
        "location": "Gurugram, Haryana",
        "preferred_locations": ["Gurugram", "Noida", "Delhi NCR", "Remote"],
        "education": "B.Tech in Computer Science, DTU (Delhi Technological University) (2023)",
        "skills": ["React", "TypeScript", "Next.js", "Redux Toolkit", "REST APIs", "Jest", "Tailwind CSS", "Webpack"],
        "job_title": "React Frontend Engineer",
        "answers": [
            {"question": "How much experience do you have with TypeScript in React projects?", "answer": "Over 1.5 years using strict TypeScript interfaces, generics, and component props."},
            {"question": "Have you worked with Next.js SSR and SSG?", "answer": "Yes, built several merchant landing pages and portals with Next.js 14 App Router."}
        ],
        "resume_text": """ADITYA KULKARNI
Email: aditya.kulkarni.react@talentseed.dev | Phone: +91 98450 11025 | Location: Gurugram, Haryana

PROFESSIONAL SUMMARY
Software Engineer specializing in modern frontend engineering with React, TypeScript, and Next.js. 2 years of experience developing high-traffic, performance-critical user interfaces and merchant portals.

TECHNICAL SKILLS
- Languages: TypeScript, JavaScript (ES6+), HTML5, CSS3
- Frontend: React.js, Next.js, Redux Toolkit, React Query, Zustand
- Styling: Tailwind CSS, Styled Components, Material UI
- Build & Test: Vite, Webpack, Jest, React Testing Library, ESLint

EXPERIENCE
Zomato | Frontend Software Engineer (Jul 2023 – Present)
- Developed critical merchant order management modules handling 50,000+ daily concurrent merchant transactions using React and TypeScript.
- Migrated legacy client-side rendered dashboards to Next.js App Router with Server Components, slashing First Contentful Paint (FCP) by 45%.
- Implemented real-time order tracking notifications using WebSockets and Redux state synchronization.
- Mentored 2 junior interns on component modularity, state normalization, and TypeScript best practices.

PROJECTS
- Restaurant Analytics Portal: High-volume data table with virtualized scrolling, dynamic filtering, and CSV export capabilities.
- Component Library Showcase: Storybook documentation site for 40+ atomic UI components used across company web properties.

EDUCATION
- B.Tech in Computer Science | Delhi Technological University (DTU) (2019 – 2023) | CGPA: 8.5/10
"""
    },
    {
        "role_category": "Node.js Developer",
        "full_name": "Tanvi Hegde",
        "email": "tanvi.hegde.node@talentseed.dev",
        "phone": "+91 98450 11026",
        "headline": "Node.js Backend Developer | TypeScript, Express, Redis & Event-Driven APIs",
        "current_company": "Swiggy",
        "experience_years": Decimal("2.0"),
        "current_ctc_lpa": Decimal("10.50"),
        "expected_ctc_lpa": Decimal("15.00"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Remote"],
        "education": "B.E. in Information Science, RV College of Engineering, Bengaluru (2023)",
        "skills": ["Node.js", "Express.js", "TypeScript", "MongoDB", "PostgreSQL", "Redis", "Docker", "Jest", "Microservices"],
        "job_title": "Node.js Developer",
        "answers": [
            {"question": "How do you handle distributed caching and cache invalidation in Node.js?", "answer": "Using Redis with TTL policies, Redis Pub/Sub, and write-through cache patterns."},
            {"question": "What is your experience with asynchronous message queues?", "answer": "Implemented BullMQ and RabbitMQ workers for background notification dispatch."}
        ],
        "resume_text": """TANVI HEGDE
Email: tanvi.hegde.node@talentseed.dev | Phone: +91 98450 11026 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Backend Engineer with 2 years of experience designing scalable microservices, RESTful APIs, and event-driven architectures using Node.js, TypeScript, PostgreSQL, and Redis.

TECHNICAL SKILLS
- Runtime & Frameworks: Node.js, Express.js, Nest.js, Fastify
- Languages: TypeScript, JavaScript, SQL
- Databases & Caching: PostgreSQL, MongoDB, Redis
- Tools: Docker, Jest, Supertest, BullMQ, Git, Postman

EXPERIENCE
Swiggy | Backend Engineer (Aug 2023 – Present)
- Engineered high-throughput microservices in Node.js/TypeScript processing delivery partner dispatch events at 3,000 requests/sec.
- Implemented multi-tier caching with Redis, reducing database read pressure on core catalog clusters by 55%.
- Built idempotent webhook integration for payment gateway status callbacks, eliminating double-credit bugs.
- Designed comprehensive test suites with Jest and Supertest achieving over 90% branch coverage.

PROJECTS
- Real-Time Fleet Telemetry Service: Node.js WebSocket service streaming live GPS coordinates with GeoJSON calculations.
- Distributed Task Scheduler: Resilient background job queue engine using Redis streams and worker concurrency controls.

EDUCATION
- B.E. in Information Science and Engineering | RV College of Engineering (RVCE), Bengaluru (2019 – 2023) | CGPA: 9.1/10
"""
    },
    {
        "role_category": "Mobile Developer",
        "full_name": "Karthik Sundaram",
        "email": "karthik.sundaram.mobile@talentseed.dev",
        "phone": "+91 98450 11027",
        "headline": "Mobile Developer | Flutter, Kotlin, Bloc State Architecture & Performance Tuning",
        "current_company": "PhonePe",
        "experience_years": Decimal("2.0"),
        "current_ctc_lpa": Decimal("11.00"),
        "expected_ctc_lpa": Decimal("16.00"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Chennai", "Remote"],
        "education": "B.Tech in Computer Science, PSG College of Technology, Coimbatore (2023)",
        "skills": ["Flutter", "Dart", "Android", "Kotlin", "Firebase", "Bloc", "REST APIs", "SQLite", "Git"],
        "job_title": "Mobile Application Developer",
        "answers": [
            {"question": "Which architecture pattern do you follow in Flutter applications?", "answer": "Clean Architecture combined with BLoC (Business Logic Component) pattern for strict state separation."},
            {"question": "Have you published applications to Google Play Store and Apple App Store?", "answer": "Yes, handled CI/CD build flavors and deployment pipelines with Fastlane."}
        ],
        "resume_text": """KARTHIK SUNDARAM
Email: karthik.sundaram.mobile@talentseed.dev | Phone: +91 98450 11027 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Mobile Application Engineer with 2 years of experience crafting smooth, cross-platform Android and iOS applications using Flutter, Dart, and native Kotlin. Specialized in state management, offline persistence, and payment flows.

TECHNICAL SKILLS
- Frameworks & Languages: Flutter, Dart, Android SDK, Kotlin
- Architecture: BLoC Pattern, Clean Architecture, Provider, Riverpod
- Storage & Backend: SQLite, Hive, Firebase Auth & Firestore, REST APIs
- Tools: Android Studio, Xcode, Fastlane, Git, Bitrise

EXPERIENCE
PhonePe | Mobile Software Engineer (Jul 2023 – Present)
- Developed and optimized merchant onboarding and KYC document upload flows across Android and iOS apps using Flutter and BLoC.
- Reduced app startup time by 28% through tree-shaking unused asset bundles and deferring non-essential module initialization.
- Implemented offline-first synchronization using SQLite/Hive with background retry queues for low-connectivity regions.
- Wrote custom platform channels in Kotlin for biometric hardware authentication (fingerprint and face unlock).

PROJECTS
- Personal Finance & Budget Tracker: Open-source Flutter app with interactive charts, encrypted local SQLite database, and biometric lock.
- Delivery Rider Navigation App: Real-time map rendering application with route polylines and battery consumption optimization.

EDUCATION
- B.Tech in Computer Science | PSG College of Technology, Coimbatore (2019 – 2023) | CGPA: 8.6/10
"""
    },
    {
        "role_category": ".NET Developer",
        "full_name": "Manish Aggarwal",
        "email": "manish.aggarwal.dotnet@talentseed.dev",
        "phone": "+91 98450 11028",
        "headline": ".NET Developer | C#, ASP.NET Core, EF Core & Cloud Microservices",
        "current_company": "Cognizant",
        "experience_years": Decimal("2.5"),
        "current_ctc_lpa": Decimal("7.50"),
        "expected_ctc_lpa": Decimal("11.00"),
        "notice_raw": "60 Days",
        "notice_days_max": 60,
        "location": "Noida, Uttar Pradesh",
        "preferred_locations": ["Noida", "Gurugram", "Chandigarh"],
        "education": "B.Tech in Computer Science, Thapar Institute of Engineering & Technology (2022)",
        "skills": ["C#", ".NET Core", "ASP.NET Core", "Entity Framework Core", "SQL Server", "REST APIs", "Azure", "Docker"],
        "job_title": ".NET Software Engineer",
        "answers": [
            {"question": "How comfortable are you with Entity Framework Core migrations and performance optimization?", "answer": "Experienced in query splitting, compiled queries, AsNoTracking(), and index tuning in SQL Server."},
            {"question": "Have you deployed .NET Core applications to Microsoft Azure?", "answer": "Yes, deployed containerized ASP.NET services to Azure App Services and Azure Container Apps."}
        ],
        "resume_text": """MANISH AGGARWAL
Email: manish.aggarwal.dotnet@talentseed.dev | Phone: +91 98450 11028 | Location: Noida, Uttar Pradesh

PROFESSIONAL SUMMARY
Results-driven .NET Software Engineer with 2.5 years of experience developing enterprise backend systems, microservices, and secure RESTful Web APIs using C#, ASP.NET Core, and Microsoft Azure.

TECHNICAL SKILLS
- Frameworks & Languages: C#, .NET 6/8, ASP.NET Core Web API, LINQ
- ORM & Databases: Entity Framework Core, Dapper, Microsoft SQL Server, PostgreSQL
- Architecture: Clean Architecture, Repository Pattern, CQRS with MediatR
- Cloud & DevOps: Azure App Services, Docker, Azure DevOps CI/CD, Git

EXPERIENCE
Cognizant | Associate Software Engineer (Nov 2022 – Present)
- Built enterprise healthcare claim adjudication REST APIs using ASP.NET Core 8 and EF Core, processing 100,000+ claims monthly.
- Refactored legacy heavy LINQ queries into raw SQL and Dapper procedures, decreasing average API response time from 620ms to 95ms.
- Implemented OAuth2 / OpenID Connect authentication using Azure Active Directory and JWT token validation.
- Containerized ASP.NET Core services using multi-stage Docker builds and automated deployments via Azure DevOps.

PROJECTS
- Inventory Management API: Modular monolith with CQRS (MediatR), FluentValidation, and SQL Server running in Docker.
- Employee Self-Service Portal Backend: Microservices architecture with RabbitMQ event bus for cross-service notifications.

EDUCATION
- B.Tech in Computer Science | Thapar Institute of Engineering & Technology (2018 – 2022) | CGPA: 8.2/10
"""
    },

    # -------------------------------------------------------------------------
    # 3. 3–5 Years Experience
    # -------------------------------------------------------------------------
    {
        "role_category": "Python Backend Developer",
        "full_name": "Vikramaditya Bose",
        "email": "vikram.bose.python@talentseed.dev",
        "phone": "+91 98450 11029",
        "headline": "Senior Python Developer | FastAPI, Distributed Systems, Kafka & Redis Caching",
        "current_company": "CRED",
        "experience_years": Decimal("4.0"),
        "current_ctc_lpa": Decimal("18.00"),
        "expected_ctc_lpa": Decimal("24.00"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Remote"],
        "education": "B.Tech in Computer Science, Jadavpur University, Kolkata (2021)",
        "skills": ["Python", "FastAPI", "Django", "PostgreSQL", "Redis", "Docker", "Kubernetes", "Kafka", "AWS", "Celery"],
        "job_title": "Senior Python Backend Developer",
        "answers": [
            {"question": "How do you structure high-throughput asynchronous services in FastAPI?", "answer": "Using asyncpg with connection pooling, dependency injection, Pydantic v2 validation, and Redis caching layers."},
            {"question": "Have you managed distributed background workloads?", "answer": "Extensively with Kafka consumers and Celery workers backed by Redis and PostgreSQL."}
        ],
        "resume_text": """VIKRAMADITYA BOSE
Email: vikram.bose.python@talentseed.dev | Phone: +91 98450 11029 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Senior Python Backend Engineer with 4 years of experience architecting resilient, low-latency microservices using Python, FastAPI, PostgreSQL, Kafka, and Redis. Passionate about concurrent programming and distributed systems.

TECHNICAL SKILLS
- Languages & Frameworks: Python 3.11+, FastAPI, Django REST Framework, SQLAlchemy 2.0, asyncpg
- Distributed Systems: Apache Kafka, Celery, Redis, RabbitMQ
- Databases: PostgreSQL, ClickHouse, Redis
- Infrastructure: Docker, Kubernetes, AWS (ECS, RDS, S3, CloudWatch), Terraform

EXPERIENCE
CRED | Software Development Engineer II (Jul 2021 – Present)
- Designed and operated core credit card reward redemption microservices in FastAPI serving 12,000 requests/sec with p99 latency < 45ms.
- Built event-driven transaction ledger using Apache Kafka with idempotency keys, guaranteeing exactly-once semantics.
- Spearheaded database partitioning and indexing strategy on PostgreSQL, reducing storage footprint and read latency by 40%.
- Conducted architecture reviews and automated CI quality gates with Black, Ruff, and MyPy.

PROJECTS
- Open-Source Async Rate Limiter: Distributed sliding-window token bucket algorithm built on Redis and async Python.
- Real-Time Fraud Detection Engine: Stream processing service using Kafka and FastAPI evaluating 10,000 transactions/min.

EDUCATION
- B.Tech in Computer Science and Engineering | Jadavpur University, Kolkata (2017 – 2021) | CGPA: 9.0/10
"""
    },
    {
        "role_category": "Full Stack Developer",
        "full_name": "Ananya Mukherjee",
        "email": "ananya.mukherjee.fullstack@talentseed.dev",
        "phone": "+91 98450 11030",
        "headline": "Full Stack Engineer | React, Node.js, TypeScript, PostgreSQL & Cloud Architecture",
        "current_company": "Razorpay",
        "experience_years": Decimal("4.5"),
        "current_ctc_lpa": Decimal("20.00"),
        "expected_ctc_lpa": Decimal("26.00"),
        "notice_raw": "15 Days",
        "notice_days_max": 15,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Mumbai", "Remote"],
        "education": "B.Tech in Information Technology, IIIT Allahabad (2020)",
        "skills": ["React", "Node.js", "TypeScript", "PostgreSQL", "GraphQL", "Docker", "AWS", "Tailwind CSS", "Microservices"],
        "job_title": "Full Stack Software Engineer",
        "answers": [
            {"question": "How do you approach end-to-end feature delivery across frontend and backend?", "answer": "I design clean contracts (OpenAPI/GraphQL), build scalable backend services, and construct responsive frontend UIs with TypeScript."},
            {"question": "Notice period flexibility?", "answer": "Serving notice currently, can join within 15 days."}
        ],
        "resume_text": """ANANYA MUKHERJEE
Email: ananya.mukherjee.fullstack@talentseed.dev | Phone: +91 98450 11030 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Dynamic Full Stack Engineer with 4.5 years of experience delivering end-to-end cloud applications. Expert in modern TypeScript, React, Node.js, GraphQL, and relational database systems in high-growth fintech environments.

TECHNICAL SKILLS
- Frontend: React.js, Next.js, TypeScript, Redux Toolkit, Tailwind CSS, Webpack
- Backend: Node.js, Express, Nest.js, GraphQL (Apollo), RESTful APIs
- Databases: PostgreSQL, MongoDB, Redis
- Cloud & Tools: AWS (S3, Lambda, CloudFront), Docker, GitHub Actions, Jest

EXPERIENCE
Razorpay | Senior Software Engineer (Oct 2020 – Present)
- Architected and built the merchant subscription billing management dashboard using React, TypeScript, and GraphQL.
- Reduced API roundtrips by 60% by introducing Apollo GraphQL federation layer over backend payment microservices.
- Led the migration of legacy frontend modules to modern Next.js architecture, improving SEO and page loading speeds.
- Collaborated cross-functionally with product managers and security auditors to ensure PCI-DSS compliance across checkout flows.

PROJECTS
- Multi-Tenant SaaS Workspace: React and Node.js portal with role-based permissions, Stripe integration, and PostgreSQL row-level security.
- Collaborative Document Editor: Real-time rich text editor using WebSockets and operational transformation (OT).

EDUCATION
- B.Tech in Information Technology | Indian Institute of Information Technology (IIIT) Allahabad (2016 – 2020) | CGPA: 8.9/10
"""
    },
    {
        "role_category": "Data Engineer",
        "full_name": "Harish Balakrishnan",
        "email": "harish.balakrishnan.de@talentseed.dev",
        "phone": "+91 98450 11031",
        "headline": "Data Engineer | PySpark, Airflow, Snowflake, AWS & Big Data Pipelines",
        "current_company": "Flipkart",
        "experience_years": Decimal("4.0"),
        "current_ctc_lpa": Decimal("19.00"),
        "expected_ctc_lpa": Decimal("25.00"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Chennai", "Hyderabad"],
        "education": "B.E. in Computer Science, College of Engineering Guindy (CEG), Anna University (2021)",
        "skills": ["Python", "PySpark", "Apache Spark", "Airflow", "SQL", "AWS S3", "Snowflake", "Kafka", "Data Modeling"],
        "job_title": "Data Engineer",
        "answers": [
            {"question": "How do you handle data skew and shuffle partitions in Apache Spark?", "answer": "Salting keys, broadcast joins for dimension tables, and tuning spark.sql.shuffle.partitions dynamically."},
            {"question": "What is your experience with Airflow orchestration?", "answer": "Authored 40+ complex DAGs with custom operators, SLAs, and Slack alerting."}
        ],
        "resume_text": """HARISH BALAKRISHNAN
Email: harish.balakrishnan.de@talentseed.dev | Phone: +91 98450 11031 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Data Engineer with 4 years of experience building petabyte-scale data lakes, batch ETL pipelines, and near real-time streaming architectures using PySpark, Apache Airflow, Snowflake, and AWS.

TECHNICAL SKILLS
- Big Data & Processing: Apache Spark, PySpark, MapReduce, Delta Lake
- Orchestration: Apache Airflow, Prefect
- Data Warehouses & Databases: Snowflake, Amazon Redshift, PostgreSQL, Hive
- Cloud & Streaming: AWS (S3, EMR, Glue), Apache Kafka, dbt

EXPERIENCE
Flipkart | Data Engineer II (Jun 2021 – Present)
- Engineered automated daily ETL pipelines in PySpark and Airflow processing 8 Terabytes of customer clickstream and order logs.
- Designed dimensional star-schema models in Snowflake, cutting business intelligence query execution times by 50%.
- Migrated legacy on-premise Hadoop clusters to AWS EMR and Delta Lake, reducing infrastructure operational costs by $120,000 annually.
- Implemented automated data quality validation checks using Great Expectations within Airflow DAGs.

PROJECTS
- Real-Time Price Tracking Lakehouse: Streaming pipeline using Kafka and Spark Structured Streaming writing to Delta Lake.
- Customer 360 Feature Store: Batch data transformation pipeline consolidating cross-channel user attributes for machine learning.

EDUCATION
- B.E. in Computer Science and Engineering | College of Engineering Guindy (CEG), Anna University (2017 – 2021) | CGPA: 8.8/10
"""
    },
    {
        "role_category": "DevOps Engineer",
        "full_name": "Meera Nambiar",
        "email": "meera.nambiar.devops@talentseed.dev",
        "phone": "+91 98450 11032",
        "headline": "DevOps Engineer | Kubernetes, Terraform, AWS, CI/CD Pipelines & Observability",
        "current_company": "Freshworks",
        "experience_years": Decimal("4.5"),
        "current_ctc_lpa": Decimal("17.50"),
        "expected_ctc_lpa": Decimal("23.00"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Chennai, Tamil Nadu",
        "preferred_locations": ["Chennai", "Bengaluru", "Remote"],
        "education": "B.Tech in Computer Science, Amrita School of Engineering (2020)",
        "skills": ["Kubernetes", "Docker", "Terraform", "AWS", "CI/CD", "GitHub Actions", "Prometheus", "Grafana", "Linux", "Bash"],
        "job_title": "DevOps Engineer",
        "answers": [
            {"question": "How do you manage Infrastructure as Code across multiple environments?", "answer": "Using modular Terraform with remote S3 backends, state locking with DynamoDB, and automated Terragrunt pipelines."},
            {"question": "What is your observability and alerting stack?", "answer": "Prometheus, Grafana, Alertmanager, and OpenTelemetry instrumentation."}
        ],
        "resume_text": """MEERA NAMBIAR
Email: meera.nambiar.devops@talentseed.dev | Phone: +91 98450 11032 | Location: Chennai, Tamil Nadu

PROFESSIONAL SUMMARY
Cloud and DevOps Engineer with 4.5 years of experience automating cloud infrastructure, orchestrating containerized microservices in Kubernetes (EKS), and architecting continuous integration/continuous deployment pipelines.

TECHNICAL SKILLS
- Containers & Orchestration: Docker, Kubernetes, Helm, Amazon EKS
- Infrastructure as Code: Terraform, Terragrunt, AWS CloudFormation
- CI/CD & Automation: GitHub Actions, Jenkins, ArgoCD (GitOps)
- Monitoring & Logging: Prometheus, Grafana, ELK Stack (Elasticsearch, Logstash, Kibana), CloudWatch

EXPERIENCE
Freshworks | Senior DevOps Engineer (Sep 2020 – Present)
- Automated provisioning of 12 multi-region AWS environments using modular Terraform, cutting environment spin-up time from 3 days to 45 minutes.
- Managed and scaled production Amazon EKS clusters running 200+ microservice pods with Karpenter auto-scaling.
- Replaced legacy Jenkins pipelines with GitHub Actions and ArgoCD GitOps, increasing daily deployment frequency by 3x.
- Implemented comprehensive Prometheus alert rules and Grafana dashboards, maintaining 99.98% platform SLA.

PROJECTS
- Zero-Downtime Blue/Green Deployment System: Automated traffic shifting controller using AWS ALB and Argo Rollouts.
- Cloud Security & Vulnerability Scanner: Automated container image security scanning in CI using Trivy and AWS ECR.

EDUCATION
- B.Tech in Computer Science | Amrita School of Engineering (2016 – 2020) | CGPA: 8.7/10
"""
    },

    # -------------------------------------------------------------------------
    # 4. 6–8 Years Experience
    # -------------------------------------------------------------------------
    {
        "role_category": "Java Backend Developer",
        "full_name": "Siddharth Sen",
        "email": "siddharth.sen.java@talentseed.dev",
        "phone": "+91 98450 11033",
        "headline": "Lead Java Developer | Spring Boot, Microservices, Kafka & High-Throughput Systems",
        "current_company": "Morgan Stanley",
        "experience_years": Decimal("6.5"),
        "current_ctc_lpa": Decimal("26.00"),
        "expected_ctc_lpa": Decimal("34.00"),
        "notice_raw": "60 Days",
        "notice_days_max": 60,
        "location": "Mumbai, Maharashtra",
        "preferred_locations": ["Mumbai", "Pune", "Bengaluru"],
        "education": "B.Tech in Computer Science, VJTI Mumbai (2018)",
        "skills": ["Java 17", "Spring Boot", "Microservices", "Hibernate", "PostgreSQL", "Kafka", "Docker", "Kubernetes", "JUnit", "AWS"],
        "job_title": "Lead Java Backend Engineer",
        "answers": [
            {"question": "How do you handle distributed transactions and consistency across Java microservices?", "answer": "Saga pattern with orchestration or choreography over Kafka, alongside outbox patterns for reliable event publishing."},
            {"question": "What is your experience with JVM performance tuning and garbage collection?", "answer": "Extensive experience tuning G1GC and ZGC flags, analyzing heap dumps with Eclipse MAT and JProfiler."}
        ],
        "resume_text": """SIDDHARTH SEN
Email: siddharth.sen.java@talentseed.dev | Phone: +91 98450 11033 | Location: Mumbai, Maharashtra

PROFESSIONAL SUMMARY
Senior Java Backend Engineer and Technical Lead with 6.5 years of experience designing robust, high-volume financial transaction processing platforms using Java 17, Spring Boot, Apache Kafka, and PostgreSQL.

TECHNICAL SKILLS
- Core & Frameworks: Java 17/21, Spring Boot, Spring Cloud, Hibernate, JPA, MapStruct
- Messaging & Streaming: Apache Kafka, RabbitMQ, JMS
- Databases: PostgreSQL, Oracle Database, Redis
- Architecture: Domain-Driven Design (DDD), Event-Driven Architecture, Microservices, REST, gRPC

EXPERIENCE
Morgan Stanley | Senior Java Developer / Tech Lead (Jul 2018 – Present)
- Led a team of 6 engineers architecting the global algorithmic trade settlement platform processing over $2 Billion in daily transaction volume.
- Redesigned message serialization from JSON to Protobuf over Kafka, increasing event throughput by 2.8x and decreasing network payload sizes by 65%.
- Tuned JVM garbage collection parameters (ZGC) and eliminated memory leaks, reducing tail latency (p99.9) from 120ms to 18ms.
- Enforced automated SonarQube quality gates and JUnit/Mockito test suites achieving 92% code coverage.

PROJECTS
- Real-Time Position Risk Engine: In-memory risk calculation engine capable of computing portfolio Greeks under extreme market volatility.
- Distributed Audit Ledger: Tamper-evident financial audit event logging service with HMAC cryptographic signatures.

EDUCATION
- B.Tech in Computer Science | Veermata Jijabai Technological Institute (VJTI), Mumbai (2014 – 2018) | CGPA: 9.1/10
"""
    },
    {
        "role_category": "Machine Learning Engineer",
        "full_name": "Pooja Chawla",
        "email": "pooja.chawla.mle@talentseed.dev",
        "phone": "+91 98450 11034",
        "headline": "Senior ML Engineer | PyTorch, MLOps, Model Deployment & Scalable ML Pipelines",
        "current_company": "InMobi",
        "experience_years": Decimal("6.0"),
        "current_ctc_lpa": Decimal("28.00"),
        "expected_ctc_lpa": Decimal("36.00"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Hyderabad", "Remote"],
        "education": "M.Tech in Data Science & Artificial Intelligence, IIT Hyderabad (2019)",
        "skills": ["Python", "PyTorch", "Scikit-Learn", "MLflow", "Kubeflow", "Docker", "FastAPI", "SQL", "Feature Engineering", "AWS SageMaker"],
        "job_title": "Senior Machine Learning Engineer",
        "answers": [
            {"question": "How do you manage model drift and automated re-training in production?", "answer": "Continuous drift monitoring using Evidently AI, automated pipeline triggers in Kubeflow, and model registry governance in MLflow."},
            {"question": "Have you deployed deep learning models at scale?", "answer": "Yes, deployed PyTorch models using Triton Inference Server and FastAPI on AWS EKS."}
        ],
        "resume_text": """POOJA CHAWLA
Email: pooja.chawla.mle@talentseed.dev | Phone: +91 98450 11034 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Senior Machine Learning Engineer with 6 years of experience building and operationalizing end-to-end predictive systems, recommendation algorithms, and MLOps infrastructure serving millions of daily inferences.

TECHNICAL SKILLS
- ML Frameworks: PyTorch, Scikit-Learn, XGBoost, LightGBM, HuggingFace
- MLOps & Tooling: MLflow, Kubeflow, Feast (Feature Store), DVC, Docker, Triton Inference Server
- Cloud & Platforms: AWS SageMaker, EKS, Databricks, BigQuery
- Languages: Python, SQL, C++ basics

EXPERIENCE
InMobi | Senior ML Engineer (Aug 2019 – Present)
- Engineered real-time mobile ad click-through rate (CTR) prediction models handling 80,000 queries/sec with response times < 20ms.
- Built automated continuous training and validation pipelines in Kubeflow and MLflow, saving 15 hours of manual experimentation weekly.
- Implemented Feast feature store on Redis and PostgreSQL, ensuring zero training-serving skew across offline and online features.
- Reduced model inference memory footprint by 50% through FP16 quantization and ONNX runtime optimization.

PROJECTS
- Contextual Recommendation Engine: Multi-armed bandit recommendation system for personalized mobile in-app experiences.
- Image Fraud Detection Pipeline: Deep learning CNN classifier screening user-submitted advertisement creatives.

EDUCATION
- M.Tech in Data Science & AI | Indian Institute of Technology (IIT) Hyderabad (2017 – 2019) | CGPA: 9.3/10
- B.Tech in Computer Science | Punjab Engineering College (PEC), Chandigarh (2013 – 2017) | CGPA: 8.8/10
"""
    },
    {
        "role_category": "Cloud Engineer",
        "full_name": "Gaurav Mehta",
        "email": "gaurav.mehta.cloud@talentseed.dev",
        "phone": "+91 98450 11035",
        "headline": "Senior Cloud Engineer | Multi-Cloud (AWS/Azure), Terraform, Cloud Security & FinOps",
        "current_company": "Cisco Systems",
        "experience_years": Decimal("7.0"),
        "current_ctc_lpa": Decimal("27.00"),
        "expected_ctc_lpa": Decimal("35.00"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Pune", "Remote"],
        "education": "B.E. in Information Technology, Manipal Institute of Technology (2018)",
        "skills": ["AWS", "Azure", "Terraform", "CloudFormation", "Python", "Networking (VPC)", "IAM", "Security", "Docker", "Cost Optimization"],
        "job_title": "Senior Cloud Infrastructure Engineer",
        "answers": [
            {"question": "What is your approach to cloud cost governance and FinOps?", "answer": "Automated resource tagging policies, rightsizing underutilized EC2/RDS instances, Savings Plans, and automated off-hours shutdowns."},
            {"question": "How do you enforce security controls across multi-account AWS organizations?", "answer": "AWS Control Tower, Service Control Policies (SCPs), GuardDuty, and automated compliance auditing with AWS Config."}
        ],
        "resume_text": """GAURAV MEETA
Email: gaurav.mehta.cloud@talentseed.dev | Phone: +91 98450 11035 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Senior Cloud Solutions Engineer with 7 years of deep expertise in multi-cloud architecture (AWS and Microsoft Azure), automated cloud governance, infrastructure as code, and cloud financial operations (FinOps).

TECHNICAL SKILLS
- Cloud Providers: Amazon Web Services (AWS - 5x Certified), Microsoft Azure
- IaC & Automation: Terraform, Terragrunt, AWS CDK, Python (Boto3), Ansible
- Networking & Security: AWS Direct Connect, Transit Gateway, VPC Peering, IAM, KMS, Security Hub
- Observability & Governance: AWS CloudWatch, CloudTrail, Datadog, AWS Config

EXPERIENCE
Cisco Systems | Senior Cloud Engineer (Jun 2018 – Present)
- Designed and migrated enterprise hybrid-cloud networking utilizing AWS Transit Gateway and Direct Connect across 14 enterprise data centers.
- Spearheaded company-wide AWS FinOps initiative, identifying idle assets and optimizing compute instances to achieve $450,000 annual recurring savings.
- Formulated zero-trust IAM privilege boundaries and centralized role management across 85+ AWS accounts using AWS IAM Identity Center.
- Built automated disaster recovery failover workflows across primary (Mumbai) and secondary (Hyderabad) AWS regions.

PROJECTS
- Automated Multi-Account Vending Machine: Self-service portal provisioning compliant AWS sandboxes with predefined Terraform guardrails.
- Enterprise Cloud Migration: Lift-and-shift followed by re-platforming of 60+ on-premise Linux/Windows services to AWS.

EDUCATION
- B.E. in Information Technology | Manipal Institute of Technology (MIT Manipal) (2014 – 2018) | CGPA: 8.6/10
- Certifications: AWS Certified Solutions Architect - Professional, AWS Certified DevOps Engineer - Professional
"""
    },
    {
        "role_category": "Cybersecurity Engineer",
        "full_name": "Neha Singhal",
        "email": "neha.singhal.sec@talentseed.dev",
        "phone": "+91 98450 11036",
        "headline": "Lead Cybersecurity Engineer | DevSecOps, AppSec, Threat Modeling & Cloud Defense",
        "current_company": "PayU India",
        "experience_years": Decimal("7.5"),
        "current_ctc_lpa": Decimal("29.00"),
        "expected_ctc_lpa": Decimal("38.00"),
        "notice_raw": "60 Days",
        "notice_days_max": 60,
        "location": "Gurugram, Haryana",
        "preferred_locations": ["Gurugram", "Noida", "Delhi NCR", "Remote"],
        "education": "B.Tech in Computer Science, NSUT (Netaji Subhas University of Technology) (2017)",
        "skills": ["Application Security", "Penetration Testing", "OWASP Top 10", "DevSecOps", "SIEM", "Splunk", "Python", "Cloud Security", "ISO 27001"],
        "job_title": "Lead Cybersecurity Engineer",
        "answers": [
            {"question": "How do you integrate automated security checks into fast-paced CI/CD pipelines?", "answer": "Integrating SAST (SonarQube/Semgrep), DAST (OWASP ZAP), and SCA (Snyk/Trivy) into PR gates with automated vulnerability triaging."},
            {"question": "What is your experience with regulatory audits like PCI-DSS and SOC 2?", "answer": "Led technical remediation for PCI-DSS v4.0 and SOC 2 Type II compliance audits across fintech infrastructure."}
        ],
        "resume_text": """NEHA SINGHAL
Email: neha.singhal.sec@talentseed.dev | Phone: +91 98450 11036 | Location: Gurugram, Haryana

PROFESSIONAL SUMMARY
Lead Information Security Engineer with 7.5 years of experience securing cloud-native payments infrastructure. Specialized in application security (AppSec), DevSecOps CI/CD integration, threat modeling, and incident response.

TECHNICAL SKILLS
- Security Disciplines: Application Security (SAST, DAST, SCA), Threat Modeling (STRIDE), Penetration Testing
- Tools: Burp Suite Professional, Snyk, Semgrep, SonarQube, OWASP ZAP, Metasploit, Splunk, Wiz
- Compliance & Standards: OWASP Top 10, PCI-DSS, ISO 27001, SOC 2 Type II, RBI Cyber Security Framework
- Scripting & Automation: Python, Bash, Go

EXPERIENCE
PayU India | Lead Security Engineer (Jul 2017 – Present)
- Formulated the organization-wide DevSecOps program, embedding Semgrep and Snyk scans into 120+ microservice repositories.
- Discovered and resolved 18 high-severity vulnerabilities including SSRF and IDOR vulnerabilities prior to production release.
- Led technical remediation and architecture audits for PCI-DSS v4.0 compliance across payments transaction gateways.
- Conducted hands-on secure code training sessions for 150+ software engineers across backend and mobile teams.

PROJECTS
- Automated Threat Modeling Tool: Python-based CLI tool generating architecture threat vectors directly from Terraform code.
- Cloud Security Posture Management: Continuous AWS misconfiguration auditing and automated remediation lambda bots.

EDUCATION
- B.Tech in Computer Science | Netaji Subhas University of Technology (NSUT), New Delhi (2013 – 2017) | CGPA: 8.9/10
- Certifications: Certified Information Systems Security Professional (CISSP), Certified Ethical Hacker (CEH)
"""
    },

    # -------------------------------------------------------------------------
    # 5. 8+ Years Experience
    # -------------------------------------------------------------------------
    {
        "role_category": "AI Engineer",
        "full_name": "Dr. Arindam Ghosh",
        "email": "arindam.ghosh.ai@talentseed.dev",
        "phone": "+91 98450 11037",
        "headline": "Staff AI Engineer | Deep Learning, NLP, Computer Vision & Distributed Inference",
        "current_company": "Adobe Systems",
        "experience_years": Decimal("8.5"),
        "current_ctc_lpa": Decimal("38.00"),
        "expected_ctc_lpa": Decimal("48.00"),
        "notice_raw": "30 Days",
        "notice_days_max": 30,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Noida", "Remote"],
        "education": "Ph.D. in Computer Science (AI/ML), IIT Kharagpur (2019); B.Tech (2015)",
        "skills": ["Python", "PyTorch", "TensorFlow", "Deep Learning", "Computer Vision", "NLP", "CUDA", "FastAPI", "ONNX", "Docker"],
        "job_title": "Staff AI Research Engineer",
        "answers": [
            {"question": "What is your experience optimizing neural network inference on GPUs?", "answer": "Profiling with NVIDIA Nsight, TensorRT conversion, kernel fusion, and FP16/INT8 post-training quantization."},
            {"question": "Have you published research papers in peer-reviewed conferences?", "answer": "Yes, author of 6 papers in IEEE, CVPR workshops, and NeurIPS workshops."}
        ],
        "resume_text": """DR. ARINDAM GHOSH
Email: arindam.ghosh.ai@talentseed.dev | Phone: +91 98450 11037 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Staff Artificial Intelligence Engineer and Researcher with 8.5 years of industry and academic experience pushing the state-of-the-art in Computer Vision, Natural Language Processing, and high-performance GPU model inference.

TECHNICAL SKILLS
- Deep Learning: PyTorch, TensorFlow, JAX, HuggingFace Transformers, OpenCV, CUDA
- Model Optimization: TensorRT, ONNX Runtime, OpenVINO, Pruning, Quantization
- Serving & Infra: Triton Inference Server, vLLM, Ray Serve, Docker, Kubernetes
- Languages: Python, C++, CUDA C

EXPERIENCE
Adobe Systems | Staff AI Engineer (Jul 2019 – Present)
- Spearheaded the development of proprietary diffusion-based image segmentation and enhancement models powering Creative Cloud features.
- Optimized multi-modal vision-language transformers using NVIDIA TensorRT, achieving 4.2x speedup in real-time inference latency.
- Mentored a research group of 8 applied scientists and research engineers, filing 4 patent applications.
- Built distributed model training infrastructure across clusters of 64 NVIDIA H100 GPUs using PyTorch FSDP and DeepSpeed.

PUBLICATIONS & PATENTS
- 6 peer-reviewed papers published in IEEE Transactions, CVPR Workshops, and Pattern Recognition.
- 4 US Patents granted in deep image synthesis and document understanding.

EDUCATION
- Ph.D. in Computer Science (Artificial Intelligence) | Indian Institute of Technology (IIT) Kharagpur (2015 – 2019)
- B.Tech in Computer Science | Indian Institute of Technology (IIT) Kharagpur (2011 – 2015)
"""
    },
    {
        "role_category": "GenAI / LLM Engineer",
        "full_name": "Preeti Chadha",
        "email": "preeti.chadha.genai@talentseed.dev",
        "phone": "+91 98450 11038",
        "headline": "Principal GenAI Engineer | LLMs, Agentic Workflows, Multi-modal RAG & Vector Search",
        "current_company": "Microsoft India",
        "experience_years": Decimal("9.0"),
        "current_ctc_lpa": Decimal("42.00"),
        "expected_ctc_lpa": Decimal("52.00"),
        "notice_raw": "15 Days",
        "notice_days_max": 15,
        "location": "Hyderabad, Telangana",
        "preferred_locations": ["Hyderabad", "Bengaluru", "Remote"],
        "education": "M.Tech in Computer Science, IIIT Hyderabad (2016)",
        "skills": ["LangChain", "LlamaIndex", "RAG Architecture", "OpenAI / Claude APIs", "Vector Databases", "vLLM", "HuggingFace", "Python", "FastAPI", "Docker"],
        "job_title": "Principal Generative AI Engineer",
        "answers": [
            {"question": "How do you evaluate and benchmark RAG pipelines against hallucinations?", "answer": "Using Ragas and TruLens frameworks measuring context relevancy, faithfullness, and answer relevancy."},
            {"question": "What is your approach to autonomous agent tool calling and error recovery?", "answer": "Deterministic state machines with LangGraph, strict JSON schema validation, exponential retry, and human-in-the-loop fallback."}
        ],
        "resume_text": """PREETI CHADHA
Email: preeti.chadha.genai@talentseed.dev | Phone: +91 98450 11038 | Location: Hyderabad, Telangana

PROFESSIONAL SUMMARY
Principal Generative AI Engineer with 9 years of overall software experience and 3+ years dedicated to Large Language Models (LLMs), Agentic workflows, Multi-modal Retrieval-Augmented Generation (RAG), and vector databases.

TECHNICAL SKILLS
- GenAI & LLM Tools: LangChain, LlamaIndex, LangGraph, Guidance, Semantic Kernel, DSPy
- Model Inference & Serving: vLLM, Ollama, HuggingFace TGI, OpenAI / Anthropic APIs
- Vector Databases: Pinecone, Milvus, Qdrant, pgvector, ChromaDB
- Backend & Systems: Python, FastAPI, Docker, Kubernetes, Azure OpenAI Service

EXPERIENCE
Microsoft India | Principal AI Solutions Architect (Sep 2016 – Present)
- Architected enterprise Copilot agents leveraging Azure OpenAI and LangGraph for automated enterprise contract analysis.
- Designed advanced multi-stage RAG pipeline utilizing hybrid search (dense embeddings + sparse BM25) and cross-encoder re-ranking.
- Reduced hallucinations across customer-facing knowledge bots by 78% through fine-tuned prompt engineering and strict grounding checks.
- Scaled open-weight LLM deployment (Llama 3 70B, Mistral Large) using vLLM on multi-GPU Azure instances, lowering token cost by 60%.

PROJECTS
- Multi-Agent Code Reviewer: Autonomous agent team that inspects PRs for security vulnerabilities, style conformity, and test coverage.
- Medical Literature Question-Answering System: High-precision biomedical RAG tool backed by Milvus and PubMed embeddings.

EDUCATION
- M.Tech in Computer Science | International Institute of Information Technology (IIIT) Hyderabad (2014 – 2016) | CGPA: 9.2/10
- B.Tech in Computer Science | Osmania University College of Engineering (2010 – 2014) | CGPA: 8.7/10
"""
    },
    {
        "role_category": "Database Engineer",
        "full_name": "Suresh Soundararajan",
        "email": "suresh.soundararajan.db@talentseed.dev",
        "phone": "+91 98450 11039",
        "headline": "Lead Database Engineer | PostgreSQL Internals, Performance Optimization & HA Clustering",
        "current_company": "Oracle India",
        "experience_years": Decimal("10.0"),
        "current_ctc_lpa": Decimal("36.00"),
        "expected_ctc_lpa": Decimal("45.00"),
        "notice_raw": "60 Days",
        "notice_days_max": 60,
        "location": "Bengaluru, Karnataka",
        "preferred_locations": ["Bengaluru", "Chennai"],
        "education": "B.E. in Electronics & Communication, NITK Surathkal (2015)",
        "skills": ["PostgreSQL", "Oracle DB", "MySQL", "Performance Tuning", "Query Optimization", "High Availability", "Replication", "PgBouncer", "Linux", "Python"],
        "job_title": "Lead Database Reliability Engineer",
        "answers": [
            {"question": "How do you diagnose vacuum bloat and transaction ID wraparound in PostgreSQL?", "answer": "Monitoring autovacuum workers, vacuum freeze settings, pg_stat_user_tables dead tuples, and pg_class relfrozenxid."},
            {"question": "What high-availability replication topologies have you built?", "answer": "Patroni with etcd for automated leader failover, streaming physical replication with read replicas, and PgBouncer connection pooling."}
        ],
        "resume_text": """SURESH SOUNDARARAJAN
Email: suresh.soundararajan.db@talentseed.dev | Phone: +91 98450 11039 | Location: Bengaluru, Karnataka

PROFESSIONAL SUMMARY
Lead Database Administrator and Database Reliability Engineer with 10 years of experience managing mission-critical enterprise database clusters. Deep expertise in PostgreSQL internals, query planner optimization, and high availability architectures.

TECHNICAL SKILLS
- Relational Databases: PostgreSQL (v11-v16), Oracle Database 19c, MySQL, MariaDB
- HA & Clustering: Patroni, etcd, Streaming Replication, Oracle Data Guard, PgBouncer
- Performance & Tuning: pg_stat_statements, EXPLAIN ANALYZE, Index Tuning (B-Tree, GIN, BRIN), Partitioning
- Operating Systems & Tools: Linux (RHEL, Ubuntu), Bash scripting, Python, Ansible

EXPERIENCE
Oracle India | Lead Database Engineer (Jul 2015 – Present)
- Managed 140+ production PostgreSQL and Oracle database instances supporting 99.999% uptime for cloud telecom services.
- Spearheaded PostgreSQL major version upgrades across 40 TB databases with less than 2 minutes of planned downtime using pg_upgrade.
- Configured Patroni and etcd automated failover clusters, achieving zero data loss (RPO = 0) and under 15-second failovers (RTO < 15s).
- Optimized query execution plans for top 50 slowest queries, slashing average server CPU load from 82% to 34%.

PROJECTS
- Automated Database Provisioning Platform: Ansible playbooks that spin up hardened, benchmarked PostgreSQL HA clusters in minutes.
- Real-Time Query Performance Monitor: Custom telemetry agent feeding lock contention and buffer cache metrics into Grafana.

EDUCATION
- B.E. in Electronics and Communication | National Institute of Technology Karnataka (NITK), Surathkal (2011 – 2015) | CGPA: 8.5/10
"""
    },
    {
        "role_category": "Solution/Software Architect",
        "full_name": "Deepak Varma",
        "email": "deepak.varma.architect@talentseed.dev",
        "phone": "+91 98450 11040",
        "headline": "Principal Solution Architect | Distributed Systems, Cloud-Native Scalability & High-Resilience Platforms",
        "current_company": "Amazon Web Services (AWS)",
        "experience_years": Decimal("13.5"),
        "current_ctc_lpa": Decimal("58.00"),
        "expected_ctc_lpa": Decimal("70.00"),
        "notice_raw": "60 Days",
        "notice_days_max": 60,
        "location": "Hyderabad, Telangana",
        "preferred_locations": ["Hyderabad", "Bengaluru", "Remote"],
        "education": "B.Tech in Computer Science, IIT Madras (2011)",
        "skills": ["Enterprise Architecture", "Cloud Solution Design", "Distributed Systems", "AWS", "Microservices", "System Design", "Kafka", "Kubernetes", "DevSecOps"],
        "job_title": "Principal Solution Architect",
        "answers": [
            {"question": "How do you evaluate architectural trade-offs between consistency and availability?", "answer": "CAP theorem analysis, choosing eventual consistency with distributed sagas for non-critical paths, and strong consistency with distributed consensus for financial ledgers."},
            {"question": "What is your experience mentoring senior engineering staff and driving technical roadmaps?", "answer": "Over 7 years leading Architecture Review Boards, authoring RFCs, and mentoring Principal and Staff engineers."}
        ],
        "resume_text": """DEEPAK VARMA
Email: deepak.varma.architect@talentseed.dev | Phone: +91 98450 11040 | Location: Hyderabad, Telangana

PROFESSIONAL SUMMARY
Principal Solution and Enterprise Architect with 13.5 years of industry experience guiding the architecture of large-scale distributed systems, multi-region cloud infrastructures, and high-concurrency microservices platforms.

TECHNICAL SKILLS
- Architectural Patterns: Microservices, Event-Driven Architecture, CQRS, Hexagonal Architecture, Serverless
- Technologies: AWS, Kubernetes, Apache Kafka, PostgreSQL, Redis, Docker, Terraform
- Methodologies: TOGAF, Domain-Driven Design (DDD), Reliability Engineering, Threat Modeling
- Leadership: Technical Strategy, Architecture Review Boards (ARB), RFC Governance, Executive Advisory

EXPERIENCE
Amazon Web Services (AWS) | Principal Solution Architect (Aug 2011 – Present)
- Advised Tier-1 enterprise fintech and banking customers across APAC on designing fault-tolerant, multi-region cloud platforms on AWS.
- Led the architectural migration of legacy core banking monoliths into decoupled microservice fabrics serving 100M+ retail customers.
- Established enterprise architecture governance frameworks, authoring 35+ Architecture Decision Records (ADRs).
- Designed disaster-recovery architectures achieving active-active multi-region resiliency with zero data loss.

PUBLICATIONS & SPEAKING
- Keynote speaker at AWS Summit and international enterprise architecture conferences.
- Published author of whitepapers on resilient cloud banking patterns and event-driven architectures.

EDUCATION
- B.Tech in Computer Science and Engineering | Indian Institute of Technology (IIT) Madras (2007 – 2011) | CGPA: 9.4/10
- Certifications: AWS Certified Solutions Architect - Professional, TOGAF 9.2 Certified
"""
    }
]


async def seed_candidates():
    print("=" * 70)
    print("Starting candidate seed...")
    print("=" * 70)

    settings = get_settings()
    engine = create_async_engine(settings.async_database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    target_emails = [c["email"] for c in CANDIDATE_DATA]
    total_to_create = len(CANDIDATE_DATA)

    async with session_factory() as db:
        # Check existing matching candidates
        q_existing = select(Candidate.email).where(Candidate.email.in_(target_emails))
        existing_emails = set((await db.execute(q_existing)).scalars().all())

        existing_count = len(existing_emails)
        print(f"\nExisting matching candidates in DB: {existing_count}")
        print(f"Candidates to process: {total_to_create}\n")

        created_count = 0
        skipped_count = 0
        failed_count = 0

        for idx, data in enumerate(CANDIDATE_DATA, 1):
            email = data["email"]
            name = data["full_name"]
            role = data["role_category"]

            if email in existing_emails:
                print(f"[{idx}/{total_to_create}] SKIPPED: {name} ({role}) - Email already exists: {email}")
                skipped_count += 1
                continue

            try:
                now = datetime.now(timezone.utc)
                candidate_id = uuid.uuid4()
                mail_id = uuid.uuid4()

                # 1. Create linked Mail record
                subject = f"Application for {role} - {name}"
                mail = Mail(
                    id=mail_id,
                    tenant_id=None,
                    message_id=f"seed-msg-{email}",
                    received_at=now,
                    sender=email,
                    subject=subject,
                    source="seed_talent_pool",
                    raw_headers={"From": f"{name} <{email}>", "To": "careers@talentpool.io"},
                    raw_body_text=f"Candidate Application for {role}.\nName: {name}\nExperience: {data['experience_years']} years\nNotice: {data['notice_raw']}",
                    raw_body_html=f"<html><body><h2>Application for {role}</h2><p>Candidate: {name}</p><p>Experience: {data['experience_years']} years</p></body></html>",
                    status="parsed",
                    created_at=now,
                )
                db.add(mail)

                # 2. Create Candidate record
                candidate = Candidate(
                    id=candidate_id,
                    tenant_id=None,
                    full_name=name,
                    email=email,
                    phone=data["phone"],
                    headline=data["headline"],
                    current_company=data["current_company"],
                    experience_years=data["experience_years"],
                    current_ctc_lpa=data["current_ctc_lpa"],
                    notice_raw=data["notice_raw"],
                    notice_days_max=data["notice_days_max"],
                    location=data["location"],
                    preferred_locations=data["preferred_locations"],
                    education=data["education"],
                    skills=data["skills"],
                    first_seen_at=now,
                    last_seen_at=now,
                    merged_into=None,
                    created_at=now,
                )
                db.add(candidate)

                # 3. Create linked Application record
                application = Application(
                    id=uuid.uuid4(),
                    tenant_id=None,
                    candidate_id=candidate_id,
                    mail_id=mail_id,
                    job_title=data["job_title"],
                    job_locations=data["preferred_locations"],
                    expected_ctc_lpa=data["expected_ctc_lpa"],
                    answers=data["answers"],
                    received_at=now,
                    created_at=now,
                )
                db.add(application)

                # 4. Create linked Resume record
                resume_text = data["resume_text"].strip()
                resume_bytes = resume_text.encode("utf-8")
                resume_hash = hashlib.sha256(resume_bytes).hexdigest()

                resume = Resume(
                    id=uuid.uuid4(),
                    tenant_id=None,
                    candidate_id=candidate_id,
                    mail_id=mail_id,
                    file_name=f"{name.replace(' ', '_')}_Resume.pdf",
                    file_hash=resume_hash,
                    file_size_bytes=len(resume_bytes),
                    file_content_bytes=resume_bytes,
                    text_content=resume_text,
                    text_quality="ok",
                    created_at=now,
                )
                db.add(resume)

                # Commit transaction per candidate for clean transactional safety
                await db.commit()
                created_count += 1
                print(f"[{idx}/{total_to_create}] Created {name:<22} | {role:<28} | Exp: {data['experience_years']}y | Notice: {data['notice_raw']:<9} | {email}")

            except Exception as e:
                await db.rollback()
                failed_count += 1
                print(f"[{idx}/{total_to_create}] FAILED {name}: {e}")

        await engine.dispose()

        print("\n" + "=" * 70)
        print("Seed completed successfully.")
        print("=" * 70)
        print(f"Total created: {created_count}")
        print(f"Total skipped: {skipped_count}")
        print(f"Total failed:  {failed_count}")
        print("=" * 70)

        return {
            "created": created_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "total": total_to_create,
        }


if __name__ == "__main__":
    asyncio.run(seed_candidates())
