# Sprint 1 GitHub Issues (Ready-to-create)

## 사용 방법
아래 이슈는 Sprint 1(주 1-2) 기준으로 바로 GitHub Issue에 등록 가능한 수준으로 작성했다.  
라벨 권장 세트: `type:feature`, `type:infra`, `type:bug`, `area:backend`, `area:frontend`, `area:platform`, `priority:P0/P1`.

## 이슈 목록 요약
| No | Title | Labels | Priority | Estimate | Depends On |
|---|---|---|---|---|---|
| 1 | [BE] Auth: 회원가입 API 구현 | type:feature, area:backend | P0 | 3pt | - |
| 2 | [BE] Auth: 로그인/토큰 발급 API 구현 | type:feature, area:backend | P0 | 3pt | 1 |
| 3 | [BE] Auth: 2FA(TOTP) 검증 플로우 구현 | type:feature, area:backend | P1 | 3pt | 2 |
| 4 | [BE] Billing: Stripe Checkout Session API 구현 | type:feature, area:backend | P0 | 2pt | 2 |
| 5 | [BE] Billing: Stripe Webhook 구독 상태 동기화 | type:feature, area:backend | P0 | 3pt | 4 |
| 6 | [BE] Subscription Gate: 플랜 기반 권한 미들웨어 | type:feature, area:backend | P0 | 2pt | 5 |
| 7 | [Platform] API Gateway 기본 라우팅/헬스체크 구성 | type:infra, area:platform | P0 | 2pt | - |
| 8 | [Platform] 공통 에러 코드/응답 포맷 표준화 | type:infra, area:platform | P0 | 2pt | 7 |
| 9 | [Platform] 구조화 로깅 + Trace ID 미들웨어 | type:infra, area:platform | P0 | 2pt | 7 |
| 10 | [DB] 초기 스키마 마이그레이션(users/subscriptions) | type:infra, area:backend | P0 | 3pt | - |
| 11 | [FE] Dashboard Shell: 레이아웃/네비/플랜 배지 UI | type:feature, area:frontend | P1 | 3pt | 2, 6 |
| 12 | [QA] 온보딩 E2E: 가입→결제→권한반영 시나리오 | type:infra, area:platform | P0 | 3pt | 1~11 |

---

## 1) [BE] Auth: 회원가입 API 구현
### Description
이메일/비밀번호 기반 회원가입 API를 구현한다. 비밀번호는 강한 해시로 저장하고, 중복 이메일은 차단한다.

### Acceptance Criteria
- `POST /v1/auth/register`가 `201`로 사용자 생성
- 중복 이메일은 `409 CONFLICT` 반환
- 비밀번호 평문 저장 금지
- 단위 테스트 포함

### Checklist
- [ ] Request/Response 스키마 구현
- [ ] 비밀번호 해시 유틸 적용
- [ ] 중복 체크 + DB unique 제약
- [ ] 테스트 추가

### Labels
`type:feature`, `area:backend`, `priority:P0`

## 2) [BE] Auth: 로그인/토큰 발급 API 구현
### Description
로그인 성공 시 JWT access/refresh token을 발급한다.

### Acceptance Criteria
- `POST /v1/auth/login` 성공 시 토큰 반환
- 잘못된 자격증명은 `401`
- refresh token 저장 및 회전 정책 적용
- 테스트 포함

### Labels
`type:feature`, `area:backend`, `priority:P0`

## 3) [BE] Auth: 2FA(TOTP) 검증 플로우 구현
### Description
TOTP 기반 2FA 검증 API를 추가한다.

### Acceptance Criteria
- `POST /v1/auth/mfa/verify` 구현
- 유효/무효 코드 검증
- 실패 횟수 제한
- 감사로그 기록

### Labels
`type:feature`, `area:backend`, `priority:P1`

## 4) [BE] Billing: Stripe Checkout Session API 구현
### Description
요금제 선택 시 Stripe Checkout URL을 생성해 반환한다.

