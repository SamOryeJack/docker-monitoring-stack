#!/bin/bash
echo "=== Monitoring Stack Health Report ==="
echo "Date: $(date)"
echo ""
echo "Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}"
echo ""
echo "Metrics Collection:"
curl -s localhost:9090/api/v1/query?query='up' | jq -r '.data.result[] | "\(.metric.job): \(.value[1])"'
echo ""
echo "Total Metrics:"
curl -s localhost:9090/api/v1/label/__name__/values | jq '.data | length'
echo ""
echo "Alert Status:"
curl -s localhost:9090/api/v1/alerts | jq -r '.data.alerts[] | "\(.labels.alertname): \(.state)"'
