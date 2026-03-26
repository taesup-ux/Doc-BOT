# Sandbox Doc Bot - 설정 상수
# 문서 요청 감지 기능 전용. 사무 업무·주간 집계 기능 없음.

import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

KST = ZoneInfo("Asia/Seoul")

# ─── 채널 ID ─────────────────────────────────────────────────────────────────────
DOC_CHANNEL = os.environ["HELPDESK_CHANNEL"]
TEAM_CHANNEL = os.environ["TEAM_CHANNEL"]

# ─── 근무 시간 ────────────────────────────────────────────────────────────────────
WORK_START = 9
WORK_END = 19

# ─── 제외 키워드 (물리 인감 요청 → 봇 처리 불필요) ──────────────────────────────
EXCLUDE_KEYWORDS = ["인감증명", "인감 도장", "인감확인", "인감 신청", "인감 발급"]

# ─── 테스트 모드 ──────────────────────────────────────────────────────────────────
# True : 팀 채널에 미리보기 카드 발송 (확인 후 샌드박스-문서자료실 전송)
# False: 샌드박스-문서자료실에 즉시 응답
TEST_MODE = os.environ.get("TEST_MODE", "true").lower() == "true"
