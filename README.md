# Smart AI Job Portal - Real Time Working Project

Features:
- User signup and login
- Secure password hashing
- SQLite database
- Dashboard
- Resume PDF upload
- Skill extraction
- Real remote job API search using Remotive
- Fallback jobs if API is unavailable
- Save jobs
- Apply for jobs
- View submitted applications
- No Jinja/templates, so no template cache errors

## Run

```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```
