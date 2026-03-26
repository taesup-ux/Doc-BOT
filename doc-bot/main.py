# Sandbox Doc Bot - 문서 ?�청 ?�동 ?�내 �?#
# ??��: Slack ?�프?�스??채널?�서 문서/?�류 ?�청 ?�워?��? 감�???#       Notion ?�료??링크 ?�는 로컬 ?�일???�레?�로 바로 ?�송.
#
# Claude API ?�음 ???�수 ?�워??매칭?�로 ?�작 (빠르�?가벼�?)
#
# ?�행: python main.py
# ?�전 조건:
#   1. api.slack.com/apps ?�서 Doc Bot ???�성
#   2. .env??DOC_BOT_TOKEN, SLACK_SIGNING_SECRET ?�력
#   3. ?�프?�스??채널??�?초�?: /invite @Sandbox Doc Bot
#   4. python refresh_docs.py ?�행 ??로컬 ?�일 캐시 ?�성 (?�택)

import logging
import os
import re
import sys
from collections import OrderedDict
from datetime import datetime

import requests
from dotenv import load_dotenv
from slack_bolt import App

logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

load_dotenv()

from config import (
    HELPDESK_CHANNEL,
    WORK_START, WORK_END, KST,
    EXCLUDE_KEYWORDS,
)
import agents.doc_request_agent as doc_request

# ?�?�?� Slack Bolt ??초기??(HTTP 모드) ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
app = App(
    token=os.environ["DOC_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
)

# ?�?�?� 중복 처리 방�? (최근 1000건만 ?��?, O(1) 조회) ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
_processed_ts: OrderedDict = OrderedDict()
_PROCESSED_MAX = 1000


# ?�?�?� ?�틸 ?�수 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
def is_work_hours() -> bool:
    now = datetime.now(KST)
    return WORK_START <= now.hour < WORK_END


def _is_excluded(text: str) -> bool:
    """?�감 ??물리 ?�???�수 문의 ??�?처리 ?�외."""
    return any(kw in text for kw in EXCLUDE_KEYWORDS)


# ?�?�?� ?�벤?? 메시지 ?�들???�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
@app.event("message")
def handle_message(event, client, logger):
    message = event
    # 삭제·수정·봇 메시지 등 처리 불필요한 subtype 제외
    subtype = event.get("subtype", "")
    if subtype in ("message_deleted", "message_changed", "bot_message",
                   "channel_join", "channel_leave", "channel_topic"):
        return
    channel = message.get("channel")

    # ?�?� ?�프?�스??채널�??�하 처리 ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    if channel != HELPDESK_CHANNEL:
        return

    # 봇·시?�템 메시지 ?�외
    if message.get("bot_id"):
        return

    ts = message.get("ts", "")
    thread_ts = message.get("thread_ts") or ts

    if ts in _processed_ts:
        return
    _processed_ts[ts] = None
    if len(_processed_ts) > _PROCESSED_MAX:
        _processed_ts.popitem(last=False)

    text = message.get("text", "").strip()
    if not text or len(text) < 2:
        return

    if _is_excluded(text):
        logger.info(f"[filter] ?�외 ?�워??감�?, ?�킵: ts={ts}")
        return

    if not is_work_hours():
        return

    # ?�?� 문서 ?�청 감�? (?�중) ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
    doc_list = doc_request.detect_document_requests(text)
    if not doc_list:
        return

    # 감�? �??�내 메시지
    try:
        client.chat_postMessage(
            channel=HELPDESK_CHANNEL,
            thread_ts=thread_ts,
            text="?�청 ?�수?�습?�다! ?�류 찾아?�릴게요 ?��",
        )
    except Exception:
        pass

    for doc_info in doc_list:
        is_group = doc_info.get("is_group", False)
        has_file = False if is_group else doc_request.has_local_file(doc_info)
        can_download = not is_group and not has_file and doc_request.has_downloadable_url(doc_info)
        reply_text = doc_request.build_reply(doc_info, has_file=has_file)

        try:
            client.chat_postMessage(
                channel=HELPDESK_CHANNEL,
                thread_ts=thread_ts,
                text=reply_text,
            )
            if has_file:
                doc_request.upload_local_file(client, HELPDESK_CHANNEL, thread_ts, doc_info)
            elif can_download:
                doc_request.download_and_upload_url(client, HELPDESK_CHANNEL, thread_ts, doc_info)
            logger.info(f"[doc_request] ?��? ?�료: {doc_info['name']}, ts={ts}")
        except Exception as e:
            logger.error(f"[doc_request] ?�패: {e}")


# ?�?�?� ?�작 ?�태?��? ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
def startup_check() -> bool:
    """�??�작 ???�수 ?�태 ?��?. ?�패 ??False 반환."""
    import requests
    from pathlib import Path

    token = os.environ.get("DOC_BOT_TOKEN", "")
    h = {"Authorization": f"Bearer {token}"}
    ok = True

    print("?�?� ?�태?��? ?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�")

    # 1. ?�큰 ?�효??    r = requests.post("https://slack.com/api/auth.test", headers=h, timeout=10)
    d = r.json()
    if d.get("ok"):
        print(f"  ???�큰  : {d.get('user')} / {d.get('team')}")
    else:
        print(f"  ???�큰 ?�류: {d.get('error')}")
        ok = False

    # 2. ?�코???�인
    scopes = r.headers.get("X-OAuth-Scopes", "")
    required = {"chat:write", "files:write", "groups:history"}
    missing = required - set(s.strip() for s in scopes.split(","))
    if not missing:
        print(f"  ???�코??: {scopes}")
    else:
        print(f"  ???�코???�락: {missing}")
        ok = False

    # 3. 채널 ?�스??가???��?
    r2 = requests.post(
        "https://slack.com/api/conversations.info",
        headers=h,
        data={"channel": HELPDESK_CHANNEL},
        timeout=10,
    )
    d2 = r2.json()
    if d2.get("ok") or d2.get("error") in ("missing_scope",):
        print(f"  ??채널   : {HELPDESK_CHANNEL}")
    elif d2.get("error") == "channel_not_found":
        print(f"  ??채널 ?�음: {HELPDESK_CHANNEL}")
        ok = False
    else:
        print(f"  ??채널   : {HELPDESK_CHANNEL} ({d2.get('error','ok')})")

    # 4. 로컬 ?�일 캐시 ?�인
    files_dir = Path(__file__).parent / "knowledge" / "files"
    file_count = len(list(files_dir.glob("*"))) if files_dir.exists() else 0
    doc_count = len(doc_request._load_documents())
    print(f"  ??문서   : documents.json {doc_count}�?/ 캐시 ?�일 {file_count}�?)

    # 5. Signing Secret 존재 ?�인
    if os.environ.get("SLACK_SIGNING_SECRET"):
        print(f"  ??Signing Secret: ?�정??)
    else:
        print(f"  ??SLACK_SIGNING_SECRET 미설??)
        ok = False

    print("?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�")
    if not ok:
        print("  ???�태?��? ?�패 ??????�� ?�인 ???�시?�하?�요")

    return ok


# ?�?�?� 진입???�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�?�
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))

    print("=" * 50)
    print("Sandbox Doc Bot ?�작")
    print(f"  ?�프?�스??채널: {HELPDESK_CHANNEL}")
    print(f"  ?�트: {port}")
    print("  모드: HTTP ???�워??감�? ???�레??즉시 ?��? + ?�일 ?�송")
    print("=" * 50)

    if not startup_check():
        raise SystemExit(1)

    app.start(port=port)


