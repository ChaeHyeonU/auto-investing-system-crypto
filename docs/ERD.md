# ERD (MVP)

## 개요
아래 ERD는 구독형 AI 투자 자동화 시스템의 MVP 기준 데이터 모델이다. 핵심은 `user -> subscription -> exchange_account -> strategy -> order/fill` 흐름과 리스크 이벤트 추적이다.

```mermaid
erDiagram
  USERS ||--o{ SUBSCRIPTIONS : "owns"
  USERS ||--o{ EXCHANGE_ACCOUNTS : "connects"
  USERS ||--o{ STRATEGIES : "configures"
  USERS ||--o{ ALERT_CHANNELS : "receives"
  USERS ||--o{ DAILY_REPORTS : "gets"

  SUBSCRIPTIONS ||--o{ BILLING_INVOICES : "generates"
  SUBSCRIPTIONS ||--o{ BILLING_WEBHOOK_EVENTS : "sync_events"
  EXCHANGE_ACCOUNTS ||--o{ ORDERS : "routes"
  STRATEGIES ||--o{ ORDERS : "creates"
  ORDERS ||--o{ FILLS : "executes"
  STRATEGIES ||--o{ RISK_EVENTS : "produces"
  STRATEGIES ||--o{ SIGNAL_SNAPSHOTS : "uses"

  USERS {
    uuid id PK
    string email UK
    string password_hash
    string role
    boolean mfa_enabled
    string status
    timestamptz created_at
    timestamptz updated_at
  }

  SUBSCRIPTIONS {
    uuid id PK
    uuid user_id FK
    string plan
    string status
    timestamptz current_period_start
    timestamptz current_period_end
    string stripe_customer_id
    string stripe_subscription_id
    timestamptz created_at
  }

  BILLING_INVOICES {
    uuid id PK
    uuid subscription_id FK
    string stripe_invoice_id
    numeric amount_usd
    string currency
    string status
    timestamptz paid_at
    timestamptz created_at
  }

  BILLING_WEBHOOK_EVENTS {
    uuid id PK
    string stripe_event_id UK
    string event_type
    string processing_result
    timestamptz processed_at
  }

  EXCHANGE_ACCOUNTS {
    uuid id PK
    uuid user_id FK
    string venue
    string api_key_encrypted
    string api_secret_encrypted
    string passphrase_encrypted
    string key_version
    string status
    timestamptz last_verified_at
    timestamptz created_at
  }

  STRATEGIES {
    uuid id PK
    uuid user_id FK
    uuid exchange_account_id FK
    string profile
    string mode
    jsonb risk_limits
    jsonb allocation_rules
    string status
    timestamptz activated_at
    timestamptz created_at
    timestamptz updated_at
  }

  SIGNAL_SNAPSHOTS {
    uuid id PK
    uuid strategy_id FK
    string symbol
    string signal
    numeric score
    jsonb feature_digest
    timestamptz generated_at
  }

  ORDERS {
    uuid id PK
    uuid strategy_id FK
    uuid exchange_account_id FK
    string venue
    string symbol
    string side
    string type
    numeric quantity
    numeric limit_price
    string status
    string idempotency_key UK
    string exchange_order_id
    timestamptz submitted_at
    timestamptz updated_at
  }

  FILLS {
    uuid id PK
    uuid order_id FK
    numeric fill_qty
    numeric fill_price
    numeric fee
    string fee_asset
    timestamptz filled_at
  }

  RISK_EVENTS {
    uuid id PK
    uuid strategy_id FK
    string event_type
    string severity
    jsonb payload
    boolean blocked_order
    timestamptz occurred_at
  }

  ALERT_CHANNELS {
    uuid id PK
    uuid user_id FK
    string channel_type
    string destination
    boolean enabled
    timestamptz created_at
  }

  DAILY_REPORTS {
    uuid id PK
    uuid user_id FK
    date report_date
    numeric net_pnl
    numeric return_pct
    numeric sharpe
    numeric max_drawdown
    string storage_url
    timestamptz created_at
  }
```

## 설계 메모
1. `strategies.risk_limits`는 일손실/포지션/변동성 제한을 JSON으로 저장해 초기 유연성을 확보한다.
2. `orders.idempotency_key`를 unique로 강제해 중복 주문을 차단한다.
3. 민감 정보(API 키)는 암호화된 문자열만 저장하고 평문은 저장하지 않는다.
