from pydantic import BaseModel


class DiskRequest(BaseModel):
    id: int
    sequence: str


class DiskSetRequest(BaseModel):
    alphabet: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    disks: list[DiskRequest]


class CipherKeyRequest(BaseModel):
    disk_order: list[int]
    offset: int


class CipherRequest(BaseModel):
    text: str
    disk_set: DiskSetRequest
    key: CipherKeyRequest
    include_trace: bool = True


class CipherByDiskSetRequest(BaseModel):
    text: str
    disk_set_id: int
    key: CipherKeyRequest
    include_trace: bool = True


class CipherStepResponse(BaseModel):
    block_index: int
    char_index: int
    disk_id: int
    input_char: str
    output_char: str
    input_position: int
    output_position: int
    offset: int
    mode: str


class CipherResponse(BaseModel):
    text: str
    normalized_text: str
    trace: list[CipherStepResponse]


class ErrorDetailResponse(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetailResponse
