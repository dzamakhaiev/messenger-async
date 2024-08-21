from datetime import datetime, timedelta
import hashlib
import jwt
from logger.logger import Logger
from app import settings


service_logger = Logger('auth_service')


class AuthService:

    @staticmethod
    def hash_password(password: str):
        hashed_password = hashlib.sha256(str(password).encode()).hexdigest()
        return hashed_password

    @staticmethod
    def create_token(username, user_id, user_role='default'):
        """
        Create jwt token for client.
        :return: token
        """
        service_logger.info('Create authorization token.')
        token = jwt.encode(
            key=settings.SECRET_KEY, algorithm='HS256',
            payload={'user': username, 'user_id': user_id, 'user_role': user_role,
                     'exp': datetime.now() + timedelta(minutes=settings.TOKEN_EXP_MINUTES)})

        service_logger.debug('Token created.')
        return token
