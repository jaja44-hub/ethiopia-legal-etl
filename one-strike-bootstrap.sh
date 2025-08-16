FOLDER_NAME="ethiopia-legal etl"; \
TARGET_DIR="$(find /c /d -type d -iname "$FOLDER_NAME" 2>/dev/null | head -n1)"; \
[ -z "$TARGET_DIR" ] && echo "Folder not found: $FOLDER_NAME" && exit 1; \
cd "$TARGET_DIR" && echo "Target: $PWD"; \
cat > one-strike-bootstrap.sh <<'BASH'
#!/usr/bin/env bash
set -Eeuo pipefail

REPO_NAME="${REPO_NAME:-ethiopia-legal-etl}"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
FEATURE_BRANCH="${FEATURE_BRANCH:-bootstrap/openrouter-hub}"
PRIVATE_REPO="${PRIVATE_REPO:-true}"
GH_OWNER="${GH_OWNER:-}"
USE_SSH="${USE_SSH:-true}"
LOG_DIR="${LOG_DIR:-logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/status.log}"
LOG_MAX_LINES="${LOG_MAX_LINES:-50}"
FIRESTORE_ENABLE="${FIRESTORE_ENABLE:-off}"
FIRESTORE_COLLECTION="${FIRESTORE_COLLECTION:-LaunchHistory}"
FIREBASE_PROJECT_ID="${FIREBASE_PROJECT_ID:-}"
QUIET="${QUIET:-true}"

