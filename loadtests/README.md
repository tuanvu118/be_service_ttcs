# QR Attendance k6 Load Test

This script prepares test data and then sends QR scan traffic through Caddy.

Default target:

```text
POST http://caddy/api/attendance/scan
```

Run from `be_ttcs`:

```powershell
docker compose --profile loadtest run --rm k6
```

Useful overrides:

```powershell
$env:K6_USER_COUNT="1000"
$env:K6_RATE="1000"
$env:K6_DURATION="1s"
$env:K6_SETUP_TIMEOUT="10m"
$env:K6_PRE_ALLOCATED_VUS="1000"
$env:K6_MAX_VUS="2000"
$env:K6_QR_WINDOW_SECONDS="300"
docker compose --profile loadtest run --rm k6
```

`setup()` creates users, logs them in, registers them to the event, and waits for
`event_start`. Keep `K6_SETUP_TIMEOUT` higher than that preparation time.

What the script does:

```text
1. Login seed admin ADMIN / ADMIN.
2. Create a load-test event.
3. Create USER_COUNT users.
4. Login every user.
5. Register every user to the event.
6. Wait until event_start.
7. Open one QR session.
8. Send RATE requests/second to /attendance/scan.
```

For a meaningful success test, keep `USER_COUNT >= RATE * duration_seconds`.
Otherwise duplicate check-in protection will intentionally reject reused users.
