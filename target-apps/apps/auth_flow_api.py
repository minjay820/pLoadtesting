import hashlib
from itertools import count

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="pLoadtesting Target Suite - Auth Flow API",
    version="1.0.0",
    description="Auth-like and scenario-style business flow target for controlled session and checkout workloads.",
)

ACCESS_TOKENS: dict[str, dict] = {}
REFRESH_TOKENS: dict[str, dict] = {}
ORDERS: dict[int, dict] = {}
ORDER_COUNTER = count(1)
TOKEN_COUNTER = count(1)
VALID_PASSWORD = "demo-password"
MAX_ACCESS_USES = 5
MAX_REFRESH_USES = 3


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=64)
    access_token_uses: int = Field(default=3, ge=1, le=MAX_ACCESS_USES)
    refresh_uses: int = Field(default=2, ge=1, le=MAX_REFRESH_USES)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=128)
    access_token_uses: int = Field(default=3, ge=1, le=MAX_ACCESS_USES)


class CheckoutRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    quantity: int = Field(default=1, ge=1, le=10)


def _issue_access_token(username: str, uses_left: int) -> str:
    token = hashlib.sha256(f"demo-access|{username}|{next(TOKEN_COUNTER)}".encode("utf-8")).hexdigest()
    ACCESS_TOKENS[token] = {"username": username, "uses_left": uses_left, "revoked": False}
    return token


def _issue_refresh_token(username: str, refresh_uses_left: int) -> str:
    token = hashlib.sha256(f"demo-refresh|{username}|{next(TOKEN_COUNTER)}".encode("utf-8")).hexdigest()
    REFRESH_TOKENS[token] = {"username": username, "refresh_uses_left": refresh_uses_left, "revoked": False}
    return token


def _require_user(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = authorization.split(" ", 1)[1]
    access_state = ACCESS_TOKENS.get(token)
    if not access_state:
        raise HTTPException(status_code=401, detail="Invalid bearer token.")
    if access_state["revoked"]:
        raise HTTPException(status_code=401, detail="Revoked bearer token.")
    if access_state["uses_left"] <= 0:
        raise HTTPException(status_code=401, detail="Expired bearer token.")
    access_state["uses_left"] -= 1
    return access_state["username"]


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "target_app_id": "auth-flow-api"}


@app.post("/api/login")
async def login(body: LoginRequest) -> dict:
    if body.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid demo credentials.")
    access_token = _issue_access_token(body.username, body.access_token_uses)
    refresh_token = _issue_refresh_token(body.username, body.refresh_uses)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "access_uses_left": body.access_token_uses,
        "refresh_uses_left": body.refresh_uses,
    }


@app.post("/api/refresh")
async def refresh(body: RefreshRequest) -> dict:
    refresh_state = REFRESH_TOKENS.get(body.refresh_token)
    if not refresh_state:
        raise HTTPException(status_code=401, detail="Invalid refresh token.")
    if refresh_state["revoked"]:
        raise HTTPException(status_code=401, detail="Revoked refresh token.")
    if refresh_state["refresh_uses_left"] <= 0:
        raise HTTPException(status_code=401, detail="Expired refresh token.")

    refresh_state["refresh_uses_left"] -= 1
    access_token = _issue_access_token(refresh_state["username"], body.access_token_uses)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "access_uses_left": body.access_token_uses,
        "refresh_uses_left": refresh_state["refresh_uses_left"],
    }


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


@app.post("/api/logout")
async def logout(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = authorization.split(" ", 1)[1]
    access_state = ACCESS_TOKENS.get(token)
    if not access_state:
        raise HTTPException(status_code=401, detail="Invalid bearer token.")
    access_state["revoked"] = True
    return {"status": "logged_out"}
