from pydantic import BaseModel


class DiskResponse(BaseModel):
    id: int
    position: int
    sequence: str


class DiskSetListItemResponse(BaseModel):
    id: int
    name: str
    slug: str
    alphabet: str
    disks_count: int


class DiskSetResponse(BaseModel):
    id: int
    name: str
    slug: str
    alphabet: str
    disks: list[DiskResponse]