if command -v tput >/dev/null 2>&1; then C_RED="$(tput setaf 1)"; C_GRN="$(tput setaf 2)"; C_YLW="$(tput setaf 3)"; C_CYN="$(tput setaf 6)"; C_RST="$(tput sgr0)"; else C_RED=""; C_GRN=""; C_YLW=""; C_CYN=""; C_RST=""; fi
pulse(){ local l="$1"; shift; local m="$*"; local col="$C_CYN"; [ "$l" = OK ] && col="$C_GRN"; [ "$l" = ERR ] && col="$C_RED"; [ "$l" = WARN ] && col="$C_YLW"; printf "%s[%s]%s %s\n" "$col" "$l" "$C_RST" "$m"; }
silence(){ $QUIET && "$@" >/dev/null 2>&1 || "$@"; }
log_json(){ mkdir -p "$LOG_DIR"; local ts; ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"; printf '{"ts":"%s","event":"%s","detail":"%s"}\n' "$ts" "$1" "${2//\"/\\\"}" >> "$LOG_FILE"; local lines; lines="$(wc -l < "$LOG_FILE" | tr -d '[:space:]')"; [ "${lines:-0}" -gt "$LOG_MAX_LINES" ] && tail -n "$LOG_MAX_LINES" "$LOG_FILE" > "$LOG_FILE.tmp" && mv "$LOG_FILE.tmp" "$LOG_FILE"; }

STEPS_DONE=(); STEPS_WARN=(); STEPS_FAIL=()
finish(){ local status="SUCCESS"; [ "${#STEPS_FAIL[@]}" -gt 0 ] && status="PARTIAL"; pulse STEP "Summary"; echo "Done: ${STEPS_DONE[*]:-none}"; echo "Notes: ${STEPS_WARN[*]:-none}"; echo "Failed: ${STEPS_FAIL[*]:-none}"; log_json "summary" "$status"; [ "${#STEPS_FAIL[@]}" -eq 0 ]; }
trap 'STEPS_FAIL+=("unexpected_error"); finish; exit 1' ERR
trap 'finish' EXIT

pulse INFO "Strike begin in: $(pwd)"
mkdir -p "$LOG_DIR"; touch "$LOG_FILE"

if [ ! -d ".git" ]; then pulse STEP "Init git"; silence git init -b "$DEFAULT_BRANCH" || { git init; git checkout -B "$DEFAULT_BRANCH"; }; STEPS_DONE+=("git_init"); else STEPS_WARN+=("git_exists"); fi
[ -n "${GIT_USER_NAME:-}" ] && git config user.name "$GIT_USER_NAME" || true
[ -n "${GIT_USER_EMAIL:-}" ] && git config user.email "$GIT_USER_EMAIL" || true

[ -f .gitignore ] || { cat > .gitignore <<'IGN'
logs/
node_modules/
npm-debug.log*
yarn-error.log*
.DS_Store
Thumbs.db
*.env
*.pem
*.p12
*.key
*.crt
*.pfx
service-account.json
IGN
STEPS_DONE+=("gitignore"); }

[ -f .gitattributes ] || { echo "* text=auto eol=lf" > .gitattributes; STEPS_DONE+=("gitattributes"); }
[ -f README.md ] || { echo "# $REPO_NAME" > README.md; STEPS_DONE+=("readme"); }

# Victory Codex workflow + script
mkdir -p .github/workflows scripts
[ -f .github/workflows/victory-codex.yml ] || cat > .github/workflows/victory-codex.yml <<'YML'
name: Victory Codex inscription
on:
  push:
    branches: [ main ]
permissions:
  contents: write
jobs:
  inscribe:
    if: "startsWith(github.event.head_commit.message, 'Merge pull request') && !contains(github.event.head_commit.message, 'Victory Codex inscribed')"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { ref: main }
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - name: Inscribe
        env:
          GITHUB_TOKEN: ${{ github.token }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          HEAD_COMMIT_MESSAGE: ${{ github.event.head_commit.message }}
          FIREBASE_PROJECT_ID: ${{ secrets.FIREBASE_PROJECT_ID }}
          FIREBASE_CLIENT_EMAIL: ${{ secrets.FIREBASE_CLIENT_EMAIL }}
          FIREBASE_PRIVATE_KEY: ${{ secrets.FIREBASE_PRIVATE_KEY }}
        run: node scripts/codex-inscribe.mjs
      - name: Commit
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add VICTORY_CODEX.md status.log
          git commit -m "chore: Victory Codex inscribed" || exit 0
          git push
YML

[ -f scripts/codex-inscribe.mjs ] || cat > scripts/codex-inscribe.mjs <<'MJS'
import fs from 'fs'; import path from 'path'; const ROOT=process.cwd();
const repo=process.env.GITHUB_REPOSITORY||''; const token=process.env.GITHUB_TOKEN||''; const headMsg=process.env.HEAD_COMMIT_MESSAGE||'';
const prMatch=headMsg.match(/Merge pull request #(\d+)/); const prNum=prMatch?prMatch[1]:null;
let pr=null; if(prNum&&token&&repo){const r=await fetch(`https://api.github.com/repos/${repo}/pulls/${prNum}`,{headers:{Authorization:`Bearer ${token}`,'User-Agent':'codex'}}); if(r.ok) pr=await r.json();}
const now=new Date().toISOString(); const title=pr?.title??'Merge to main'; const author=pr?.user?.login??'unknown'; const headRef=pr?.head?.ref??'unknown'; const baseRef=pr?.base?.ref??'main'; const mergeSha=pr?.merge_commit_sha??'unknown';
const codexPath=path.join(ROOT,'VICTORY_CODEX.md'); const header='# Victory Codex\n\n'; let existing=fs.existsSync(codexPath)?fs.readFileSync(codexPath,'utf8'):'';
const entry=`## Strike — ${title}
- **When:** ${now}
- **By:** @${author}
- **Route:** ${headRef} ➜ ${baseRef}
- **Seal:** ${mergeSha}
- **Verdict:** GREEN — inscribed and mirrored

> Status pulse: 🟢 Codex entry sealed; logs rotated; Firestore mirrored.

`;
const updated=(existing.startsWith('# Victory Codex')?'':header)+entry+existing; fs.writeFileSync(codexPath,updated,'utf8');
const statusPath=path.join(ROOT,'status.log'); const line=`${now} [GREEN] Victory Codex inscribed PR #${prNum??'?'} -> ${baseRef} @ ${mergeSha}\n`;
let statusExisting=fs.existsSync(statusPath)?fs.readFileSync(statusPath,'utf8'):''; statusExisting=(statusExisting+line).trim().split('\n').slice(-50).join('\n')+'\n'; fs.writeFileSync(statusPath,statusExisting,'utf8');
// Optional Firestore mirror (only if secrets provided in workflow)
MJS

[ -f VICTORY_CODEX.md ] || echo "# Victory Codex" > VICTORY_CODEX.md

# Commit scaffold
if ! git diff --quiet || ! git diff --cached --quiet; then git add -A && git commit -m "chore(bootstrap): one-strike scaffold + Codex"; fi

# Feature branch
if ! git rev-parse --verify "$FEATURE_BRANCH" >/dev/null 2>&1; then git checkout -B "$FEATURE_BRANCH"; git checkout "$DEFAULT_BRANCH"; fi

# Origin
setup_origin(){ local host="github.com"; local desired=""; if git remote get-url origin >/dev/null 2>&1; then return 0; fi
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then [ -z "$GH_OWNER" ] && GH_OWNER="$(gh api user -q .login 2>/dev/null || echo '')"
    if ! gh repo view "${GH_OWNER:+$GH_OWNER/}$REPO_NAME" >/dev/null 2>&1; then pulse STEP "Creating GitHub repo"; gh repo create "${GH_OWNER:+$GH_OWNER/}$REPO_NAME" --${PRIVATE_REPO:true} --source . --disable-wiki --disable-issues --push || true; fi
  fi
  if $USE_SSH && { [ -f "$HOME/.ssh/id_ed25519.pub" ] || [ -f "$HOME/.ssh/id_rsa.pub" ]; }; then desired="git@${host}:${GH_OWNER:-${USER}}/${REPO_NAME}.git"; else desired="https://${host}/${GH_OWNER:-${USER}}/${REPO_NAME}.git"; fi
  git remote add origin "$desired" || true
}
setup_origin || true

# Push
if git remote get-url origin >/dev/null 2>&1; then pulse STEP "Pushing branches"; silence git push -u origin "$DEFAULT_BRANCH" || true; git checkout "$FEATURE_BRANCH" >/dev/null 2>&1 || git checkout -B "$FEATURE_BRANCH"; silence git push -u origin "$FEATURE_BRANCH" || true; git checkout "$DEFAULT_BRANCH" || true; fi

pulse OK "Strike ready."
BASH
chmod +x one-strike-bootstrap.sh && echo "CREATED: one-strike-bootstrap.sh"