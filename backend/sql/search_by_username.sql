USE chatter;

DELIMITER //

CREATE PROCEDURE search_for_profile_by_username(
    IN user_username VARCHAR(50),
    IN results_cap INT
)
BEGIN

    SELECT u.id, u.username, u.profile_picture
    FROM chatter.users u
    WHERE u.username LIKE CONCAT(user_username, '%')
    ORDER BY u.username
    LIMIT results_cap;

END //

DELIMITER ;
