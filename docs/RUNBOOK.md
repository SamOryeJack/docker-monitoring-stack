# Operations Runbook

**System:** GPU Infrastructure Monitoring Stack  
**Platform:** Docker Compose on GCP  
**Last Updated:** October 2025

---

## Quick Reference

### Access Information

**SSH Access:**
```bash
gcloud compute ssh monitoring-stack --zone=us-central1-a
```

**Service URLs:**
- Grafana: `http://[EXTERNAL_IP]:3000` (admin / YOUR_PASSWORD)
- Prometheus: `http://[EXTERNAL_IP]:9090`

### Common Commands

```bash
# View all containers
docker-compose ps

# Check container logs
docker logs [container-name] -f

# Restart a service
docker-compose restart [service-name]

# View resource usage
docker stats --no-stream
```

---

## Daily Health Check (5 minutes)

Run this script every morning to verify system health:

```bash
#!/bin/bash
# Save as: daily_health_check.sh

echo "=== Monitoring Stack Health Check $(date) ==="
echo ""

# 1. Container Status
echo "📦 Container Status:"
RUNNING=$(docker-compose ps | grep -c "Up")
echo "   Running: $RUNNING / 14 containers"
[[ $RUNNING -eq 14 ]] && echo "   ✅ All containers healthy" || echo "   ⚠️  Some containers down!"
echo ""

# 2. Prometheus Targets
echo "🎯 Prometheus Targets:"
HEALTHY=$(curl -s localhost:9090/api/v1/targets 2>/dev/null | jq -r '.data.activeTargets[].health' | grep -c "up")
echo "   Healthy: $HEALTHY / 9 targets"
[[ $HEALTHY -eq 9 ]] && echo "   ✅ All targets healthy" || echo "   ⚠️  Some targets down!"
echo ""

# 3. System Resources
echo "💻 System Resources:"
echo "   Memory: $(free -h | grep Mem | awk '{print $3 " / " $2}')"
echo "   Disk: $(df -h / | tail -1 | awk '{print $3 " / " $2 " (" $5 " used)"}')"
echo "   Load: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

# 4. Active Alerts
echo "🚨 Active Alerts:"
ALERTS=$(curl -s localhost:9090/api/v1/alerts 2>/dev/null | jq -r '.data.alerts | length')
echo "   Count: $ALERTS"
[[ $ALERTS -eq 0 ]] && echo "   ✅ No active alerts" || echo "   ⚠️  Review alerts in Prometheus"
echo ""

echo "Health check complete!"
```

---

## Service Management

### Start All Services

```bash
cd ~/monitoring-project
docker-compose up -d

# Wait for services to be ready
sleep 30

# Verify all started
docker-compose ps
```

### Stop All Services

```bash
cd ~/monitoring-project
docker-compose down

# To also remove volumes (⚠️ WARNING: deletes all data):
# docker-compose down -v
```

### Restart Specific Service

```bash
docker-compose restart [service-name]

# Examples:
docker-compose restart prometheus
docker-compose restart grafana
docker-compose restart python-app
```

### Rolling Restart (Zero Downtime)

```bash
# Restart monitoring core first
docker-compose restart prometheus
sleep 10
docker-compose restart grafana
sleep 5

# Restart exporters (no dependencies)
for service in node-exporter cadvisor nginx-exporter redis-exporter postgres-exporter; do
  echo "Restarting $service..."
  docker-compose restart $service
  sleep 3
done

# Restart application stack
docker-compose restart nginx redis postgres
sleep 5

# Restart custom apps
docker-compose restart python-app load-generator gpu-simulator ml-simulator

echo "Rolling restart complete!"
```

---

## Common Operational Tasks

### View Container Logs

```bash
# Real-time logs (follows)
docker logs [container-name] -f

# Last 100 lines
docker logs [container-name] --tail 100

# Since specific time
docker logs [container-name] --since 1h

# Examples:
docker logs prometheus -f
docker logs python-app --tail 50
docker logs grafana --since 30m
```

### Check Resource Usage

```bash
# All containers
docker stats --no-stream

# Specific container
docker stats python-app --no-stream

# Continuous monitoring
docker stats

# Sort by memory usage
docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}" | sort -k2 -h
```

### Access Container Shell

```bash
# Interactive shell
docker exec -it [container-name] sh

# Run single command
docker exec [container-name] [command]

# Examples:
docker exec -it prometheus sh
docker exec grafana grafana-cli plugins list
docker exec postgres psql -U metrics_user -d metrics_db -c "SELECT version();"
```

---

## Troubleshooting

### Issue: Container Not Starting

**Symptoms:**
- Container missing from `docker-compose ps`
- Status shows "Exited"
- Service unavailable

