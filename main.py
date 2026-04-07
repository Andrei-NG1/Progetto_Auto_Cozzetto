import json
import secrets
import hashlib
import hmac
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from databases import Database
from pydantic import BaseModel

# Configurazione percorsi
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "autoscout_clone.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
USERS_FILE = BASE_DIR / "users.json"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

database = Database(f"sqlite:///{DB_PATH}")
SESSIONS = {}
PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210000


class RegisterRequest(BaseModel):
    email: str
    password: str
    role: str = "user"


class LoginRequest(BaseModel):
    email: str
    password: str


class ListingIn(BaseModel):
    brand_name: str
    model_name: str
    price: float
    mileage: int
    fuel_type: str
    registration_date: str
    power_kw: int
    description: str = ""
    image_url: str = ""


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    ).hex()
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_password: str) -> bool:
    parts = stored_password.split("$", 3)
    if len(parts) == 4 and parts[0] == PASSWORD_SCHEME:
        _, iterations_s, salt, saved_digest = parts
        try:
            iterations = int(iterations_s)
        except ValueError:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(digest, saved_digest)
    # Compatibilita temporanea con vecchie password salvate in chiaro.
    return hmac.compare_digest(stored_password, password)


def load_users():
    if not USERS_FILE.exists():
        USERS_FILE.write_text("[]", encoding="utf-8")
    with USERS_FILE.open("r", encoding="utf-8") as f:
        users = json.load(f)

    changed = False
    for u in users:
        pwd = u.get("password")
        if isinstance(pwd, str) and not pwd.startswith(f"{PASSWORD_SCHEME}$"):
            u["password"] = hash_password(pwd)
            changed = True

    if changed:
        save_users(users)

    return users


def save_users(users):
    sanitized = []
    for u in users:
        item = dict(u)
        pwd = item.get("password")
        if isinstance(pwd, str) and not pwd.startswith(f"{PASSWORD_SCHEME}$"):
            item["password"] = hash_password(pwd)
        sanitized.append(item)
    with USERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(sanitized, f, indent=4)


async def ensure_demo_listings():
    demo_cars = [
        {
            "brand": "Toyota",
            "model": "Yaris Hybrid Trend",
            "price": 16900,
            "mileage": 43200,
            "fuel": "Elettrica/Benzina",
            "date": "06/2021",
            "kw": 85,
            "desc": "Compatta ibrida, perfetta per citta e viaggi.",
            "img": "https://cdn.group.renault.com/ren/it/product-plans/yaris-hybrid.jpg.ximg.medium.jpg/21f6f7ef70.jpg",
        },
        {
            "brand": "Volkswagen",
            "model": "Golf 2.0 TDI Life",
            "price": 22400,
            "mileage": 59000,
            "fuel": "Diesel",
            "date": "02/2022",
            "kw": 110,
            "desc": "Golf affidabile con cambio automatico e ADAS completi.",
            "img": "https://images.carwow.it/carwow/wp-content/uploads/2020/01/08153458/vw-golf-front-1.jpg",
        },
        {
            "brand": "Renault",
            "model": "Clio 1.0 TCe Zen",
            "price": 12900,
            "mileage": 48800,
            "fuel": "Benzina",
            "date": "09/2020",
            "kw": 67,
            "desc": "Utilitaria economica, ideale per neopatentati.",
            "img": "https://cdn.motor1.com/images/mgl/9mWZ2/s1/renault-clio-e-tech-hybrid.jpg",
        },
    ]

    for car in demo_cars:
        existing_id = await database.fetch_val(
            """
            SELECT l.id
            FROM Listings l
            JOIN Models m ON l.model_id = m.id
            JOIN Brands b ON m.brand_id = b.id
            WHERE b.name = :brand AND m.name = :model
            LIMIT 1
            """,
            {"brand": car["brand"], "model": car["model"]},
        )
        if existing_id:
            continue

        await database.execute(
            "INSERT OR IGNORE INTO Brands (name) VALUES (:brand)",
            {"brand": car["brand"]},
        )
        brand_id = await database.fetch_val(
            "SELECT id FROM Brands WHERE name = :brand",
            {"brand": car["brand"]},
        )

        await database.execute(
            "INSERT OR IGNORE INTO Models (brand_id, name) VALUES (:brand_id, :model)",
            {"brand_id": brand_id, "model": car["model"]},
        )
        model_id = await database.fetch_val(
            "SELECT id FROM Models WHERE brand_id = :brand_id AND name = :model",
            {"brand_id": brand_id, "model": car["model"]},
        )

        listing_id = await database.execute(
            """
            INSERT INTO Listings (model_id, price, mileage, fuel_type, registration_date, power_kw, description)
            VALUES (:model_id, :price, :mileage, :fuel, :date, :kw, :desc)
            """,
            {
                "model_id": model_id,
                "price": car["price"],
                "mileage": car["mileage"],
                "fuel": car["fuel"],
                "date": car["date"],
                "kw": car["kw"],
                "desc": car["desc"],
            },
        )

        if car["img"].strip():
            await database.execute(
                "INSERT INTO CarImages (listing_id, image_url) VALUES (:listing_id, :image_url)",
                {"listing_id": listing_id, "image_url": car["img"]},
            )


