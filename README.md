# HelloWorld

Hi this is hello world !!!

## Local observability tools

This repository includes a Docker Compose observability stack you can run locally while developing the app. It provides:

- **OpenTelemetry Collector** for receiving OTLP traces, metrics, and logs from applications.
- **Prometheus** for scraping and storing metrics.
- **Grafana** for dashboards and exploration.
- **Loki** for log storage.
- **Tempo** for trace storage.

### Start the stack

```bash
docker compose -f docker-compose.observability.yml up -d
```

### Send telemetry from an app

Configure your application or OpenTelemetry SDK to export OTLP data to one of these collector endpoints:

- OTLP gRPC: `http://localhost:4317`
- OTLP HTTP: `http://localhost:4318`

The collector routes telemetry to the local backends:

- metrics -> Prometheus
- logs -> Loki
- traces -> Tempo

### Explore telemetry

After the containers are healthy, open these local tools:

- Grafana: <http://localhost:3000> (`admin` / `admin`)
- Prometheus: <http://localhost:9090>
- Loki API: <http://localhost:3100>
- Tempo API: <http://localhost:3200>

Grafana is pre-provisioned with Prometheus, Loki, and Tempo data sources plus an OpenTelemetry Collector overview dashboard.

### Stop the stack

```bash
docker compose -f docker-compose.observability.yml down
```

To remove persisted local metrics, dashboards, and traces as well:

```bash
docker compose -f docker-compose.observability.yml down -v
```
