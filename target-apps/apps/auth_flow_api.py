import hashlib
from itertools import count

from fastapi import Cookie, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field

app = FastAPI(
    title="pLoadtesting Target Suite - Auth Flow API",
    version="1.0.0",
    description="Auth-like and scenario-style business flow target for controlled session and checkout workloads.",
)

ACCESS_TOKENS: dict[str, dict] = {}
REFRESH_TOKENS: dict[str, dict] = {}
SESSIONS: dict[str, dict] = {}
MFA_CHALLENGES: dict[str, dict] = {}
ORDERS: dict[int, dict] = {}
ORDER_COUNTER = count(1)
TOKEN_COUNTER = count(1)
VALID_PASSWORD = "demo-password"
MAX_ACCESS_USES = 5
MAX_REFRESH_USES = 3
MAX_SESSION_USES = 5
MAX_ACTIVE_MFA_CHALLENGES = 20
SESSION_COOKIE_NAME = "ploadtesting_demo_session"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=64)
    access_token_uses: int = Field(default=3, ge=1, le=MAX_ACCESS_USES)
    refresh_uses: int = Field(default=2, ge=1, le=MAX_REFRESH_USES)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=128)
    access_token_uses: int = Field(default=3, ge=1, le=MAX_ACCESS_USES)


class SessionLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=64)
    session_uses: int = Field(default=3, ge=1, le=MAX_SESSION_USES)


class MfaStartRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=64)
    channel: str = Field(default="sms", pattern="^(sms|email|authenticator)$")


class MfaVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=6, max_length=6)
    issue_mode: str = Field(default="bearer", pattern="^(bearer|session)$")
    access_token_uses: int = Field(default=3, ge=1, le=MAX_ACCESS_USES)
    refresh_uses: int = Field(default=2, ge=1, le=MAX_REFRESH_USES)
    session_uses: int = Field(default=3, ge=1, le=MAX_SESSION_USES)


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


def _issue_session(username: str, uses_left: int) -> str:
    session_id = hashlib.sha256(f"demo-session|{username}|{next(TOKEN_COUNTER)}".encode("utf-8")).hexdigest()
    SESSIONS[session_id] = {"username": username, "uses_left": uses_left, "revoked": False}
    return session_id


def _expected_mfa_code(username: str, channel: str) -> str:
    total = sum(f"{username}|{channel}".encode("utf-8"))
    return f"{(total * 137) % 1_000_000:06d}"


def _issue_mfa_challenge(username: str, channel: str) -> str:
    if len(MFA_CHALLENGES) >= MAX_ACTIVE_MFA_CHALLENGES:
        raise HTTPException(status_code=422, detail=f"Too many active MFA challenges; cap is {MAX_ACTIVE_MFA_CHALLENGES}.")
    challenge_id = hashlib.sha256(f"demo-mfa|{username}|{channel}|{next(TOKEN_COUNTER)}".encode("utf-8")).hexdigest()
    MFA_CHALLENGES[challenge_id] = {
        "username": username,
        "channel": channel,
        "expected_code": _expected_mfa_code(username, channel),
        "used": False,
    }
    return challenge_id


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


def _require_session(session_id: str | None) -> str:
    if not session_id:
        raise HTTPException(status_code=401, detail="Missing session cookie.")
    session_state = SESSIONS.get(session_id)
    if not session_state:
        raise HTTPException(status_code=401, detail="Invalid session cookie.")
    if session_state["revoked"]:
        raise HTTPException(status_code=401, detail="Revoked session cookie.")
    if session_state["uses_left"] <= 0:
        raise HTTPException(status_code=401, detail="Expired session cookie.")
    session_state["uses_left"] -= 1
    return session_state["username"]


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


@app.post("/api/session/login")
async def session_login(body: SessionLoginRequest, response: Response) -> dict:
    if body.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid demo credentials.")
    session_id = _issue_session(body.username, body.session_uses)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="strict",
        secure=False,
        path="/",
    )
    return {
        "session_mode": "cookie",
        "session_uses_left": body.session_uses,
        "cookie_name": SESSION_COOKIE_NAME,
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


@app.post("/api/mfa/login/start")
async def mfa_login_start(body: MfaStartRequest) -> dict:
    if body.password != VALID_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid demo credentials.")
    challenge_id = _issue_mfa_challenge(body.username, body.channel)
    return {
        "challenge_id": challenge_id,
        "channel": body.channel,
        "demo_code_rule": "deterministic-sum-x137-mod-1000000",
        "code_hint_suffix": _expected_mfa_code(body.username, body.channel)[-2:],
    }


@app.post("/api/mfa/login/verify")
async def mfa_login_verify(body: MfaVerifyRequest, response: Response) -> dict:
    challenge = MFA_CHALLENGES.get(body.challenge_id)
    if not challenge:
        raise HTTPException(status_code=401, detail="Invalid MFA challenge.")
    if challenge["used"]:
        raise HTTPException(status_code=401, detail="Used MFA challenge.")
    if challenge["expected_code"] != body.code:
        raise HTTPException(status_code=401, detail="Invalid MFA code.")

    challenge["used"] = True
    username = challenge["username"]
    if body.issue_mode == "session":
        session_id = _issue_session(username, body.session_uses)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_id,
            httponly=True,
            samesite="strict",
            secure=False,
            path="/",
        )
        return {
            "issue_mode": "session",
            "cookie_name": SESSION_COOKIE_NAME,
            "session_uses_left": body.session_uses,
            "channel": challenge["channel"],
        }

    access_token = _issue_access_token(username, body.access_token_uses)
    refresh_token = _issue_refresh_token(username, body.refresh_uses)
    return {
        "issue_mode": "bearer",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "access_uses_left": body.access_token_uses,
        "refresh_uses_left": body.refresh_uses,
        "channel": challenge["channel"],
    }


@app.get("/api/profile")
async def profile(authorization: str | None = Header(default=None)) -> dict:
    username = _require_user(authorization)
    return {"username": username, "roles": ["tester"], "tenant": "demo"}


@app.get("/api/session/profile")
async def session_profile(ploadtesting_demo_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME)) -> dict:
    username = _require_session(ploadtesting_demo_session)
    return {"username": username, "session_mode": "cookie", "tenant": "demo"}


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


@app.post("/api/session/logout")
async def session_logout(
    response: Response,
    ploadtesting_demo_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict:
    if not ploadtesting_demo_session:
        raise HTTPException(status_code=401, detail="Missing session cookie.")
    session_state = SESSIONS.get(ploadtesting_demo_session)
    if not session_state:
        raise HTTPException(status_code=401, detail="Invalid session cookie.")
    session_state["revoked"] = True
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return {"status": "session_logged_out"}