### Acceptance Criteria
- `POST /v1/billing/checkout-session` 구현
- 플랜 파라미터 검증
- Stripe 오류 시 표준 에러 코드 반환

### Labels
`type:feature`, `area:backend`, `priority:P0`

## 5) [BE] Billing: Stripe Webhook 구독 상태 동기화
### Description
결제 이벤트를 수신해 구독 상태를 DB와 동기화한다.

### Acceptance Criteria
- Webhook 서명 검증 통과 시에만 처리
- `active/past_due/canceled` 상태 반영
- 이벤트 중복 수신에도 멱등 처리

### Labels
`type:feature`, `area:backend`, `priority:P0`

## 6) [BE] Subscription Gate: 플랜 기반 권한 미들웨어
### Description
API 접근을 구독 플랜에 따라 제한한다.

### Acceptance Criteria
- 플랜 미충족 시 `403` 반환
- 보호 엔드포인트 지정 가능
- 테스트 포함

### Labels
`type:feature`, `area:backend`, `priority:P0`

## 7) [Platform] API Gateway 기본 라우팅/헬스체크 구성
### Description
API gateway 엔트리 포인트와 라우팅 기본구조를 만든다.

### Acceptance Criteria
- `/healthz` 응답
- `/v1/*` 라우팅 구조 정리
- 로컬 개발 실행 가이드 포함

### Labels
`type:infra`, `area:platform`, `priority:P0`

## 8) [Platform] 공통 에러 코드/응답 포맷 표준화
### Description
서비스 공통 에러 응답 포맷과 코드 체계를 정의하고 적용한다.

### Acceptance Criteria
- `{code, message, details}` 포맷 통일
- 인증/검증/서버 에러 코드 표준 문서화
- API 테스트 반영

### Labels
`type:infra`, `area:platform`, `priority:P0`

## 9) [Platform] 구조화 로깅 + Trace ID 미들웨어
### Description
요청 단위 trace ID를 생성하고 구조화 로그(JSON)로 남긴다.

### Acceptance Criteria
- 모든 요청 로그에 trace ID 포함
- 에러 로그에 스택/문맥 필드 포함
- 민감정보 마스킹

### Labels
`type:infra`, `area:platform`, `priority:P0`

## 10) [DB] 초기 스키마 마이그레이션(users/subscriptions)
### Description
MVP 필수 테이블(users, subscriptions, invoices)의 초기 마이그레이션을 추가한다.

### Acceptance Criteria
- 업/다운 마이그레이션 동작
- unique/index/fk 반영
- 로컬 DB에서 재현 가능

### Labels
`type:infra`, `area:backend`, `priority:P0`

## 11) [FE] Dashboard Shell: 레이아웃/네비/플랜 배지 UI
### Description
로그인 후 진입하는 대시보드 기본 레이아웃과 플랜 표시 UI를 구현한다.

### Acceptance Criteria
- 반응형 레이아웃(모바일/데스크톱)
- 사용자/플랜 상태 표시
- API 연결 전 더미 상태 관리

### Labels
`type:feature`, `area:frontend`, `priority:P1`

## 12) [QA] 온보딩 E2E: 가입→결제→권한반영 시나리오
### Description
핵심 온보딩 흐름의 E2E 테스트를 추가해 출시 전 회귀를 방지한다.

### Acceptance Criteria
- 가입 -> 로그인 -> 결제 완료 -> 권한 반영 시나리오 통과
- 실패 케이스(중복 가입, 결제 실패) 포함
- CI에서 자동 실행

### Labels
`type:infra`, `area:platform`, `priority:P0`

---

## 권장 Milestone
- Milestone: `MVP-Sprint-1`
- Due date: 스프린트 시작일 + 14일

## 권장 순서
1. 이슈 `1, 7, 10` 시작
2. 이슈 `2, 4, 8, 9` 병렬 진행
3. 이슈 `5, 6, 11` 진행
4. 이슈 `12`로 통합 검증

