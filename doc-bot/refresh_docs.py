# Sandbox Doc Bot - Notion DB → documents.json + 파일 캐시 자동 동기화
#
# 동작:
#   1. Notion "자주찾는 공용 문서" DB 전체 조회
#   2. documents.json에 없는 신규 문서 자동 추가 (aliases 자동 생성)
#   3. 기존 문서 파일 최신화 (Notion 파일명 → knowledge/files/ 저장)
#   4. documents.json 업데이트
#
# 실행: python refresh_docs.py

import json
import os
import re
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DOCUMENTS_PATH = Path("knowledge/documents.json")
FILES_DIR = Path("knowledge/files")

# Notion 자주찾는 공용 문서 DB ID
CHILD_DB_ID = "30229436cbac8110874ae5443858295f"

NOTION_API = "https://api.notion.com/v1"
NOTION_VER = "2022-06-28"


def notion_headers():
    token = os.environ.get("NOTION_TOKEN", "")
    if not token:
        raise ValueError("❌ .env에 NOTION_TOKEN이 없습니다.")
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VER,
        "Content-Type": "application/json",
    }


def query_all_pages(db_id: str) -> list:
    """DB 전체 페이지 수집 (페이지네이션 자동 처리)."""
    pages, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(f"{NOTION_API}/databases/{db_id}/query",
                          headers=notion_headers(), json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return pages


def get_prop_text(props: dict, key: str) -> str:
    """title / rich_text 속성에서 텍스트 추출."""
    prop = props.get(key, {})
    items = prop.get("title") or prop.get("rich_text") or []
    return "".join(t.get("plain_text", "") for t in items).strip()


def get_file_info(props: dict) -> tuple[str, str]:
    """'문서 파일' 속성에서 (파일명, URL) 반환. 없으면 ('', '')."""
    files = props.get("문서 파일", {}).get("files", [])
    if not files:
        return "", ""
    f = files[0]
    name = f.get("name", "")
    if f["type"] == "file":
        url = f["file"]["url"]
    elif f["type"] == "external":
        url = f["external"]["url"]
    else:
        return "", ""
    return name, url


def make_aliases(name: str) -> list:
    """문서명으로 기본 aliases 자동 생성."""
    aliases = [name]
    # 공백 없는 버전
    no_space = name.replace(" ", "")
    if no_space != name:
        aliases.append(no_space)
    # 괄호 제거
    clean = re.sub(r"[()（）]", "", name).strip()
    if clean not in aliases:
        aliases.append(clean)
    # 접미사 제거 (연도, 분기 패턴)
    short = re.sub(r"\s*(20\d{2}|\d+Q|PPT/PDF|pdf|pptx)\s*", " ", name, flags=re.IGNORECASE).strip()
    if short and short not in aliases:
        aliases.append(short)
    return list(dict.fromkeys(aliases))  # 중복 제거, 순서 유지


def safe_filename(doc_name: str, notion_filename: str) -> str:
    """저장할 로컬 파일명 결정: 문서명 기반 + Notion 확장자."""
    ext = Path(notion_filename).suffix if notion_filename else ".pdf"
    # 파일명에 사용 불가한 문자 제거
    base = re.sub(r'[\\/:*?"<>|]', "", doc_name)
    return base + ext


def download_file(url: str, save_path: Path) -> int:
    """파일 다운로드. 성공 시 파일 크기(KB) 반환."""
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    save_path.write_bytes(r.content)
    return len(r.content) // 1024


def main():
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    # 기존 documents.json 로드
    if DOCUMENTS_PATH.exists():
        with open(DOCUMENTS_PATH, encoding="utf-8") as f:
            documents = json.load(f)
    else:
        documents = []

    # 기존 page_id 인덱스
    existing_ids = {doc.get("notion_page_id", ""): i for i, doc in enumerate(documents)}

    print("=" * 55)
    print("Notion DB 동기화 시작")
    print("=" * 55)

    pages = query_all_pages(CHILD_DB_ID)
    print(f"Notion DB: {len(pages)}개 페이지 조회")
    print()

    added, updated, skipped, failed = 0, 0, 0, 0

    for page in pages:
        page_id = page["id"].replace("-", "")
        props = page["properties"]
        notion_url = page.get("url", "")

        # 문서명 추출
        doc_name = get_prop_text(props, "문서명")
        if not doc_name:
            doc_name = get_prop_text(props, "페이지") or get_prop_text(props, "이름")
        if not doc_name:
            print(f"  ⏭  page_id={page_id}: 문서명 없음, 건너뜀")
            skipped += 1
            continue

        notion_fname, file_url = get_file_info(props)

        # URL만 있는 경우 (오피스 가이드 등)
        if not file_url and notion_fname.startswith("http"):
            file_url = notion_fname
            notion_fname = ""

        # 로컬 파일명 결정
        local_file = safe_filename(doc_name, notion_fname) if notion_fname and not notion_fname.startswith("http") else ""

        # ── 신규 문서 추가 ──────────────────────────────────────────
        if page_id not in existing_ids:
            new_doc = {
                "name": doc_name,
                "aliases": make_aliases(doc_name),
                "notion_url": notion_url,
                "notion_page_id": page_id,
                "local_file": local_file,
                "description": doc_name,
            }
            documents.append(new_doc)
            existing_ids[page_id] = len(documents) - 1
            print(f"  ➕ 신규: {doc_name}")
            added += 1
        else:
            # 기존 문서 — notion_url / local_file 업데이트
            idx = existing_ids[page_id]
            documents[idx]["notion_url"] = notion_url
            if local_file:
                documents[idx]["local_file"] = local_file

        # ── 파일 다운로드 ───────────────────────────────────────────
        if not file_url or not local_file:
            if not file_url:
                print(f"  ⏭  {doc_name}: 첨부 파일 없음")
            skipped += 1
            continue

        save_path = FILES_DIR / local_file
        try:
            size_kb = download_file(file_url, save_path)
            print(f"  ✅ {doc_name}: {local_file} ({size_kb}KB)")
            updated += 1
        except Exception as e:
            print(f"  ❌ {doc_name}: 다운로드 실패 — {e}")
            failed += 1

    # documents.json 저장
    with open(DOCUMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 55)
    print(f"✅ 완료: 신규 {added}개 | 파일 갱신 {updated}개 | 건너뜀 {skipped}개 | 실패 {failed}개")
    print(f"📝 documents.json 업데이트 완료 ({len(documents)}개 항목)")
    print("=" * 55)


if __name__ == "__main__":
    main()
