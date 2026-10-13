# AI-Based Local Problem Detection, Prioritization, and Automated Multi-Action Alert System for Officials

This repository contains a complete full-stack web application.

For a complete checkout including the road-damage dataset source, clone with submodules:

```sh
git clone --recurse-submodules https://github.com/samanvithak1/local_problem_discovery.git
```

## Technology Stack
- Frontend: React.js + Vite
- Backend: Flask (Python)
- Database: MySQL
- Authentication: JWT
- UI: Modern transparent glassmorphism with responsive layout
- Icons: React Icons and Material UI

## Project Structure
- `frontend/` - React application with public-facing pages, authentication flows, and dashboards
- `backend/` - Flask API server, models, JWT authentication, and admin/official workflows
- `db/schema.sql` - MySQL schema for the application

## Backend Setup
1. Create a Python virtual environment inside `backend/`:
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. Configure local database credentials in `backend/.env`:
   ```ini
   SECRET_KEY=your-secret-key
   JWT_SECRET_KEY=your-jwt-secret
   DATABASE_URI=mysql+pymysql://root:password@localhost:3306/problem_alert_db
   ```
3. Create the database and tables with the provided schema:
   ```powershell
   mysql -u root -p < ..\db\schema.sql
   ```
4. Seed a local admin, status values, and departments (the first-run admin password is generated randomly and printed once):
   ```powershell
   python sample_data.py
   ```
5. Run the Flask backend server:
   ```powershell
   python app.py
   ```

## Frontend Setup
1. Install dependencies in `frontend/`:
   ```powershell
   cd frontend
   npm install
   ```
2. Start the development server:
   ```powershell
   npm run dev
   ```
3. Open the app at `http://localhost:3000`

## Authentication
- Citizens: `/auth/login/user`, `/auth/register/user`
- Officials: `/auth/login/official`, `/auth/register/official`
- Admin: `/auth/login/admin`
- Password reset: `/auth/forgot-password` and `/auth/reset-password`

## Available Database Tables
- `users`
- `officials`
- `admins`
- `departments`
- `complaint_status`
- `complaints`
- `notifications`
- `images`
- `logs`

## Notes
- Official registrations require admin approval before login.
- The app uses JWT stored in local storage for authentication.
- Google Maps embeds are included for location selection previews.
- Official identity card and complaint media upload support is implemented using backend file upload endpoints.
