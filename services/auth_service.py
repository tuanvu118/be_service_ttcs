from datetime import datetime, timedelta, timezone
from uuid import uuid4

from beanie import PydanticObjectId

from exceptions import ErrorCode, app_exception
from models.refresh_tokens import RefreshTokenSession
from repositories.refresh_token_repo import RefreshTokenRepo
from repositories.user_repo import UserRepo
from schemas.auth import Token
from security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from services.rbac_service import RBACService
from services.user_service import UserService


class AuthService:
    def __init__(
        self,
        user_repo: UserRepo,
        refresh_token_repo: RefreshTokenRepo,
        rbac_service: RBACService,
        user_service: UserService,
    ) -> None:
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo
        self.rbac_service = rbac_service
        self.user_service = user_service

    @staticmethod
    def _refresh_token_expiry() -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    async def _issue_token_pair(self, user) -> Token:
        roles_list = await self.rbac_service.build_unit_role_claims_for_user(user.id)
        access_token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "student_id": user.student_id,
                "is_active": True,
                "roles": roles_list,
            },
        )

        refresh_jti = uuid4().hex
        refresh_expires_at = self._refresh_token_expiry()
        refresh_token = create_refresh_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "student_id": user.student_id,
                "jti": refresh_jti,
            },
            expires_delta=refresh_expires_at - datetime.now(timezone.utc),
        )

        await self.refresh_token_repo.create(
            RefreshTokenSession(
                user_id=user.id,
                jti=refresh_jti,
                expires_at=refresh_expires_at,
            )
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    @staticmethod
    def _validate_refresh_payload(refresh_token: str) -> dict:
        try:
            payload = decode_token(refresh_token)
        except Exception:
            app_exception(ErrorCode.INVALID_TOKEN)

        if payload.get("type") != "refresh":
            app_exception(ErrorCode.INVALID_TOKEN)

        if not payload.get("sub") or not payload.get("jti"):
            app_exception(ErrorCode.INVALID_TOKEN)

        return payload

    async def login(self, username: str, password: str) -> Token:
        user = await self.user_repo.get_by_student_id(username)
        if not user or not self.user_service.verify_passwod(password, user.password_hash):
            app_exception(ErrorCode.INVALID_CREDENTIALS)

        return await self._issue_token_pair(user)

    async def refresh(self, refresh_token: str) -> Token:
        payload = self._validate_refresh_payload(refresh_token)
        session = await self.refresh_token_repo.get_active_by_jti(payload["jti"])
        if not session or str(session.user_id) != str(payload["sub"]):
            app_exception(ErrorCode.INVALID_TOKEN)

        user = await self.user_repo.get_by_id(PydanticObjectId(payload["sub"]))
        if not user:
            app_exception(ErrorCode.INVALID_TOKEN)

        await self.refresh_token_repo.revoke(session)
        return await self._issue_token_pair(user)

    async def logout(self, refresh_token: str) -> None:
        payload = self._validate_refresh_payload(refresh_token)
        session = await self.refresh_token_repo.get_active_by_jti(payload["jti"])
        if session:
            await self.refresh_token_repo.revoke(session)
