# Sandbox Automation

샌드박스네트워크 GA팀 Slack 자동화 봇 모노레포.
Railway 단일 프로젝트에서 서비스별로 독립 배포.

## 서비스 목록

| 서비스 | 폴더 | 상태 | 설명 |
|--------|------|------|------|
| Doc Bot | `doc-bot/` | 🟢 운영 중 | 헬프데스크 문서 요청 자동 안내 |
| Helpdesk Bot | `helpdesk-bot/` | 🔜 예정 | - |
| GA Automation Bot | `ga-bot/` | 🔜 예정 | - |

## Railway 배포 구조

```
Railway 프로젝트: sandbox-automation
  ├── Service: doc-bot       (Root Directory = doc-bot/)
  ├── Service: helpdesk-bot  (Root Directory = helpdesk-bot/)
  └── Service: ga-bot        (Root Directory = ga-bot/)
```

## 새 봇 추가 방법

1. 새 폴더 생성: `새봇이름/`
2. 해당 폴더에 `main.py`, `requirements.txt`, `Procfile` 작성
3. Railway 프로젝트에서 New Service → GitHub Repo → Root Directory 지정
4. 환경변수 설정 후 배포

## 환경변수 관리

각 서비스별 `.env.example` 참고. 실제 값은 Railway 대시보드에서 설정.
