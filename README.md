# JournalJourney

## Overview

JournalJourney is an AI-assisted digital journaling platform developed using Flask and Natural Language Processing (NLP). The application provides secure user authentication, intelligent sentiment analysis, automatic diary categorization, and persistent personal journal management through a SQLite database.

The project combines full-stack web development with NLP techniques to create a personalized journaling experience where users can record, organize, and analyze their daily thoughts.

---

## Features

* Secure user registration and login
* Password hashing using Bcrypt
* Session-based authentication
* Personal diary entry management
* Automatic sentiment analysis
* Automatic diary categorization
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
        ┌─────────────┼─────────────┐
        │                           │
        ▼                           ▼
Authentication Module       NLP Processing Module
        │                           │
        ├── Flask Sessions          ├── Tokenization
        ├── Bcrypt                  ├── Stopword Removal
        └── CSRF Protection         ├── Lemmatization
                                    ├── Category Prediction
                                    └── Sentiment Analysis
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
7. VADER Sentiment Analysis determines whether the text is Positive, Negative, or Neutral.
8. The processed entry is stored in the SQLite database.
9. Users can later search, view, or delete their own entries.

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

| Field     | Type        |
| --------- | ----------- |
| id        | Integer     |
| text      | Text        |
| category  | String      |
| sentiment | String      |
| timestamp | DateTime    |
| user_id   | Foreign Key |

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

---

## Future Enhancements

* Machine Learning based category prediction
* Mood trend visualization
* AI-generated journaling insights
* Voice-to-text journaling
* Journal export functionality
* Cloud database integration
* Dark mode interface

---

## Academic Purpose

This project was developed to explore the integration of Natural Language Processing techniques with full-stack web development for building intelligent and interactive applications.

---

## Author

**Arundhati Chaudhuri**

Bachelor of Technology (Computer Science Engineering)

KIIT University
