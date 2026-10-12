#!/usr/bin/env bash
# Kiểm tra âm N1–N19 cho scripts/ci.sh (T-002, Implementation_Plan §11.5).
# Mỗi ca: sao chép repo (file được theo dõi + chưa theo dõi, bỏ file bị ignore) vào thư mục tạm, tiêm một lỗi,
# chạy scripts/ci.sh và yêu cầu: mã thoát khác 0, dừng đúng bước, log có dấu hiệu lỗi mong đợi.
# Không sửa repo gốc. Cần mạng cho npm/uv và cho N19 (quét lỗ hổng).
#
# Tùy chọn:
#   AIEOS_N17_NODE_DIR   thư mục chứa node khác major 22 (vd. Node 24) cho N17a; không đặt → N17a NOT RUN
#   AIEOS_N17_PYTHON     phiên bản Python sai cho N17b (mặc định 3.10)
#   N_ONLY="N1 N4"       chỉ chạy các ca liệt kê
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
LOGS="$WORK/logs"
mkdir -p "$LOGS"
FAILED=0

fresh_copy() {
  local dest="$WORK/repo"
  rm -rf "$dest"
  mkdir -p "$dest"
  (cd "$ROOT" && git ls-files -co --exclude-standard -z | xargs -0 cp --parents -t "$dest")
  echo "$dest"
}

write() { mkdir -p "$(dirname "$1")" && printf '%s' "$2" > "$1"; }

# run_case <ID> <bước mong đợi> <mẫu grep trong log> <hàm tiêm lỗi> [VAR=giá_trị ...]
run_case() {
  local id="$1" expect="$2" pattern="$3" inject="$4"
  shift 4
  if [ -n "${N_ONLY:-}" ] && [[ " $N_ONLY " != *" $id "* ]]; then return; fi
  local repo log rc got
  repo="$(fresh_copy)"
  log="$LOGS/$id.log"
  (cd "$repo" && "$inject") > "$log.inject" 2>&1 || {
    echo "$id FAIL — không tiêm được lỗi (xem $log.inject)"
    FAILED=1
    return
  }
  env "$@" "$repo/scripts/ci.sh" > "$log" 2>&1
  rc=$?
  got="$(grep -oE 'CI FAILED step=[a-z-]+' "$log" | sed 's/CI FAILED step=//')"
  if [ "$rc" -ne 0 ] && [ "$got" = "$expect" ] && grep -qE "$pattern" "$log"; then
    echo "$id PASS — ci.sh rc=$rc tại bước $got; khớp /$pattern/"
  else
    echo "$id FAIL — rc=$rc, bước='${got:-không có}', mong đợi '$expect' và /$pattern/ (log: $log)"
    FAILED=1
  fi
}

B=backend/src/aieos
n1() { write $B/audit/n1.py $'import os\n'; }
n2() { write $B/audit/n2.py $'x=1\n'; }
n3() { write $B/audit/n3.py $'def f() -> int:\n    return "a"\n'; }
n4() {
  write $B/finance/api.py $'"""API công khai."""\n'
  write $B/ai/n4.py $'from aieos.finance import api\n\nNAME = api.__name__\n'
}
n5() { write $B/providers/n5.py $'from aieos import access\n\nNAME = access.__name__\n'; }
n6() {
  write $B/gateway/api.py $'"""API công khai."""\n'
  write $B/finance/n6.py $'from aieos.gateway import api\n\nNAME = api.__name__\n'
}
n7() {
  write $B/finance/models.py $'"""Model nội bộ."""\n'
  write $B/goals/n7.py $'from aieos.finance import models\n\nNAME = models.__name__\n'
}
n8() { write backend/tests/test_n8.py $'def test_n8() -> None:\n    assert 1 + 1 == 3\n'; }
n9() { :; }
n10() {
  write frontend/src/n10.tsx $'import { useState } from "react";\n\nexport function N10({ flag }: { flag: boolean }) {\n  if (flag) {\n    useState(0);\n  }\n  return null;\n}\n'
}
n11() {
  write frontend/src/n11.ts $'async function load(): Promise<number> {\n  return Promise.resolve(1);\n}\n\nexport function run(): void {\n  load();\n}\n'
}
n12() { write frontend/src/n12.ts $'export const n12 = {a:1};\n'; }
n13() { write frontend/src/n13.ts $'export const n13: number = "a";\n'; }
n14() {
  write frontend/src/n14.test.ts $'import { expect, it } from "vitest";\n\nit("n14", () => {\n  expect(1 + 1).toBe(3);\n});\n'
}
n15() { sed -i 's/^dependencies = \[\]$/dependencies = ["idna==3.10"]/' backend/pyproject.toml && grep -q idna backend/pyproject.toml; }
n16() {
  node -e 'const f="frontend/package.json",fs=require("fs"),p=JSON.parse(fs.readFileSync(f));p.dependencies["left-pad"]="1.3.0";fs.writeFileSync(f,JSON.stringify(p,null,2)+"\n")'
}
n17() { :; }
n18() { printf '\n[liên kết hỏng](khong-ton-tai.md)\n' >> docs/Implementation_Handoff.md; }
n19a() { (cd backend && uv add --quiet --dev "jinja2==2.10"); }
n19b() { (cd frontend && npm install --silent --no-audit --no-fund --save-exact lodash@4.17.20); }

echo "Thư mục tạm: $WORK"
run_case N1 ruff-check 'F401' n1
run_case N2 ruff-format 'would be reformatted' n2
run_case N3 mypy 'Incompatible return value' n3
run_case N4 import-contracts 'C2 ai-jobs-capture khong import domain BROKEN' n4
run_case N5 import-contracts 'C1 providers khong import module aieos khac BROKEN' n5
run_case N6 import-contracts 'C3 domain khong import gateway BROKEN' n6
run_case N7 pytest 'test_source_tree_respects_c4' n7
run_case N8 pytest 'test_n8' n8
run_case N9 pytest 'AIEOS_REQUIRE_DB=1 nhưng thiếu AIEOS_TEST_DATABASE_URL' n9 AIEOS_REQUIRE_DB=1 AIEOS_TEST_DATABASE_URL=
run_case N10 eslint 'react-hooks/rules-of-hooks' n10
run_case N11 eslint '@typescript-eslint/no-floating-promises' n11
run_case N12 prettier 'Code style issues' n12
run_case N13 tsc 'TS2322' n13
run_case N14 vitest 'n14' n14
run_case N15 backend-lock 'lockfile' n15
run_case N16 frontend-install 'in sync' n16
if [ -n "${AIEOS_N17_NODE_DIR:-}" ]; then
  run_case N17a runtime 'Cần Node' n17 PATH="$AIEOS_N17_NODE_DIR:$PATH"
else
  echo "N17a NOT RUN — chưa đặt AIEOS_N17_NODE_DIR"
fi
run_case N17b runtime 'Cần Python|No interpreter found|requires-python' n17 UV_PYTHON="${AIEOS_N17_PYTHON:-3.10}"
run_case N18 docs 'khong-ton-tai.md' n18
run_case N19a audit-python 'jinja2' n19a
run_case N19b audit-npm 'lodash' n19b

if [ "$FAILED" -ne 0 ]; then
  echo "NEGATIVE CHECKS FAILED (log: $LOGS)"
  exit 1
fi
rm -rf "$WORK/repo"
echo "NEGATIVE CHECKS OK (log: $LOGS)"
