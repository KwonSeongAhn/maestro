#!/usr/bin/env bash
# tools/install-git-hooks.sh
# pre-commit 프레임워크 없이도 순정 git 훅으로 STL 검증을 강제 설치한다.
#   사용:  bash tools/install-git-hooks.sh
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
hook="$repo_root/.git/hooks/pre-commit"

cat > "$hook" <<'HOOK'
#!/usr/bin/env bash
# [auto-installed] STL fuse/manifold 규칙 강제
set -euo pipefail
stls=$(git diff --cached --name-only --diff-filter=ACM | grep -i '\.stl$' || true)
[ -z "$stls" ] && exit 0
echo "[pre-commit] STL 검증: $stls"
if ! python3 "$(git rev-parse --show-toplevel)/tools/check_stl.py" $stls; then
  echo ""
  echo "❌ STL 검증 실패 — boolean union(fuse)/manifold 여부 확인 후 다시 커밋하세요."
  echo "   (규칙: STL_RULES.md,  우회 필요시 git commit --no-verify)"
  exit 1
fi
HOOK

chmod +x "$hook"
echo "설치 완료: $hook"
echo "이제 *.stl 커밋 시 tools/check_stl.py 로 자동 검증됩니다."
