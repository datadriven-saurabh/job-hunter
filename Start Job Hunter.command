#!/bin/zsh
PROJECT_DIR="${0:A:h}"
cd "$PROJECT_DIR"
"$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/scripts/local.py" start
if [ $? -eq 0 ]; then
  open 'http://localhost:3000'
else
  echo 'Startup failed. Check data/runtime/ for service logs.'
  read -r 'REPLY?Press Enter to close.'
fi
