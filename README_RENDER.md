# Deploying CareLink AI to Render

This folder is configured for deployment on Render.

## Steps to Deploy

1.  **Create a Repository**: Push this `CareLink_Render` folder to a new GitHub/GitLab repository.
2.  **Sign up for Render**: Go to [render.com](https://render.com) and create an account.
3.  **New Web Service**:
    *   Click "New" -> "Web Service".
    *   Connect your GitHub/GitLab account and select the repository you just created.
4.  **Configuration**:
    *   Render should automatically detect the `render.yaml` file and configure the service.
    *   If not, manually set:
        *   **Runtime**: Python 3
        *   **Build Command**: `pip install -r requirements.txt`
        *   **Start Command**: `gunicorn backend.app:app`
5.  **Deploy**: Click "Create Web Service".

## Important Notes

*   **Database**: This deployment uses SQLite (`carelink.db`). **Data will be reset** every time the app redeploys or restarts. For persistent data, consider using Render's PostgreSQL database service and updating the `SQLALCHEMY_DATABASE_URI` in `backend/app.py`.
*   **Security**: The `JWT_SECRET_KEY` is currently hardcoded in `backend/app.py`. For production, you should use environment variables.
    *   In Render dashboard: go to **Environment** tab and add `JWT_SECRET_KEY` with a secure random string.
    *   Update `backend/app.py` to use `os.environ.get('JWT_SECRET_KEY')`.
