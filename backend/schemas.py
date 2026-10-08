from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str


class ItemCreate(BaseModel):
    name: str
    quantity: int


class ItemUpdate(BaseModel):
    name: str | None = None
    quantity: int | None = None
    is_bought: bool | None = None


class ItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    is_bought: bool
    user_id: int

    class Config:
        from_attributes = True