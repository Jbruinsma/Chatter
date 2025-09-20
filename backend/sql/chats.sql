USE chatter;

DELIMITER //

CREATE PROCEDURE retrieve_main_chat_ids (
    IN target_user_id VARCHAR(36),
    IN target_user_username VARCHAR(50)
)

BEGIN

    SELECT c.chat_id
    FROM chatter.chats c
    JOIN chatter.chat_participants cp ON c.chat_id = cp.chat_id
    JOIN chatter.users u ON cp.user_id = u.id
    LEFT JOIN chatter.messages m ON c.chat_id = m.chat_id
    WHERE cp.user_id IN (target_user_id, target_user_username) AND cp.role IN ('OWNER', 'PARTICIPANTS')
    ORDER BY m.time_sent DESC;

end //

CREATE PROCEDURE retrieve_request_chat_ids (
    IN target_user_id VARCHAR(36),
    IN target_user_username VARCHAR(50)
)

BEGIN

    SELECT c.chat_id
    FROM chatter.chats c
    JOIN chatter.chat_participants cp ON c.chat_id = cp.chat_id
    JOIN chatter.users u ON cp.user_id = u.id
    LEFT JOIN chatter.messages m ON c.chat_id = m.chat_id
    WHERE cp.user_id IN (target_user_id, target_user_username) AND cp.role = 'INVITED'
    ORDER BY m.time_sent DESC;

end //

DELIMITER ;