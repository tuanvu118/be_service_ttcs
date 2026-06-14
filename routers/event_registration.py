from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, Header, Path, Request, status

from utils.rate_limiter import limiter
from schemas.auth import TokenData
from schemas.event_registration import (
    EventRegistrationRequest,
    EventRegistrationResponse,
    EventRegistrationUserResponse,
    MyEventDetailResponse,
    MyEventRegistrationResponse,
)
from internal_auth import get_current_user_from_gateway
from services.event_registration_service import EventRegistrationService


router = APIRouter(prefix="/events", tags=["Event Registration"])


@router.post(
    "/{event_id}/register_public_event",
    response_model=EventRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/second")
async def register_public_event(
    request: Request,
    event_id: PydanticObjectId = Path(...),
    body: EventRegistrationRequest = None,
    current_user: TokenData = Depends(get_current_user_from_gateway),
    x_idempotency_key: str = Header(default=None, alias="X-Idempotency-Key"),
):
    return await EventRegistrationService.register_public_event(
        event_id=event_id,
        user_id=PydanticObjectId(current_user.sub),
        answers=body.answers if body else [],
        idempotency_key=x_idempotency_key,
    )




@router.delete(
    "/{event_id}/register",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_registration(
    event_id: PydanticObjectId = Path(...),
    current_user: TokenData = Depends(get_current_user_from_gateway),
):
    await EventRegistrationService.cancel(
        event_id=event_id,
        user_id=PydanticObjectId(current_user.sub),
    )


@router.get(
    "/me/registrations",
    response_model=List[MyEventRegistrationResponse],
)
async def get_my_registrations(
    current_user: TokenData = Depends(get_current_user_from_gateway),
):
    return await EventRegistrationService.get_my_registrations(
        user_id=PydanticObjectId(current_user.sub)
    )


@router.get(
    "/{event_id}/registrations",
    response_model=List[EventRegistrationUserResponse],
    dependencies=[Depends(get_current_user_from_gateway)],
)
async def get_event_registrations(
    event_id: PydanticObjectId = Path(...),
):
    return await EventRegistrationService.get_event_registrations(event_id=event_id)


@router.get(
    "/{event_id}/my-registration",
    response_model=MyEventDetailResponse,
)
async def get_my_event_detail(
    event_id: PydanticObjectId = Path(...),
    current_user: TokenData = Depends(get_current_user_from_gateway),
):
    return await EventRegistrationService.get_my_event_detail(
        event_id=event_id,
        user_id=PydanticObjectId(current_user.sub),
    )
