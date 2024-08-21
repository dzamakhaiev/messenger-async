from datetime import datetime, timedelta
import hashlib
import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
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
            payload={'username': username, 'user_id': user_id, 'user_role': user_role,
                     'exp': datetime.now() + timedelta(minutes=settings.TOKEN_EXP_MINUTES)})

        service_logger.debug('Token created.')
        return token

    @staticmethod
    def check_token(token: str):
        """
        Check client's token for access to protected endpoints.
        """
        service_logger.info('Check authorization token.')
        service_logger.debug(token)

        try:
            token_info = jwt.decode(token, key=settings.SECRET_KEY, algorithms=['HS256'])
            service_logger.info('Token decoded.')

            user_id = token_info.get('user_id')
            username = token_info.get('username')
            user_role = token_info.get('user_role')
            return user_id, username, user_role

        except jwt.exceptions.ExpiredSignatureError:
            service_logger.error('Token expired.')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail=settings.EXPIRED_TOKEN)

        except jwt.exceptions.InvalidTokenError:
            service_logger.error('Invalid token.')
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail=settings.INVALID_TOKEN)
