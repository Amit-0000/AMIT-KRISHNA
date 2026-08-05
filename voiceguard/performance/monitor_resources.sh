#!/usr/bin/env bash
# Samples `docker stats` for the VoiceGuard stack every 2s and writes CSV rows.
# Runs until stop-monitor file appears or DURATION seconds elapse.
OUT="performance/results/resource_usage.csv"
DURATION="${1:-75}"
echo "timestamp,container,cpu_pct,mem_usage_mb,mem_limit_mb" > "$OUT"
END=$((SECONDS + DURATION))
while [ $SECONDS -lt $END ]; do
  TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" \
    voiceguard-backend-1 voiceguard-postgres-1 voiceguard-redis-1 voiceguard-frontend-1 2>/dev/null | \
  while IFS=, read -r name cpu mem; do
    cpu_num=$(echo "$cpu" | tr -d '%')
    mem_used=$(echo "$mem" | awk -F' / ' '{print $1}')
    mem_limit=$(echo "$mem" | awk -F' / ' '{print $2}')
    to_mb() {
      v="$1"
      if [[ "$v" == *GiB ]]; then echo "${v%GiB}" | awk '{print $1*1024}'
      elif [[ "$v" == *MiB ]]; then echo "${v%MiB}"
      elif [[ "$v" == *KiB ]]; then echo "${v%KiB}" | awk '{print $1/1024}'
      else echo "0"; fi
    }
    mem_used_mb=$(to_mb "$mem_used")
    mem_limit_mb=$(to_mb "$mem_limit")
    echo "${TS},${name},${cpu_num},${mem_used_mb},${mem_limit_mb}" >> "$OUT"
  done
  sleep 2
done
