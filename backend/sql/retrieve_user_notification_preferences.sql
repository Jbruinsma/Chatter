USE chatter;

DELIMITER //

CREATE PROCEDURE retrieve_user_notification_preferences(
    IN user_id VARCHAR(36),
    IN user_username VARCHAR(50)
)

BEGIN

    SELECT u.allow_essential_notifications, u.allow_message_notifications
    FROM chatter.users u
    WHERE u.id = user_id OR u.username = user_username;

end //

DELIMITER ;