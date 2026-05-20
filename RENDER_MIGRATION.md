# Render 이관 가이드 (Doc-BOT)

Railway → Render 마이그레이션. `render.yaml`로 IaC 정의.

## 사용자 액션 (Render 대시보드)

1. https://dashboard.render.com 로그인 (GitHub OAuth)
2. **New +** → **Blueprint**
3. GitHub 레포 연결: `taesup-ux/Doc-BOT` (또는 회사 레포)
4. 브랜치 선택: `main` (이 PR 머지 후) 또는 `feat/render-migration` (테스트)
5. Render가 `render.yaml` 자동 감지 → 서비스 1개 (`sandbox-doc-bot`) 생성 제안
6. 환경변수 입력 (`sync: false` 키는 Render UI에서 직접 입력):

| 키 | 출처 |
|---|---|
| `DOC_BOT_TOKEN` | Slack 앱 → Bot User OAuth Token (`xoxb-...`) |
| `SLACK_SIGNING_SECRET` | Slack 앱 → Basic Information → Signing Secret |
| `NOTION_TOKEN` | Notion Integration Token (`secret_...`) |
| `HELPDESK_CHANNEL` | 운영 채널 ID (현재 `C03E08UCZS6` 추정) |
| `TEAM_CHANNEL` | 팀 채널 ID (현재 `C08823F52U8` 추정) |
| `TEST_MODE` | render.yaml에 `false` 고정 |

값은 기존 Railway 대시보드 또는 로컬 `.env`에서 복사.

7. **Apply Blueprint** → 빌드/배포 시작
8. 배포 URL 확보 (예: `https://sandbox-doc-bot.onrender.com`)

## Slack 앱 재설정 (HTTP 엔드포인트 변경)

Railway URL → Render URL 교체:

- https://api.slack.com/apps → Doc Bot 앱 → **Event Subscriptions**
- Request URL: `https://sandbox-doc-bot.onrender.com/slack/events`
- (slack-bolt 기본 경로)

## 서비스 플랜

`render.yaml`에 `plan: starter` ($7/mo) 설정.

이유: free 플랜은 15분 idle 후 sleep → Slack 이벤트 누락 위험. Slack 봇은 always-on 필요.

free로 일단 테스트하려면 `plan: starter` → `plan: free`로 변경 후 푸시.

## 확장 (ga-bot, helpdesk-bot)

현재 `ga-bot/`, `helpdesk-bot/` 폴더는 빈 상태. 코드 추가 시 `render.yaml`에 서비스 블록 복제해서 추가:

```yaml
  - type: web
    name: sandbox-helpdesk-bot
    runtime: docker
    region: singapore
    plan: starter
    branch: main
    dockerfilePath: ./helpdesk-bot/Dockerfile
    dockerContext: ./helpdesk-bot
    autoDeploy: true
    envVars:
      - ...
```