**Investigation:**
```bash
# Check logs for errors
docker logs [container-name] --tail 100

# Check exit code
docker inspect [container-name] | grep -A 5 "State"

# Check for port conflicts
sudo netstat -tulpn | grep [port-number]
```

**Resolution:**
```bash
# Remove and recreate container
docker-compose stop [service-name]
docker-compose rm -f [service-name]
docker-compose up -d [service-name]

# If that doesn't work, rebuild
docker-compose build --no-cache [service-name]
docker-compose up -d [service-name]
```

### Issue: High Memory Usage

**Symptoms:**
- System slowdown
- OOM kills in logs
- Containers being killed

**Investigation:**
```bash
# Check per-container usage
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check Prometheus TSDB size
du -sh ~/monitoring-project/prometheus_data

# Check metric cardinality
curl -s 'localhost:9090/api/v1/label/__name__/values' | jq '. | length'
```

**Resolution:**

1. **Add memory limits to docker-compose.yml:**
```yaml
python-app:
  deploy:
    resources:
      limits:
        memory: 256M
      reservations:
        memory: 128M
```

2. **Reduce Prometheus retention:**
```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=15d'  # Reduce from 30d
    - '--storage.tsdb.retention.size=5GB'  # Add size limit
```

3. **Restart affected services:**
```bash
docker-compose up -d
```

### Issue: Prometheus Target Down

**Symptoms:**
- Target shows "DOWN" in Prometheus UI
- Missing metrics
- Scrape errors

**Investigation:**
```bash
# Check target status
curl -s localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health=="down")'

# Check if container is running
docker ps | grep [target-name]

# Check container logs
docker logs [target-container]

# Test endpoint directly
curl http://localhost:[port]/metrics
```

**Resolution:**

1. **Container not running:**
```bash
docker-compose restart [service-name]
```

2. **Network connectivity issue:**
```bash
# Test from Prometheus container
docker exec prometheus wget -O- http://[target]:[port]/metrics

# Check network
docker network inspect monitoring-project_monitoring
```

3. **Wrong configuration:**
```bash
# Check prometheus.yml for correct target
cat prometheus/prometheus.yml | grep [target-name]
```

### Issue: No Data in Grafana

**Symptoms:**
- Dashboards show "No data"
- Panels are empty
- Queries return no results

