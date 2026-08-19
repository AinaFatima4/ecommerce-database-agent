# 🛍️ Ecommerce Database Agent

An **agentic AI chatbot** that answers natural-language questions about an
ecommerce business by reasoning over a local **SQLite** database. The agent
interprets intent, selects the right tool, retrieves or aggregates data, and
returns a **grounded** answer — never inventing values.

Built with the **OpenAI Agents SDK** and switchable between **OpenAI** and a
**local Ollama** model through a single environment variable. The database
tools and agent logic stay identical across providers.

---

## ✨ Features

- **Natural-language querying** — ask questions like *"What are the top 10
  best-selling products?"* or *"Show the monthly revenue trend for the last 6
  months."*
- **Eight-table ecommerce schema** — customers, categories, products, orders,
  order items, payments, reviews, and shipments, with realistic synthetic data.
- **Tool-based reasoning** — the agent chooses the smallest sufficient tool for
  each question and can chain tools for multi-step queries.
- **Read-only by design** — application-level guardrails reject any mutating SQL.
- **Provider-agnostic** — run against OpenAI or a fully local Ollama model with
  no code changes.
- **Multi-turn context** — resolves follow-ups like *"What about last month?"*
  and references like *"that order."*
- **Observability** — structured logging of sessions, tool calls, SQL outcomes,
  and latency.
- **Chat UI** — Gradio interface for interactive use.

---

## 🏛️ Architecture

```
User
  │
  ▼
Gradio UI  /  CLI
  │
  ▼
Agent  (OpenAI Agents SDK)
  │  intent + tool selection
  ▼
Tools
  ├── get_database_schema     schema, relationships, business definitions
  ├── search_products         by name, category, price, rating, stock
  ├── get_customer            non-sensitive customer info by id / email
  ├── get_order_details       order + items + payment + shipment
  ├── execute_readonly_sql    validated SELECT-only queries
  ├── sales_analytics         revenue, AOV, top products, trends
  ├── inventory_lookup        low / out-of-stock, category inventory
  └── review_search           reviews + rating summaries
  │
  ▼
SQLite Ecommerce Database
  │
  ▼
Tool result → Agent → Grounded final answer
```

---

## 🗂️ Database Schema

| Table         | Purpose                                            |
| ------------- | -------------------------------------------------- |
| `customers`   | Customer identity, contact, and location           |
| `categories`  | Product categories                                 |
| `products`    | Catalog items, price, stock, rating                |
| `orders`      | Order header: status, payment method, total        |
| `order_items` | Line items: quantity, unit price, discount         |
| `payments`    | Payment records: amount, status, reference         |
| `reviews`     | Customer product reviews and ratings               |
| `shipments`   | Carrier, tracking, ship / delivery dates, status   |

Foreign keys enforce valid relationships, and indexes are added on foreign keys
and frequently filtered columns.

> **Discount convention:** `order_items.discount` is stored as a
> *(document your chosen convention here — e.g. an absolute amount per line, or a
> percentage 0–1)*.

---

## 🛡️ Guardrails & Security

Guardrails are enforced in application code, not only in the system prompt:

- **SQL safety** — only read-only `SELECT` queries run; `INSERT`, `UPDATE`,
  `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `PRAGMA`, and multi-statement
  execution are rejected.
- **Table allowlist** — the SQL tool can touch only the defined ecommerce tables.
- **PII minimization** — sensitive fields are masked; customer queries return
  only the minimum fields needed.
- **Query limits** — a maximum execution time and a row cap (default 100).
- **Prompt-injection resistance** — database text (reviews, descriptions) is
  treated as untrusted data, never as instructions.
- **No fabrication** — if the data isn't there, the agent says so explicitly.
- **Out-of-scope handling** — questions unrelated to the database are politely
  declined.

---

## 📁 Project Structure

```
ecommerce_database_agent/
├── app/
│   ├── agent.py         agent definition + run loop
│   ├── config.py        env-driven provider / model config
│   ├── context.py       multi-turn conversation state
│   ├── guardrails.py    SQL validation, allowlist, PII masking
│   └── prompts.py       agent instructions
├── tools/
│   ├── schema_tool.py
│   ├── sql_tool.py
│   ├── customer_tool.py
│   ├── product_tool.py
│   ├── order_tool.py
│   ├── analytics_tool.py
│   ├── inventory_tool.py
│   └── review_tool.py
├── database/
│   ├── ecommerce.db     generated SQLite database
│   ├── schema.sql       DDL for all tables + indexes
│   └── seed.py          recreates and populates the database
├── tests/
│   ├── test_tools.py
│   ├── test_guardrails.py
│   └── test_agent.py
├── main.py              entry point (launches Gradio / CLI)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone and install

```bash
git clone https://github.com/<your-username>/ecommerce-database-agent.git
cd ecommerce-database-agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your provider

Copy the example env file and edit it:

```bash
cp .env.example .env
```

**Option A — OpenAI**

```env
LLM_PROVIDER=openai
OPENAI_MODEL=<configured-model>
OPENAI_API_KEY=<your-key>
```

**Option B — Local Ollama**

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=<configured-model>
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. Build the database

```bash
python database/seed.py
```

This recreates `ecommerce.db` from scratch with synthetic data (50+ customers,
10+ products, 200+ orders, and matching items, payments, reviews, and shipments).

### 4. Run the app

```bash
python main.py
```

---

## 💬 Example Questions

- What are the top 10 best-selling products by quantity?
- How much revenue did we generate last month?
- What is the average order value?
- Which customers placed more than 5 orders?
- Which products are low in stock?
- Which category generated the highest revenue?
- What percentage of orders were cancelled?
- Which products have the highest average review rating with at least 20 reviews?
- Show the monthly revenue trend for the last 6 months.
- What is the average delivery time by shipping carrier?

---

## 🧪 Testing & Evaluation

```bash
pytest tests/
```

The suite covers tool behavior, guardrail enforcement, and agent responses,
including **25+ evaluation cases** and dedicated **guardrail tests** that confirm
mutating SQL and out-of-scope requests are rejected.

---

## 🔭 Logging & Observability

Each request logs the session and request ID, the user query, the selected
agent/tool, tool arguments (after masking sensitive fields), the SQL outcome and
row count, per-tool and total latency, and the final response. Errors and
rejected tool calls are captured as well.

---

## 🧰 Tech Stack

| Layer        | Choice                          |
| ------------ | ------------------------------- |
| Agent        | OpenAI Agents SDK               |
| LLM          | OpenAI  /  Ollama (configurable)|
| Database     | SQLite                          |
| UI           | Gradio                          |
| Testing      | pytest                          |
| Language     | Python                          |

---

## 📄 License

Add your chosen license here (e.g. MIT).
