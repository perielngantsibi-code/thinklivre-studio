#!/bin/bash
# usage: build.sh OUT.mp4 [start_s end_s]
set -e
cd "$(dirname "$0")"
OUT=$1; A=${2:-0}; B=${3:-$(python3 -c "import json;print(json.load(open('plan.json'))['duration'])")}
FA=$(python3 -c "print(int($A*30))"); FB=$(python3 -c "print(int($B*30))")
N=${RENDER_PROCS:-$(nproc)}; [ $N -gt 8 ] && N=8; STEP=$(( (FB-FA+N-1)/N ))
mkdir -p parts
for i in $(seq 0 $((N-1))); do
  s=$((FA+i*STEP)); e=$((s+STEP)); [ $e -gt $FB ] && e=$FB
  python3 render.py $s $e parts/p$i.mp4 &
done
wait
: > parts/list.txt; for i in $(seq 0 $((N-1))); do echo "file 'p$i.mp4'" >> parts/list.txt; done
ffmpeg -v error -y -f concat -safe 0 -i parts/list.txt -c copy parts/video.mp4
ffmpeg -v error -y -i parts/video.mp4 -ss $A -t $(python3 -c "print($B-$A)") -i mix_final.wav -map 0:v -map 1:a -c:v libx264 -preset slow -b:v 8M -maxrate 10M -bufsize 16M -pix_fmt yuv420p -c:a aac -b:a 256k -shortest -movflags +faststart "$OUT"
echo built $OUT
