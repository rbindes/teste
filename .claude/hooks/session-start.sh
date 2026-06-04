#!/bin/bash
set -euo pipefail

# Só faz sentido em sessões remotas (Claude Code na web), onde o container
# é temporário e a skill global precisa ser reinstalada a cada sessão.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Idempotente: se a skill global já estiver presente, não faz nada.
if [ -e "$HOME/.claude/skills/find-skills/SKILL.md" ]; then
  echo "find-skills: skill global já instalada."
  exit 0
fi

echo "find-skills: instalando skill global..."
# Best-effort: não bloqueia o início da sessão caso a rede/instalação falhe.
if npx -y skills add https://github.com/vercel-labs/skills --skill find-skills --global; then
  echo "find-skills: instalada com sucesso."
else
  echo "find-skills: falha ao instalar (seguindo sem bloquear a sessão)." >&2
fi

exit 0