**Investigation:**
```bash
# Test Prometheus directly
curl "http://localhost:9090/api/v1/query?query=up"

# Check datasource from Grafana
docker exec grafana curl http://prometheus:9090/api/v1/query?query=up

# Check Prometheus targets
curl -s localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

**Resolution:**

1. **Verify Prometheus is running:**
```bash
docker-compose ps prometheus
curl http://localhost:9090/-/healthy
```

2. **Check datasource in Grafana:**
   - Navigate to Configuration → Data Sources
   - Click on Prometheus
   - Click "Test" button
   - Should show "Data source is working"

3. **Verify time range:**
   - Check dashboard time picker (top right)
   - Try "Last 1 hour" or "Last 6 hours"
   - Some metrics may take time to appear

4. **Test with simple query:**
   - Open any panel, click Edit
   - Try query: `up`
   - Should show all targets

### Issue: Disk Space Full

**Symptoms:**
- Prometheus fails to start
- "no space left on device" errors
- System slowdown

**Investigation:**
```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Check largest directories
du -sh ~/monitoring-project/* | sort -h
```

**Resolution:**

1. **Clean up Docker:**
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes (⚠️ careful!)
docker volume prune

# Remove all unused data
docker system prune -a
```

2. **Reduce Prometheus retention:**
```bash
# Edit docker-compose.yml
nano docker-compose.yml

# Add/modify:
prometheus:
  command:
    - '--storage.tsdb.retention.time=7d'  # Reduce to 7 days
```

3. **Restart Prometheus:**
```bash
docker-compose up -d prometheus
```

---

## Backup Procedures

### Create Backup

```bash
#!/bin/bash
# Save as: backup.sh

BACKUP_DIR="/home/$USER/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

echo "Starting backup to $BACKUP_DIR..."

# Backup Prometheus data
echo "Backing up Prometheus..."
docker run --rm \
  -v monitoring-project_prometheus_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/prometheus_data.tar.gz -C /data .

# Backup Grafana data
echo "Backing up Grafana..."
docker run --rm \
  -v monitoring-project_grafana_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/grafana_data.tar.gz -C /data .

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
docker exec postgres pg_dump -U metrics_user metrics_db > $BACKUP_DIR/postgres_dump.sql

# Backup configurations
echo "Backing up configs..."
tar czf $BACKUP_DIR/configs.tar.gz ~/monitoring-project/prometheus ~/monitoring-project/grafana ~/monitoring-project/docker-compose.yml

echo "Backup complete!"
echo "Location: $BACKUP_DIR"
ls -lh $BACKUP_DIR
```

### Restore from Backup

```bash
#!/bin/bash
# Save as: restore.sh

if [ -z "$1" ]; then
    echo "Usage: $0 <backup-directory>"
    exit 1
fi

BACKUP_DIR=$1

echo "⚠️  WARNING: This will overwrite existing data!"
read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Stop services
echo "Stopping services..."
cd ~/monitoring-project
docker-compose down

# Restore Prometheus
echo "Restoring Prometheus..."
docker run --rm \
  -v monitoring-project_prometheus_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar xzf /backup/prometheus_data.tar.gz -C /data

# Restore Grafana
echo "Restoring Grafana..."
docker run --rm \
  -v monitoring-project_grafana_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar xzf /backup/grafana_data.tar.gz -C /data

# Restore PostgreSQL
echo "Restoring PostgreSQL..."
docker-compose up -d postgres
sleep 10
cat $BACKUP_DIR/postgres_dump.sql | docker exec -i postgres psql -U metrics_user metrics_db

# Start all services
echo "Starting services..."
docker-compose up -d

echo "Restore complete!"
```

---

## Performance Tuning

### Prometheus Optimization

Edit `docker-compose.yml`:

```yaml
prometheus:
  command:
    # Reduce retention for lower memory
    - '--storage.tsdb.retention.time=15d'
    
    # Set size-based retention
    - '--storage.tsdb.retention.size=5GB'
    
    # Optimize block size
    - '--storage.tsdb.min-block-duration=2h'
    - '--storage.tsdb.max-block-duration=2h'
    
    # Tune query engine
    - '--query.max-concurrency=10'
    - '--query.timeout=2m'
```

### Grafana Optimization

```yaml
grafana:
  environment:
    - GF_DATABASE_WAL=true
    - GF_ANALYTICS_REPORTING_ENABLED=false
    - GF_USERS_DEFAULT_THEME=light
```

---

## Useful PromQL Queries

### System Metrics

```promql
# CPU usage percentage
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage percentage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk usage percentage
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100

# System load
node_load1
node_load5
```

### Application Metrics

```promql
# Request rate
sum(rate(app_requests_total[1m])) by (endpoint)

# Error rate percentage
sum(rate(app_requests_total{status=~"5.."}[5m])) / sum(rate(app_requests_total[5m])) * 100

# p95 latency
histogram_quantile(0.95, rate(app_request_duration_seconds_bucket[5m]))

# Active connections
app_active_connections
```

### GPU Metrics

```promql
# Average GPU utilization
avg(gpu_utilization_percent)

# GPU temperature
gpu_temperature_celsius

# GPUs over threshold
count(gpu_temperature_celsius > 80)

# GPU with highest temperature
topk(1, gpu_temperature_celsius)
```

---

## Monitoring the Monitors

### Key Metrics to Watch

```promql
# Prometheus up
up{job="prometheus"}

# Scrape duration
scrape_duration_seconds

# Time series count
prometheus_tsdb_head_series

# Query duration
rate(prometheus_engine_query_duration_seconds_sum[5m])
```

---

## Emergency Procedures

### Complete Stack Recovery

```bash
#!/bin/bash
# Emergency recovery script

echo "⚠️  EMERGENCY RECOVERY"
read -p "Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then exit 0; fi

cd ~/monitoring-project

# Stop everything
echo "Stopping containers..."
docker-compose down

# Clean up
echo "Cleaning up..."
docker system prune -f

# Restart Docker
echo "Restarting Docker..."
sudo systemctl restart docker
sleep 10

# Recreate network
echo "Recreating network..."
docker network create monitoring-project_monitoring 2>/dev/null || true

# Start core services first
echo "Starting Prometheus..."
docker-compose up -d prometheus
sleep 20

echo "Starting Grafana..."
docker-compose up -d grafana
sleep 10

# Start everything else
echo "Starting remaining services..."
docker-compose up -d

echo "Waiting for stabilization..."
sleep 30

# Verify
echo "Verifying services..."
docker-compose ps
curl -s localhost:9090/-/healthy
curl -s localhost:3000/api/health

echo "Recovery complete!"
```

---

## Maintenance Schedule

### Daily
- Run health check script
- Check active alerts
- Review resource usage

### Weekly
- Review dashboard usage
- Check for container updates
- Analyze resource trends
- Test backup restoration

### Monthly
- Full backup
- Security updates
- Performance review
- Documentation updates

---

## Conclusion

This runbook covers the most common operational scenarios. For issues not covered here, refer to:
- [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- [README.md](README.md) for project overview
- Prometheus docs: https://prometheus.io/docs/
- Grafana docs: https://grafana.com/docs/