# Project env for measurmentify + Orbbec
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Put project libs first so they win over site-packages
export PYTHONPATH="$PROJECT_ROOT/install/lib:$PROJECT_ROOT/third-party/pyorbbecsdk/install/lib${PYTHONPATH:+:$PYTHONPATH}"

# (optional) handy marker
export MEASURMENTIFY_ROOT="$PROJECT_ROOT"
