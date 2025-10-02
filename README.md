# company-knowledgebase-app-156280-156439

Backend container: APIGatewayBackendService (FastAPI)

Run locally:
1) Create and populate .env from APIGatewayBackendService/.env.example
2) Ensure PostgreSQL is available and DATABASE_URL points to it (asyncpg driver)
3) Install deps:
   pip install -r APIGatewayBackendService/requirements.txt
4) Start dev server:
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000 --app-dir APIGatewayBackendService

Open API docs at: http://localhost:8000/docs

Key features implemented:
- OAuth2/JWT auth with optional MFA (TOTP) and refresh tokens
- RBAC with admin/user roles
- Content CRUD with multipart uploads (text, video, audio), metadata, tagging, versioning, and soft/hard delete
- Basic search and Q&A stubs with audit logging
- Tamper-evident audit log chain
- Modular structure for future extensions (LDAP/SSO/Search/AI)

Note: Use Alembic for DB migrations in production. Models are defined in src/api/models/models.py.