from datetime import datetime, timezone

from models.refresh_tokens import RefreshTokenSession


class RefreshTokenRepo:
    async def create(self, session: RefreshTokenSession) -> RefreshTokenSession:
        return await session.insert()

    async def get_active_by_jti(self, jti: str) -> RefreshTokenSession | None:
        now = datetime.now(timezone.utc)
        return await RefreshTokenSession.find_one(
            RefreshTokenSession.jti == jti,
            RefreshTokenSession.revoked_at == None,
            RefreshTokenSession.expires_at > now,
        )

    async def revoke(self, session: RefreshTokenSession) -> RefreshTokenSession:
        session.revoked_at = datetime.now(timezone.utc)
        return await session.save()
