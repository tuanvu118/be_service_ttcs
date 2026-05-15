from fastapi import APIRouter, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from repositories.role_repo import RoleRepo
from repositories.refresh_token_repo import RefreshTokenRepo
from repositories.semester_repo import SemesterRepo
from repositories.user_repo import UserRepo
from repositories.user_role_repo import UserRoleRepo
from schemas.auth import RefreshTokenRequest, Token
from services.rbac_service import RBACService
from services.auth_service import AuthService
from services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Auth"])


def get_auth_service() -> AuthService:
    user_repo = UserRepo()
    return AuthService(
        user_repo=user_repo,
        refresh_token_repo=RefreshTokenRepo(),
        rbac_service=RBACService(user_repo, RoleRepo(), UserRoleRepo(), SemesterRepo()),
        user_service=UserService(user_repo),
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.login(form_data.username, form_data.password)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    payload: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    return await auth_service.refresh(payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    payload: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    await auth_service.logout(payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
