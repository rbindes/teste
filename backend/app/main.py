from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.database import engine, Base, async_session
from app.models import Category, CategoryRule
from app.routers import auth, accounts, imports, transactions, dashboard


SEED_CATEGORIES = [
    {"name": "Alimentação", "icon": "🍽️", "color": "#FF6B6B"},
    {"name": "Transporte", "icon": "🚗", "color": "#4ECDC4"},
    {"name": "Moradia", "icon": "🏠", "color": "#45B7D1"},
    {"name": "Saúde", "icon": "🏥", "color": "#96CEB4"},
    {"name": "Lazer", "icon": "🎬", "color": "#FFEAA7"},
    {"name": "Educação", "icon": "📚", "color": "#DDA0DD"},
    {"name": "Vestuário", "icon": "👕", "color": "#98D8C8"},
    {"name": "Transferência", "icon": "💸", "color": "#87CEEB"},
    {"name": "Salário", "icon": "💰", "color": "#2ECC71"},
    {"name": "Investimento", "icon": "📈", "color": "#3498DB"},
    {"name": "Outros", "icon": "📌", "color": "#BDC3C7"},
]

SEED_RULES = {
    "Alimentação": [
        "ifood", "rappi", "uber eats", "restaurante", "padaria", "supermercado",
        "carrefour", "pao de acucar", "assai", "mercado", "lanchonete", "pizzaria",
        "burguer", "sushi", "acougue", "hortifruti", "atacadao", "sams club",
        "extra", "dia supermercado", "big bompreco",
    ],
    "Transporte": [
        "uber", "99app", "99 ", "shell", "posto", "estacionamento", "ipva",
        "pedagio", "combustivel", "gasolina", "etanol", "br distribuidora",
        "auto posto", "sem parar", "conectcar", "veloe",
    ],
    "Moradia": [
        "aluguel", "condominio", "enel", "sabesp", "comgas", "cpfl", "cemig",
        "copel", "celesc", "light", "neoenergia", "internet", "vivo", "claro",
        "tim", "oi fibra", "net virtua",
    ],
    "Saúde": [
        "farmacia", "drogasil", "droga raia", "drogaria", "hospital", "medico",
        "plano saude", "unimed", "amil", "sulamerica", "bradesco saude",
        "hapvida", "notredame", "laboratorio", "exame",
    ],
    "Lazer": [
        "netflix", "spotify", "disney", "hbo", "amazon prime", "cinema",
        "teatro", "viagem", "hotel", "airbnb", "booking", "decolar",
        "ingresso", "show", "parque", "xbox", "playstation", "steam",
    ],
    "Educação": [
        "escola", "faculdade", "universidade", "curso", "livro", "udemy",
        "coursera", "alura", "descomplica", "mensalidade escol",
    ],
    "Vestuário": [
        "zara", "renner", "c&a", "cea", "shein", "calcado", "riachuelo",
        "hering", "marisa", "centauro", "netshoes", "arezzo",
    ],
    "Transferência": [
        "pix enviado", "pix recebido", "ted", "doc", "transferencia",
    ],
    "Salário": [
        "salario", "folha de pagamento", "pagamento mensal", "pro-labore",
    ],
}


async def seed_categories(session):
    result = await session.execute(select(Category).limit(1))
    if result.scalar_one_or_none() is not None:
        return  # já existe seed

    categories = {}
    for cat_data in SEED_CATEGORIES:
        cat = Category(**cat_data)
        session.add(cat)
        await session.flush()
        categories[cat.name] = cat.id

    for cat_name, patterns in SEED_RULES.items():
        if cat_name not in categories:
            continue
        for i, pattern in enumerate(patterns):
            rule = CategoryRule(
                household_id=None,
                pattern=pattern,
                category_id=categories[cat_name],
                priority=100 - i,
            )
            session.add(rule)

    await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        await seed_categories(session)
    yield


app = FastAPI(title="Finanças Familiar", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(imports.router, prefix="/api/imports", tags=["imports"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])


@app.get("/api/health")
async def health():
    return {"status": "ok"}
