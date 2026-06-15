# JournalJourney

## Overview

JournalJourney is an AI-assisted digital journaling platform developed using Flask and Natural Language Processing (NLP). The application provides secure user authentication, intelligent sentiment analysis, automatic diary categorization, mood-trend visualization, AI-generated weekly insights, and persistent personal journal management through a SQLite database.

The project combines full-stack web development with NLP and Large Language Model (LLM) techniques to create a personalized journaling experience where users can record, organize, visualize, and reflect on their daily thoughts.

---

## Features

* Secure user registration and login
* Password hashing using Bcrypt
* Session-based authentication
* Personal diary entry management
* Automatic sentiment analysis with a numeric VADER compound score
* Automatic diary categorization
* Mood dashboard with an interactive Chart.js sentiment trend (7-day and 30-day views)
* AI-generated weekly insights powered by Google Gemini
* Cached insights (regenerated weekly) with a manual "Refresh now" option
* Search through previous entries
* Delete existing entries
* User-specific private journals
* Persistent SQLite database storage

---

## Technology Stack

### Programming Language

* Python 3

### Backend

* Flask
* Flask-WTF
* Flask-SQLAlchemy
* Flask-Bcrypt

### Frontend

* HTML5
* CSS3
* Jinja2 Template Engine
* Chart.js (sentiment trend visualization)

### Artificial Intelligence

* Google Gemini API (`gemini-2.5-flash`)
* `google-genai` Python SDK
* Cached, prompt-engineered weekly reflections

### Configuration & Secrets

* python-dotenv (`.env` based configuration)
* truststore (OS certificate store trust for HTTPS behind corporate proxies)

### Database

* SQLite
* SQLAlchemy ORM

### Authentication & Security

* Flask Sessions
* Bcrypt Password Hashing
* CSRF Protection

### Natural Language Processing

* NLTK (Natural Language Toolkit)
* VADER Sentiment Analyzer
* Tokenization
* Stopword Removal
* Lemmatization
* Keyword-Based Category Prediction

### Development Environment

* Visual Studio Code
* Python Virtual Environment (venv)
* Git & GitHub

---

## Core Concepts Implemented

* Full-Stack Web Development
* User Authentication & Authorization
* Password Hashing
* Session Management
* ORM (Object Relational Mapping)
* CRUD Operations
* Natural Language Processing
* Sentiment Analysis
* Text Preprocessing
* Data Visualization
* LLM Prompt Engineering & API Integration
* Response Caching
* Database Relationships
* Search Functionality
* Secure Form Handling

---

## Project Structure

```text
JournalJourney/
│
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── .env                  # holds GEMINI_API_KEY (not committed)
│
├── instance/
│   └── site.db
│
├── static/
│   ├── styles1.css
│   ├── styles2.css
│   └── styles3.css
│
└── templates/
    ├── index.html
    ├── entries.html
    ├── dashboard.html
    ├── insights.html
    ├── login.html
    └── signup.html
```

---

## System Architecture

```text
                    User
                      │
                      ▼
            Flask Web Application
                      │
   ┌────────────┬─────┴──────┬────────────────┐
   │            │            │                │
   ▼            ▼            ▼                ▼
Auth        NLP          Insights         Dashboard
Module      Module       Module           Module
   │            │            │                │
   ├─ Sessions  ├─ Tokenize  ├─ Gemini API    ├─ Sentiment
   ├─ Bcrypt    ├─ Stopwords ├─ Prompt build  │   aggregation
   └─ CSRF      ├─ Lemmatize ├─ Weekly cache  └─ Chart.js
                ├─ Category  └─ (google-genai)     trend data
                └─ Sentiment
                   (+ score)
                      │
                      ▼
           SQLite Database
           (SQLAlchemy ORM)
```

---

## Workflow

1. User creates an account.
2. Password is securely hashed before storage.
3. User logs into the application.
4. A diary entry is submitted.
5. The text undergoes NLP preprocessing:

   * Tokenization
   * Stopword Removal
   * Lemmatization
6. The entry is categorized based on predefined keyword mappings.
7. VADER Sentiment Analysis determines whether the text is Positive, Negative, or Neutral, and stores the numeric compound score (-1.0 to +1.0).
8. The processed entry is stored in the SQLite database.
9. Users can later search, view, or delete their own entries.
10. The mood dashboard aggregates per-day sentiment scores and renders an interactive Chart.js trend (7-day and 30-day views).
11. The AI Insights page sends the last 7 entries to Google Gemini, which returns a three-paragraph personal reflection. The result is cached for a week and can be regenerated on demand.

---

## Categories Supported

* Work
* Health
* Relationships
* Personal Development
* Hobbies

---

## Database Schema

### User

| Field    | Type          |
| -------- | ------------- |
| id       | Integer       |
| username | String        |
| password | Hashed String |

### DiaryEntry

| Field           | Type        |
| --------------- | ----------- |
| id              | Integer     |
| text            | Text        |
| category        | String      |
| sentiment       | String      |
| sentiment_score | Float       |
| timestamp       | DateTime    |
| user_id         | Foreign Key |

### WeeklyInsight

| Field         | Type        |
| ------------- | ----------- |
| id            | Integer     |
| insight_text  | Text        |
| generated_on  | DateTime    |
| user_id       | Foreign Key |

---

## Application Routes

| Route               | Method   | Description                                            |
| ------------------- | -------- | ------------------------------------------------------ |
| `/signup`           | GET/POST | Create a new account                                   |
| `/login`            | GET/POST | Authenticate an existing user                          |
| `/logout`           | GET      | End the session                                        |
| `/`                 | GET/POST | Write a new diary entry                                |
| `/entries`          | GET      | View, search, and manage entries                       |
| `/delete_entry/<id>`| POST     | Delete one of the user's entries                       |
| `/dashboard`        | GET      | Mood trend dashboard (Chart.js)                        |
| `/insights`         | GET      | AI weekly insight (cached for 7 days)                  |
| `/insights/refresh` | POST     | Force-regenerate the AI insight                        |

All routes except `/signup` and `/login` require an active session.

---

## Installation

### Clone the repository

```bash
git clone <repository-url>
cd JournalJourney
```

### Create a virtual environment

```bash
python -m venv .venv
```

### Activate the environment

**Windows**

```bash
.venv\Scripts\activate
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file in the project root and add your Google Gemini API key
(get a free key at [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)):

```text
GEMINI_API_KEY=your_key_here
```

The `.env` file is listed in `.gitignore`, so your key is never committed.
If the key is missing, the app still runs — the AI Insights page simply shows
a message explaining the feature is unavailable.

### Run the application

```bash
python main.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

---

## Python Libraries Used

* Flask
* Flask-WTF
* Flask-SQLAlchemy
* Flask-Bcrypt
* WTForms
* SQLAlchemy
* NLTK
* bcrypt
* google-genai
* python-dotenv
* truststore

---

## Future Enhancements

* Machine Learning based category prediction
* Voice-to-text journaling
* Journal export functionality
* Cloud database integration
* Dark mode interface
* Configurable insight cadence (daily / weekly / monthly)
* Email or push notifications for new insights

---

## Academic Purpose

This project was developed to explore the integration of Natural Language Processing techniques with full-stack web development for building intelligent and interactive applications.

---

## Author

**Arundhati Chaudhuri**

Bachelor of Technology (Computer Science Engineering)

KIIT University
