# Database migrations

Run migrations from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

`DATABASE_URL` is read from `backend/.env`; it is never stored in Alembic files.

