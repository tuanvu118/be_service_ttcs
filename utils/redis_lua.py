import logging
from configs.redis_config import get_redis

logger = logging.getLogger(__name__)

LUA_REGISTER_SCRIPT = """
local users_set_key   = KEYS[1]
local idempotency_key = KEYS[2]

local user_id          = ARGV[1]
local max_participants = tonumber(ARGV[2])
local ttl_seconds      = tonumber(ARGV[3])

local status = redis.call("GET", idempotency_key)
if status == "COMPLETED" then return 2 end
if status == "PROCESSING" then return 0 end
if status == "FAILED" then return -3 end

redis.call("SET", idempotency_key, "PROCESSING", "EX", ttl_seconds)

if redis.call("SISMEMBER", users_set_key, user_id) == 1 then
    redis.call("SET", idempotency_key, "FAILED", "EX", 10)
    return -1
end

if max_participants > 0 then
    local current_count = redis.call("SCARD", users_set_key)
    if current_count >= max_participants then
        redis.call("SET", idempotency_key, "FAILED", "EX", 10)
        return -2
    end
end

redis.call("SADD", users_set_key, user_id)
redis.call("SET", idempotency_key, "COMPLETED", "EX", ttl_seconds)
return 1
"""

LUA_ROLLBACK_SCRIPT = """
local users_set_key   = KEYS[1]
local idempotency_key = KEYS[2]
local user_id         = ARGV[1]

redis.call("SREM", users_set_key, user_id)
redis.call("SET", idempotency_key, "FAILED", "EX", 5)
return 1
"""

_IDEMPOTENCY_TTL = 86400
_USERS_SET_TTL = 172800

def _users_key(event_id: str) -> str:
    return f"event:{event_id}:users"

def _idempotency_key(raw_key: str | None, event_id: str, user_id: str) -> str:
    return raw_key or f"auto:{event_id}:{user_id}"

async def run_lua(event_id: str, user_id: str, max_participants: int, idempotency_key: str | None = None) -> int:
    redis = get_redis()
    u_key = _users_key(event_id)
    i_key = _idempotency_key(idempotency_key, event_id, user_id)

    # Debug: in ra max_participants và key
    logger.warning(f"🔍 run_lua: event={event_id}, user={user_id}, max_p={max_participants}, u_key={u_key}")

    # Đảm bảo set tồn tại (expire an toàn)
    await redis.expire(u_key, _USERS_SET_TTL)

    # Kiểm tra trực tiếp Redis trước khi gọi script (chỉ để debug)
    current = await redis.scard(u_key)
    logger.warning(f"🔍 Before Lua: current members in {u_key} = {current}")

    result = await redis.eval(
        LUA_REGISTER_SCRIPT,
        2,
        u_key,
        i_key,
        user_id,
        str(max_participants),
        str(_IDEMPOTENCY_TTL),
    )
    result = int(result)
    logger.warning(f"🔍 Lua result = {result}")

    # Sau khi thực thi, kiểm tra lại
    after = await redis.scard(u_key)
    logger.warning(f"🔍 After Lua: current members = {after}")
    return result

async def rollback(event_id: str, user_id: str, idempotency_key: str | None = None) -> None:
    try:
        redis = get_redis()
        await redis.eval(
            LUA_ROLLBACK_SCRIPT,
            2,
            _users_key(event_id),
            _idempotency_key(idempotency_key, event_id, user_id),
            user_id,
        )
    except Exception:
        pass