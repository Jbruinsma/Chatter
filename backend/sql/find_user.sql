USE chatter;

DELIMITER //

CREATE PROCEDURE find_user (
    IN target_user_id VARCHAR(36),
    IN target_user_username VARCHAR(50)
)

BEGIN

    SELECT u.id, u.username
    FROM chatter.users u
    WHERE u.id = target_user_id or u.username = target_user_username;

end //

DELIMITER ;