# Mnemosyne Full-Stack AI Dashboard

> **LICENSE NOTICE**: This is a **source-available, NOT open-source** project. Viewing is permitted, but copying, redistribution, commercial use, and derivative works are **strictly prohibited** without written permission. See [LICENSE](LICENSE) for details.

This project is a complete, real-world full-stack SaaS application for the Mnemosyne system. It features a stunning, cinematic React (Vite) frontend with glassmorphic design and a high-performance Python FastAPI backend.

## Prerequisites
- Node.js (for frontend)
- Python 3.9+ (for backend)

## 1. How to run the Backend
1. Open a terminal and navigate to `backend/`:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the FastAPI server:
   ```bash
    python -m uvicorn app.main:app --reload
    ```
    *Note: Using `python -m` ensures the local path is correctly included in the search path.*
   *The backend will run on `http://localhost:8000`.*

## 2. How to run the Frontend
1. Open a new, separate terminal and navigate to `frontend/`:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *The frontend will run on `http://localhost:5173`.*

## 3. How to Use
1. Open `http://localhost:5173` in your browser.
2. Click **Register** at the bottom of the login box to create an account.
3. Login with your new credentials.
4. Use the Chat Panel to send a command. The dashboard will hit the backend API, automatically generate a real Execution Plan, and populate the Execution Logs.
5. You can click on active Plan Steps (with glowing borders) to mock their completion, and the Live Logs will update automatically via polling!
