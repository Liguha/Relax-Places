## Deploy
Build and run:
```bash
docker compose build --build-arg POSTGRES_DB=<database> --build-arg POSTGRES_USER=<user> --build-arg POSTGRES_PASSWORD=<password>
docker compose up
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