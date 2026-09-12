#!/usr/bin/env bash
# Live tuning for the two things you will actually want to change on the night.
#
#   ./tune.sh show          what it is set to right now
#   ./tune.sh vad 120       raise the listening threshold, then restart
#   ./tune.sh vol 0.6       set the speaker volume
#
# Why a script: both settings live in awkward places. The threshold is in
# jarvis.env and needs a service restart to take effect; the volume is owned by
# wireplumber under a sink id that CHANGES every time the device re-enumerates,
# so the number you used an hour ago is probably wrong now. This finds it.
set -euo pipefail

ENV_FILE="$HOME/.config/jarvis/jarvis.env"

sink_id() {
    # The sink is the line carrying "[vol:" — the other Pebble line is the
    # device, and setting volume on that one silently does nothing.
    wpctl status | grep -i pebble | grep 'vol:' \
        | sed -E 's/^[^0-9]*([0-9]+)\..*$/\1/' | head -1
}

current_vad() { grep -E '^JARVIS_VAD_SILENCE=' "$ENV_FILE" | cut -d= -f2 || true; }

case "${1:-show}" in
  show)
    echo "  VAD threshold : $(current_vad)   (higher = ignores more distant noise)"
    id=$(sink_id)
    if [ -n "$id" ]; then
        echo "  Speaker       : $(wpctl get-volume "$id" 2>/dev/null || echo '?')  (sink $id)"
        echo "  ALSA reads    : $(amixer -c V3 2>/dev/null | grep -oE '\[[0-9]+%\]' | head -1)"
    fi
    ;;

  vad)
    [ $# -eq 2 ] || { echo "usage: ./tune.sh vad <number>" >&2; exit 2; }
    # Replace in place if present, append if not — appending a duplicate would
    # leave the old line winning or losing depending on order, which has caused
    # real faults on this build.
    if grep -qE '^JARVIS_VAD_SILENCE=' "$ENV_FILE"; then
        sed -i "s/^JARVIS_VAD_SILENCE=.*/JARVIS_VAD_SILENCE=$2/" "$ENV_FILE"
    else
        echo "JARVIS_VAD_SILENCE=$2" >> "$ENV_FILE"
    fi
    n=$(grep -cE '^JARVIS_VAD_SILENCE=' "$ENV_FILE")
    [ "$n" -eq 1 ] || { echo "❌ $n copies of JARVIS_VAD_SILENCE — fix by hand" >&2; exit 1; }
    echo "  VAD threshold → $2, restarting..."
    sudo systemctl restart jarvis
    echo "  done. Watch: journalctl -u jarvis -f"
    ;;

  vol)
    [ $# -eq 2 ] || { echo "usage: ./tune.sh vol <0.0-1.0>" >&2; exit 2; }
    id=$(sink_id)
    [ -n "$id" ] || { echo "❌ no Pebble sink found in wpctl status" >&2; exit 1; }
    wpctl set-volume "$id" "$2"
    echo "  Speaker → $2 on sink $id"
    echo "  ALSA now: $(amixer -c V3 2>/dev/null | grep -oE '\[[0-9]+%\]' | head -1)"
    ;;

  *)
    echo "usage: ./tune.sh [show | vad <number> | vol <0.0-1.0>]" >&2
    exit 2
    ;;
esac
