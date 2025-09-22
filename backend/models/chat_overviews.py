from pydantic import BaseModel


class ChatOverviews(BaseModel):
    main: list[dict] = []
    requests: list[dict] = []