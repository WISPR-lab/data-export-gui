#!/usr/bin/env bash




usage() {
  cat <<EOF
Usage: $0 [--start|-s] [--down|-d] [--rm-data] [--config|-c <config-file>] [--help|-h]

  --start, -s     Start the OpenSearch container (default action).
  --down, -d      Stop and remove the OpenSearch container and network.
  --rm-data       When used with --down, also remove persistent data volume
  --config, -c    Path to the OpenSearch configuration file (timesketch.conf).
  --help, -h      Show this help message.
EOF
}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found. install Docker Desktop and start it." >&2
  exit 1
fi

# Default settings
ACTION="start"
RM_DATA=false
CONFIG_FILE="timesketch.conf"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start|-s)
      ACTION="start"; shift;;
    --down|--stop|-d)
      ACTION="down"; shift;;
    --rm-data)
      RM_DATA=true; shift;;
    --config|-c)
      CONFIG_FILE="$2"; shift 2;;
    --help|-h)
      usage; exit 0;;
    *)
      echo "Unknown option: $1" >&2; usage; exit 2;;
  esac
done

# Verify config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file not found: $CONFIG_FILE" >&2
    exit 1
fi

# Load config variables
config_output=$(python3 -c '
import yaml, sys, os
try:
    with open("'"$CONFIG_FILE"'") as f:
        yaml_text = f.read().replace("=", ": ")
        config = yaml.safe_load(yaml_text)
        
        defaults = {
            "OPENSEARCH_HOSTS": "localhost",
            "OPENSEARCH_PORT": 9200,
            "METRICS_PORT": 9600,
            "OPENSEARCH_IMAGE": "opensearchproject/opensearch:2.15.0",
            "CONTAINER_NAME": "opensearch",
            "VOLUME_NAME": "opensearch-data",
            "NETWORK_NAME": "ts-net"
        }
        
        for k, v in defaults.items():
            if k not in config:
                config[k] = v
            if config[k] is None:  # Handle None values
                config[k] = v
        for k, v in config.items():
            if k in defaults:  # Only export variables we care about
                print(f"export {k}=\"{v}\"")
                
except Exception as e:
    print(f"Error loading config: {e}", file=sys.stderr)
    sys.exit(1)
')

if [ $? -ne 0 ]; then
    echo "Failed to load configuration" >&2
    return 1
else
    eval "$config_output"
fi 


start_container() {
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "OpenSearch container already running."
    return 0
  fi

  echo "Starting OpenSearch container (may take a minute)..."
  docker network create "${NETWORK_NAME}" >/dev/null 2>&1 || true

  docker run -d --name "${CONTAINER_NAME}" \
    --network "${NETWORK_NAME}" \
    --ulimit memlock=-1:-1 \
    -e discovery.type=single-node \
    -e "DISABLE_INSTALL_DEMO_CONFIG=true" \
    -e "DISABLE_SECURITY_PLUGIN=true" \
    -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
    -p ${OPENSEARCH_HOST}:${OPENSEARCH_PORT}:${OPENSEARCH_PORT} \
    -p ${OPENSEARCH_HOST}:${METRICS_PORT}:${METRICS_PORT} \
    -v ${VOLUME_NAME}:/usr/share/opensearch/data \
    "${OPENSEARCH_IMAGE}"

  echo "Container started (id: $(docker ps -a --filter "name=${CONTAINER_NAME}" --format '{{.ID}}' | tail -n1))"

  echo "Waiting for OpenSearch to be ready..."
  sleep 3
  for i in $(seq 1 60); do
    if curl -sS --max-time 2 "http://${OPENSEARCH_HOST}:${OPENSEARCH_PORT}/_cluster/health?wait_for_status=yellow&timeout=1s" | grep -q '"status"'; then
      echo "OpenSearch ready."
      return 0
    fi
    sleep 3
  done

  echo "Warning: OpenSearch did not report ready within timeout. Check container logs: docker logs -f ${CONTAINER_NAME}" >&2
}

down_container() {
  if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Stopping container ${CONTAINER_NAME}..."
    docker rm -f "${CONTAINER_NAME}" || true
  else
    echo "No container named ${CONTAINER_NAME} found."
  fi

  if docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
    echo "Removing network ${NETWORK_NAME}..."
    docker network rm "${NETWORK_NAME}" >/dev/null 2>&1 || true
  fi

  if [ "${RM_DATA}" = true ]; then
    echo "Removing data volume ${VOLUME_NAME}..."
    docker volume rm "${VOLUME_NAME}" >/dev/null 2>&1 || true
    if [ -d "./opensearch-data" ]; then
      rm -rf ./opensearch-data || true
    fi
  else
    echo "Leaving data volume ${VOLUME_NAME} intact. Use --rm-data to delete it."
  fi
}

case "$ACTION" in
  start)
    start_container
    ;;
  down)
    down_container
    ;;
  *)
    echo "Unknown action: $ACTION"; usage; exit 2
    ;;
esac