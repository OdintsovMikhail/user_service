from utility import get_connection, DB_SCHEMA
from gql_types import User
import strawberry
import logging

logger = logging.getLogger("user_service")
S = DB_SCHEMA


def resolve_user_by_id(id: int) -> User:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT Id, Username, Email FROM [{S}].[User] WHERE Id = ?", id
        )
        row = cursor.fetchone()

    if not row:
        raise strawberry.exceptions.GraphQLError(f"User with id {id} not found")

    logger.info("User with id %s found", id)
    return User(id=row[0], username=row[1], email=row[2])


def resolve_user_by_username(username: str) -> User:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT Id, Username, Email FROM [{S}].[User] WHERE Username = ?", username
        )
        row = cursor.fetchone()

    if not row:
        raise strawberry.exceptions.GraphQLError(f"User '{username}' not found")

    logger.info("User with username %s found id=%s", username, row[0])
    return User(id=row[0], username=row[1], email=row[2])