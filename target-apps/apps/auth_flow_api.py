import hashlib
from itertools import count

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="pLoadtesting Target Suite - Auth Flow API",
    version="1.0.0",
    description="Auth-like and scenario-style business flow target for controlled session and checkout workloads.",
)

TOKENS: dict[str, str] = {}
ORDERS: dict[int, dict] = {}
ORDER_COUNTER = count(1)
VALID_PASSWORD = "demo-password"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=64)


class CheckoutRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=10)


def _issue_token(username: str) -> str:
    token = hashlib.sha256(f"demo-token|{username}".encode("utf-8")).hexdigest()
    TOKENS[token] = username
    return token


def _require_user(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = authorization.split(" ", 1)[1]
    username = TOKENS.get(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid bearer token.")
    return username


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "target_app_id": "auth-flow-api"}


@app.post("/api/login")
async def login(body: LoginRequest) -> dict:
    if body.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid demo credentials.")
    token = _issue_token(body.username)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/profile")
async def profile(authorization: str | None = Header(default=None)) -> dict:
    username = _require_user(authorization)
    return {"username": username, "roles": ["tester"], "tenant": "demo"}


@app.post("/api/checkout")
async def checkout(body: CheckoutRequest, authorization: str | None = Header(default=None)) -> dict:
    username = _require_user(authorization)
    order_id = next(ORDER_COUNTER)
    order = {
        "order_id": order_id,
        "username": username,
        "sku": body.sku,
        "quantity": body.quantity,
        "status": "confirmed",
    }
    ORDERS[order_id] = order
    return order


@app.get("/api/orders/{order_id}")
async def get_order(order_id: int, authorization: str | None = Header(default=None)) -> dict:
    username = _require_user(authorization)
    order = ORDERS.get(order_id)
    if not order or order["username"] != username:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found.")
    return order

