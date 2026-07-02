import sys
sys.path.insert(0, "auth-center")
sys.path.insert(0, ".")
from services.jwt_service import create_token
print(create_token(user_id=7, is_admin=True))
