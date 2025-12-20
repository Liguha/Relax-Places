## Deploy
Build and run:
```bash
docker compose build
docker compose up
```
with .env file:
```
POSTGRES_DB=...
POSTGRES_USER=...
POSTGRES_PASSWORD=...
DB_HOST=...
DB_PORT=...
LLM_BASE_URL=...
LLM_API_KEY=...
LLM_NAME=...
```

If you change a database clear volumes by (IMPORTANT - data will be lost):
```bash
docker compose down -v
```

Check is all ok:
```bash
# ping each service
curl http://localhost:8000/ping
curl http://localhost:8001/ping
curl http://localhost:8002/ping
# check DB accessibility from api
curl http://localhost:8000/check-db
```