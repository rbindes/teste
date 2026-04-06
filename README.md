# Finanças Familiar

Sistema de controle financeiro para casais. Importa extratos bancários (OFX, CSV, PDF, imagem), categoriza gastos automaticamente e gera dashboard DRE com insights financeiros via IA.

## Bancos suportados

| Banco | OFX | CSV | PDF |
|-------|-----|-----|-----|
| Banco do Brasil | ✅ | ✅ | ✅ |
| Nubank | ✅ | ✅ | ✅ |
| Bradesco | ✅ | - | ✅ |
| Santander | ✅ | - | ✅ |
| Mercado Pago | - | - | ✅ |

## Quick Start

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite .env com suas configurações (especialmente ANTHROPIC_API_KEY para insights com IA)
```

### 2. Subir com Docker Compose

```bash
docker compose up --build
```

### 3. Acessar

- **Frontend (Streamlit):** http://localhost:8501
- **Backend (API docs):** http://localhost:8000/docs

### 4. Primeiro uso

1. Acesse http://localhost:8501
2. Crie sua conta (o sistema gera um ID de grupo familiar)
3. Compartilhe o ID do grupo com seu cônjuge para que ele(a) crie a conta dele(a)
4. Cadastre as contas bancárias de ambos
5. Exporte extratos do internet banking (OFX recomendado)
6. Importe os extratos na página "Importar"
7. Veja o dashboard DRE e os insights!

## Como exportar extratos

- **Banco do Brasil:** Internet Banking > Conta Corrente > Extrato > Download > "Money 2000+ (ofx)"
- **Nubank:** App > Conta > Solicitar extrato > Exportar (enviado por email em CSV/OFX)
- **Bradesco:** Internet Banking > Saldos e Extratos > Salvar como arquivo > OFX
- **Santander:** Internet Banking > Extrato > Exportar OFX
- **Mercado Pago:** App > Atividade > Baixar extrato (PDF)

> **Dica:** Bancos guardam ~60 dias de extrato. Exporte mensalmente para manter histórico.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend:** Streamlit, Plotly
- **Parsers:** ofxparse (OFX), pdfplumber (PDF), pytesseract (OCR)
- **IA:** Claude Haiku (insights financeiros)

## Custo mensal estimado

- Hosting (Railway/Render): ~R$ 30-80
- Claude API (insights): ~R$ 0,50
- APIs de banco: **R$ 0** (usa exportação de arquivos)
