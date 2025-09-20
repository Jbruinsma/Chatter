USE chatter;

DELIMITER //

CREATE PROCEDURE retrieve_essential_user_info (
    IN target_user_id VARCHAR(36),
    IN target_user_username VARCHAR(50)
)

BEGIN

    SELECT u.id, u.username, u.is_public
    FROM chatter.users u
    WHERE u.id = target_user_id OR u.username = target_user_username;

end //

DELIMITER ;