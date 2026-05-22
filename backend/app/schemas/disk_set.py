from pydantic import BaseModel, ConfigDict


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


class DiskSetDiskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position: int
    sequence: str


class DiskSetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    slug: str
    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    disks: list[DiskSetDiskRequest]


class DiskSetUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    slug: str | None = None
    alphabet: str | None = None
    disks: list[DiskSetDiskRequest] | None = None
