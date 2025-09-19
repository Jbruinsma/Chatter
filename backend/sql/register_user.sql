USE chatter;

DELIMITER //

CREATE PROCEDURE  register_user (
    IN user_id VARCHAR(36),
    IN user_username VARCHAR(50),
    IN user_password BINARY(60),
    IN user_is_public BOOLEAN
)

BEGIN

    INSERT INTO chatter.users(id, username, password, is_public)
    VALUES (
            user_id,
            user_username,
            user_password,
            user_is_public
           );

END //

DELIMITER ;
