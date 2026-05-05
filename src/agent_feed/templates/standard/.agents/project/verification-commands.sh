#!/usr/bin/env sh

# Project-owned custom code verification hook.
# Source of active profile: .agents/agent-feed.json verification_profile
# Used by .agents/scripts/verify-agent-dev.sh when the selected profile is custom.

# Replace this function with this repository's real code verification commands
# when .agents/agent-feed.json sets verification_profile to "custom".
# Keep commands deterministic and local to the project. Do not put secrets here.
#
# Example for a Node/npm project:
#
# run_project_code_checks() {
#   npm test
#   npm run lint
#   npm run build
# }
#
# Remove this placeholder implementation after adding real project commands.
run_project_code_checks() {
  red=$(printf '\033[31m')
  yellow=$(printf '\033[33m')
  blue=$(printf '\033[34m')
  green=$(printf '\033[32m')
  bold=$(printf '\033[1m')
  reset=$(printf '\033[0m')
  if [ ! -t 2 ]; then
    red=""
    yellow=""
    blue=""
    green=""
    bold=""
    reset=""
  fi
  printf '%s%sError:%s Custom code verification is not configured yet.%s\n' "$red" "$bold" "$reset$red" "$reset" >&2
  printf '%sEdit %s.agents/project/verification-commands.sh%s and replace %srun_project_code_checks()%s.%s\n' "$yellow" "$blue" "$reset$yellow" "$green$bold" "$reset$yellow" "$reset" >&2
  printf '%sExample:%s\n' "$yellow" "$reset" >&2
  printf '  %srun_project_code_checks() {%s\n' "$green$bold" "$reset" >&2
  printf '    %snpm test%s\n' "$green" "$reset" >&2
  printf '    %snpm run lint%s\n' "$green" "$reset" >&2
  printf '    %snpm run build%s\n' "$green" "$reset" >&2
  printf '  %s}%s\n' "$green$bold" "$reset" >&2
  return 1
}