def auth_user(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token mancante")
    token = authorization.split(" ", 1)[1].strip()
    user = SESSIONS.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Token non valido")
    return user


def admin_only(authorization: Optional[str]):
    user = auth_user(authorization)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admin")
    return user

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    load_users()
    await ensure_demo_listings()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

# Middleware CORS per evitare blocchi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/")
async def root():
    return FileResponse(str(BASE_DIR / "index.html"))


@app.post("/api/register")
async def register(payload: RegisterRequest):
    users = load_users()
    if any(u["email"].lower() == payload.email.lower() for u in users):
        raise HTTPException(status_code=400, detail="Email gia registrata")

    role = payload.role.lower().strip()
    if role not in {"admin", "user"}:
        role = "user"

    users.append(
        {
            "email": payload.email,
            "password": hash_password(payload.password),
            "role": role,
        }
    )
    save_users(users)
    return {"message": "Registrazione completata"}


@app.post("/api/login")
async def login(payload: LoginRequest):
    users = load_users()
    user = next(
        (
            u
            for u in users
            if u["email"].lower() == payload.email.lower()
            and verify_password(payload.password, u["password"])
        ),
        None,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Credenziali non valide")

    token = secrets.token_hex(24)
    SESSIONS[token] = {"email": user["email"], "role": user["role"]}
    return {"token": token, "user": {"email": user["email"], "role": user["role"]}}


@app.get("/api/me")
async def me(authorization: Optional[str] = Header(default=None)):
    return auth_user(authorization)

@app.get("/api/listings")
async def get_listings(
    page: int = 1, 
    size: int = 5, 
    max_price: Optional[float] = Query(None), 
    fuel: Optional[str] = Query(None)
):
    offset = (page - 1) * size
    where = ["1=1"]
    values = {"limit": size, "offset": offset}
    
    if max_price:
        values["max_price"] = max_price
        where.append("l.price <= :max_price")
    if fuel and fuel.strip():
        values["fuel"] = fuel
        where.append("l.fuel_type = :fuel")
    
    where_str = " AND ".join(where)
    
    # Query per le auto
    query = f"""
        SELECT l.id, b.name as brand_name, m.name as model_name, l.price, l.mileage, 
               l.fuel_type, l.registration_date, l.power_kw,
               (SELECT image_url FROM CarImages WHERE listing_id = l.id LIMIT 1) as main_image
        FROM Listings l 
        JOIN Models m ON l.model_id = m.id 
        JOIN Brands b ON m.brand_id = b.id
        WHERE {where_str} 
        ORDER BY l.id DESC 
        LIMIT :limit OFFSET :offset
    """
    items = await database.fetch_all(query, values)
    
    # Query per il conteggio totale
    count_query = f"""
        SELECT COUNT(*) FROM Listings l 
        JOIN Models m ON l.model_id = m.id 
        JOIN Brands b ON m.brand_id = b.id 
        WHERE {where_str}
    """
    count_values = {k: v for k, v in values.items() if k not in ['limit', 'offset']}
    total = await database.fetch_val(count_query, count_values)
    
    return {
        "items": [dict(i) for i in items], 
        "total": total, 
        "total_pages": (total + size - 1) // size if total > 0 else 0
    }

@app.get("/api/listings/{id}")
async def get_listing(id: int):
    car = await database.fetch_one("""
        SELECT l.*, b.name as brand_name, m.name as model_name 
        FROM Listings l JOIN Models m ON l.model_id = m.id 
        JOIN Brands b ON m.brand_id = b.id WHERE l.id = :id
    """, {"id": id})
    if not car: raise HTTPException(404)
    
    imgs = await database.fetch_all("SELECT image_url FROM CarImages WHERE listing_id = :id", {"id": id})
    res = dict(car)
    res["images"] = [i["image_url"] for i in imgs] or ["https://via.placeholder.com/600x400"]
    return res


@app.post("/api/listings/{id}/contact")
async def contact_seller(id: int, authorization: Optional[str] = Header(default=None)):
    user = auth_user(authorization)
    car = await database.fetch_one(
        """
        SELECT l.id, b.name as brand_name, m.name as model_name
        FROM Listings l
        JOIN Models m ON l.model_id = m.id
        JOIN Brands b ON m.brand_id = b.id
        WHERE l.id = :id
        """,
        {"id": id},
    )
    if not car:
        raise HTTPException(status_code=404, detail="Annuncio non trovato")
    return {
        "message": "Venditore contattabile",
        "car": dict(car),
        "seller": {
            "phone": "+39 012 3456789",
            "email": "vendite@autoscout24-clone.it",
        },
        "requested_by": user["email"],
    }


@app.post("/api/listings")
async def create_listing(payload: ListingIn, authorization: Optional[str] = Header(default=None)):
    admin_only(authorization)

    await database.execute(
        "INSERT OR IGNORE INTO Brands (name) VALUES (:brand)",
        {"brand": payload.brand_name.strip()},
    )
    brand_id = await database.fetch_val(
        "SELECT id FROM Brands WHERE name = :brand",
        {"brand": payload.brand_name.strip()},
    )

    await database.execute(
        "INSERT OR IGNORE INTO Models (brand_id, name) VALUES (:brand_id, :model)",
        {"brand_id": brand_id, "model": payload.model_name.strip()},
    )
    model_id = await database.fetch_val(
        "SELECT id FROM Models WHERE brand_id = :brand_id AND name = :model",
        {"brand_id": brand_id, "model": payload.model_name.strip()},
    )

    listing_id = await database.execute(
        """
        INSERT INTO Listings (model_id, price, mileage, fuel_type, registration_date, power_kw, description)
        VALUES (:model_id, :price, :mileage, :fuel_type, :registration_date, :power_kw, :description)
        """,
        {
            "model_id": model_id,
            "price": payload.price,
            "mileage": payload.mileage,
            "fuel_type": payload.fuel_type,
            "registration_date": payload.registration_date,
            "power_kw": payload.power_kw,
            "description": payload.description,
        },
    )

    image_url = payload.image_url.strip() or "https://via.placeholder.com/600x400"
    await database.execute(
        "INSERT INTO CarImages (listing_id, image_url) VALUES (:listing_id, :image_url)",
        {"listing_id": listing_id, "image_url": image_url},
    )
    return {"message": "Veicolo creato", "id": listing_id}


@app.put("/api/listings/{id}")
async def update_listing(id: int, payload: ListingIn, authorization: Optional[str] = Header(default=None)):
    admin_only(authorization)

    listing = await database.fetch_one("SELECT id FROM Listings WHERE id = :id", {"id": id})
    if not listing:
        raise HTTPException(status_code=404, detail="Annuncio non trovato")

    await database.execute(
        "INSERT OR IGNORE INTO Brands (name) VALUES (:brand)",
        {"brand": payload.brand_name.strip()},
    )
    brand_id = await database.fetch_val(
        "SELECT id FROM Brands WHERE name = :brand",
        {"brand": payload.brand_name.strip()},
    )

    await database.execute(
        "INSERT OR IGNORE INTO Models (brand_id, name) VALUES (:brand_id, :model)",
        {"brand_id": brand_id, "model": payload.model_name.strip()},
    )
    model_id = await database.fetch_val(
        "SELECT id FROM Models WHERE brand_id = :brand_id AND name = :model",
        {"brand_id": brand_id, "model": payload.model_name.strip()},
    )

    await database.execute(
        """
        UPDATE Listings
        SET model_id = :model_id,
            price = :price,
            mileage = :mileage,
            fuel_type = :fuel_type,
            registration_date = :registration_date,
            power_kw = :power_kw,
            description = :description
        WHERE id = :id
        """,
        {
            "id": id,
            "model_id": model_id,
            "price": payload.price,
            "mileage": payload.mileage,
            "fuel_type": payload.fuel_type,
            "registration_date": payload.registration_date,
            "power_kw": payload.power_kw,
            "description": payload.description,
        },
    )

    image_url = payload.image_url.strip() or "https://via.placeholder.com/600x400"
    existing_img = await database.fetch_val(
        "SELECT id FROM CarImages WHERE listing_id = :listing_id LIMIT 1",
        {"listing_id": id},
    )
    if existing_img:
        await database.execute(
            "UPDATE CarImages SET image_url = :image_url WHERE id = :id",
            {"id": existing_img, "image_url": image_url},
        )
    else:
        await database.execute(
            "INSERT INTO CarImages (listing_id, image_url) VALUES (:listing_id, :image_url)",
            {"listing_id": id, "image_url": image_url},
        )

    return {"message": "Veicolo aggiornato"}


@app.delete("/api/listings/{id}")
async def delete_listing(id: int, authorization: Optional[str] = Header(default=None)):
    admin_only(authorization)
    listing = await database.fetch_one("SELECT id FROM Listings WHERE id = :id", {"id": id})
    if not listing:
        raise HTTPException(status_code=404, detail="Annuncio non trovato")

    await database.execute("DELETE FROM CarImages WHERE listing_id = :id", {"id": id})
    await database.execute("DELETE FROM Listings WHERE id = :id", {"id": id})
    return {"message": "Veicolo eliminato"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)