from typing import Annotated

ChatId = Annotated[str, "chat_id"]
UserUUID = Annotated[str, "user_uuid"]

FollowerCount = Annotated[str, "follower_count"]
FollowingCount = Annotated[str, "following_count"]