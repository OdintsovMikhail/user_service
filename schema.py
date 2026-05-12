import strawberry
from gql_types import User
import resolvers

@strawberry.type
class Query:
    user_by_id: User = strawberry.field(resolver=resolvers.resolve_user_by_id)
    user_by_username: User = strawberry.field(resolver=resolvers.resolve_user_by_username)

schema = strawberry.Schema(query=Query)