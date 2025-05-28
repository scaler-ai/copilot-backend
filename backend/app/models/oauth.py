import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


# OAuth State for CSRF protection
class OAuthStateBase(SQLModel):
    state_token: str = Field(unique=True, index=True)
    provider: str = Field(max_length=50)
    redirect_uri: str = Field(max_length=500)
    expires_at: datetime
    used: bool = Field(default=False)


class OAuthState(OAuthStateBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )


class OAuthStateCreate(OAuthStateBase):
    pass
