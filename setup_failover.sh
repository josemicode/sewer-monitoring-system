#!/bin/bash

# setup_failover.sh
# This script verifies that the InfluxDB failover infrastructure is running and provides instructions
# on how to confirm that the configuration (Buckets and Tokens) matches between the primary and secondary instances.

echo "Checking InfluxDB container status..."

PRIMARY_STATUS=$(docker ps -q -f name=influx_primary)
SECONDARY_STATUS=$(docker ps -q -f name=influx_secondary)

if [ -n "$PRIMARY_STATUS" ]; then
    echo "✅ influx_primary is running."
else
    echo "❌ influx_primary is NOT running."
fi

if [ -n "$SECONDARY_STATUS" ]; then
    echo "✅ influx_secondary is running."
else
    echo "❌ influx_secondary is NOT running."
fi

echo ""
echo "---------------------------------------------------"
echo "Verifying Configuration Consistency"
echo "---------------------------------------------------"
echo "Both instances are configured to initialize with the same environment variables from .env."
echo "To verify that they have the same initial Buckets, Orgs, and Tokens, you can inspect their environment:"

echo ""
echo "Run the following command to compare the initialization variables:"
echo "diff <(docker exec influx_primary env | grep DOCKER_INFLUXDB_INIT | sort) <(docker exec influx_secondary env | grep DOCKER_INFLUXDB_INIT | sort)"

echo ""
echo "If the command produces no output, the initial configurations are identical."
echo "Your application can switch between port 8086 (Primary) and 8087 (Secondary) using the same Token and Bucket."
