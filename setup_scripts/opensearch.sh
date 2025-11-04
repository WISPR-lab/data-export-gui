#!/usr/bin/env bash
OPENSEARCH_IMAGE="opensearchproject/opensearch:2.15.0"
OPENSEARCH_HOST="127.0.0.1"
OPENSEARCH_PORT="9200"
ACTION="start"
RM_DATA=false
CONTAINER_NAME="opensearch"
DATA_VOLUME_PATH="$(pwd)/data/opensearch"
# NETWORK_NAME="ts-net"

echo "DATA_VOLUME_PATH: ${DATA_VOLUME_PATH}"

usage() {
  cat <<EOF
Usage: $0 [--start|-s] [--down|-d] [--rm-data] [--help|-h]

  --start, -s     Start the OpenSearch container (default action).
  --down, -d      Stop and remove the OpenSearch container and network.
  --rm-data       When used with --down, also remove persistent data volume
  --help, -h      Show this help message.
EOF
}

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found. install Docker Desktop and start it." >&2
  exit 1
fi


while [[ $# -gt 0 ]]; do
  case "$1" in
    --start|-s)
      ACTION="start"; shift;;
    --down|--stop|-d)
      ACTION="down"; shift;;
    --rm-data)
      RM_DATA=true; shift;;
    --help|-h)
      usage; exit 0;;
    *)
      echo "Unknown option: $1" >&2; usage; exit 2;;
  esac
done


start_container() {
  if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "OpenSearch container already running."
    return 0
  fi
  if [ ! -d "${pwd}/data" ]; then
    mkdir -p "data"
  fi

  if [ ! -d "${DATA_VOLUME_PATH}" ]; then
    mkdir -p "${DATA_VOLUME_PATH}"
    # opensearch runs as UID 1000 in the official image; change ownership if possible.
    chown 1000:1000 "${DATA_VOLUME_PATH}" 2>/dev/null || true
  fi

  echo "Starting OpenSearch container (may take a minute)..."
  # docker network create "${NETWORK_NAME}" >/dev/null 2>&1 || true

  docker run -d --name "${CONTAINER_NAME}" \
    --ulimit memlock=-1:-1 \
    -e discovery.type=single-node \
    -e "DISABLE_INSTALL_DEMO_CONFIG=true" \
    -e "DISABLE_SECURITY_PLUGIN=true" \
    -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
    -p ${OPENSEARCH_HOST}:${OPENSEARCH_PORT}:${OPENSEARCH_PORT} \
    -v "${DATA_VOLUME_PATH}":/usr/share/opensearch/data \
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

  # if docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
  #   echo "Removing network ${NETWORK_NAME}..."
  #   docker network rm "${NETWORK_NAME}" >/dev/null 2>&1 || true
  # fi

  if [ "${RM_DATA}" = true ]; then
    if [ -d "${DATA_VOLUME_PATH}" ]; then
      echo "Removing host data directory ${DATA_VOLUME_PATH}."
      rm -rf "${DATA_VOLUME_PATH}" 2>/dev/null || true
    fi
  else
    echo "Leaving data volume ${DATA_VOLUME_PATH} intact. Use --rm-data to delete it."
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