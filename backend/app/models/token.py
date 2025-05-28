from sqlmodel import SQLModel

# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None

# Token pair combining access and refresh tokens
class TokenPair(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
