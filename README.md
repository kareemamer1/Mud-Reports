# Mud Reports

Full-stack application with React + TypeScript frontend and FastAPI + SQLite backend.

## Features

- **Frontend**: React 18, TypeScript, Vite, Axios
- **Backend**: FastAPI, SQLAlchemy, SQLite, Pydantic
- **API**: RESTful CRUD endpoints for items
- **CORS**: Configured for local development

## Setup

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python init_db.py
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm start
```

## Access

- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs

## Ports

- Frontend: 5173
- Backend: 8080

## Production

Update `backend/.env` with secure values before deploying to production.
