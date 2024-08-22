import socket
from urllib.parse import urlparse
from httpx import AsyncClient, ConnectError, TimeoutException
from logger.logger import Logger
from app import settings


LOCAL_IP = socket.gethostbyname(socket.gethostname())


service_logger = Logger('sender_service')


class SenderService:

    @staticmethod
    def check_url(url: str):
        parsed_url = urlparse(url)
        if parsed_url.hostname == LOCAL_IP or parsed_url.hostname == '127.0.0.1':
            url = url.replace(parsed_url.hostname, 'localhost')

        return url

    async def send_message(self, url, msg_json):
        try:
            url = self.check_url(url)
            service_logger.info(f'Sent message to url: {url}')

            async with AsyncClient() as client:
                response = await client.post(url, json=msg_json, timeout=5)
                service_logger.debug(f'Message sent with status code: {response.status_code}')
                return response

        except (ConnectError, TimeoutException) as e:
            service_logger.error(f'Response with error: {e}')

    async def send_message_by_list(self, address_list, msg_json):
        service_logger.info('Send message by address list.')
        message_received = False

        for user_address in address_list:
            response = await self.send_message(user_address, msg_json)
            if response and response.status_code == 200:
                message_received = True

        if not message_received:
            service_logger.info('Message not sent.')
        return message_received

    async def send_messages_by_list(self, address_list, messages):
        service_logger.info('Send messages by address list.')
        messages_to_delete = []

        for message in messages:
            msg_id, sender_id, receiver_id, sender_username, msg, msg_date = message
            msg_json = {'message': msg, 'sender_id': sender_id, 'sender_username': sender_username,
                        'receiver_id': receiver_id, 'send_date': msg_date.strftime(settings.DATETIME_FORMAT)}
            msg_received = await self.send_message_by_list(address_list, msg_json)

            if msg_received:
                messages_to_delete.append(msg_id)

        messages_to_delete = ','.join([str(msg) for msg in messages_to_delete])
        return messages_to_delete
