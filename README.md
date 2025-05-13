# HCPLogger Backend

## Overview

This is the backend service for the HCPLogger application, an intelligent system designed to assist Healthcare Professionals (HCPs). It processes conversational input, leverages LangGraph and the Groq API to extract key information from HCP interactions, and provides APIs for the frontend to auto-populate forms and log these interactions. The system uses an asynchronous architecture built with Python and FastAPI, with data persistence handled by SQLAlchemy, supporting both PostgreSQL and SQLite.

## Key Features

* **FastAPI Framework:** High-performance asynchronous API built with Python.
* **LangGraph Integration:** Utilizes LangGraph for sophisticated information extraction from conversational text about HCP interactions.
* **Groq API Powered:** Connects to the Groq API for underlying Large Language Model capabilities.
* **Automated Interaction Logging:** Core logic to process and prepare data for logging HCP interactions.
* **Asynchronous Database Operations:** Uses SQLAlchemy's async capabilities for efficient database interactions.
* **Database Flexibility:** Supports PostgreSQL and SQLite.
* **Pydantic Type Validation:** Ensures robust data validation for API requests/responses and configuration.
* **Environment-based Configuration:** Manages settings (database URLs, API keys) using `.env` files and Pydantic-settings.
* **Structured Project:** Organized into modules for clarity (e.g., `database.py`, `models.py`, `crud.py`, `agent.py`, `main.py`).

## 🛠️ Tech Stack

* **Language:** Python 
* **Framework:** FastAPI
* **AI/NLP:** LangGraph, Groq API client
* **ORM:** SQLAlchemy (with async support)
* **Database Drivers:** `aiosqlite` (for SQLite)
* **Configuration:** Pydantic-settings, `python-dotenv`
* **API Documentation:** Automatic generation via FastAPI (Swagger UI at `/docs`, ReDoc at `/redoc`)
* **Dependency Management:** `pip with requirements.txt`

## 🚀 Getting Started

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/subrahmanyasv/HCPLogger_Backend.git](https://github.com/subrahmanyasv/HCPLogger_Backend.git)
    cd HCPLogger_Backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    * Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    * Edit the `.env` file and provide your actual configuration details:

##  Running the Application

* Use Uvicorn to run the FastAPI application:
    ```bash
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
   
* The application will typically be available at `http://127.0.0.1:8000`.

# Contact Information

For any communications, please contact me at:
**Email:** [subrahmanyavaidya7@gmail.com](mailto:subrahmanyavaidya7@gmail.com)


