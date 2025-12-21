from .auth import auth_ns
from .memos import memos_ns
from .categories import categories_ns
from .types import types_ns
from .users import users_ns
from .connections import connections_ns

def register_routes(app, api):
    if auth_ns:
        api.add_namespace(auth_ns, path="/auth")
    if memos_ns:
        api.add_namespace(memos_ns, path="/memos")
    if categories_ns:
        api.add_namespace(categories_ns, path="/categories")
    if types_ns:
        api.add_namespace(types_ns, path="/types")
    if users_ns:
        api.add_namespace(users_ns, path="/users")
    if connections_ns:
        api.add_namespace(connections_ns, path="/connections")
    