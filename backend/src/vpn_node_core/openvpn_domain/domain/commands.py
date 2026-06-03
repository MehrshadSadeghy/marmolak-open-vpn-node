from pydantic import BaseModel, Field


class ServerRemoteConfig(BaseModel):
    server_host: str | None = None
    server_port: int | None = None
    proto: str | None = None


class CreateOpenVpnUserCommand(BaseModel):
    common_name: str = Field(min_length=1, max_length=255)
    remote: ServerRemoteConfig | None = None


class DeleteOpenVpnUserCommand(BaseModel):
    common_name: str = Field(min_length=1, max_length=255)
