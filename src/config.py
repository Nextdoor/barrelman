import aiobotocore
import base64
import os


class Config:
    def __getattr__(self, item):
        try:
            return self.__getattribute__(item)
        except AttributeError:
            return None

    def parse(self, loop):
        self.loop = loop

        self.prod = _bool(
            'PROD')

        self.structured_logging = self.prod or _bool(
            'STRUCTURED_LOGGING')

        self.github_uri = os.getenv(
            'GITHUB_URI', 'https://github.com')

        self.github_owner = _required_str(
            'GITHUB_OWNER')
        self.github_app_id = _required_str(
            'GITHUB_APP_ID')
        self.github_app_installation_id = _required_str(
            'GITHUB_APP_INSTALLATION_ID')

        self.github_app_private_key = os.getenv('GITHUB_APP_PRIVATE_KEY')
        self.github_webhook_secret = os.getenv('GITHUB_WEBHOOK_SECRET')

        if self.github_app_private_key is None or self.github_webhook_secret is None:
            # Load values from KMS secret file if not set in env.
            boto_session = aiobotocore.get_session(loop=self.loop)

            self.kms_client = boto_session.create_client(
                'kms', region_name=os.getenv(
                    'KMS_AWS_REGION', 'us-east-1'))

            if self.github_app_private_key is None:
                self.github_app_private_key = self._decrypt_kms(
                    'github_app_private_key')
            if self.github_webhook_secret is None:
                self.github_webhook_secret = self._decrypt_kms(
                    'github_webhook_secret')

    def _decrypt_kms(self, secret_name):
        path = '/app/secrets'
        if not self.prod:
            path += '/development'
        else:
            path += '/production'

        with open(f'{path}/{secret_name}.kms', 'r') as secret_file:
            binary_data = base64.b64decode(secret_file.read())
        return self.loop.run_until_complete(self._kms_decrypt(binary_data))

    async def _kms_decrypt(self, binary_data):
        value = await self.kms_client.decrypt(CiphertextBlob=binary_data)
        return value['Plaintext'].decode()

    def reset(self):
        """Clear all config attributes."""
        attributes = list(self.__dict__.keys())
        for attribute in attributes:
            delattr(self, attribute)


def _required_str(name):
    value = os.getenv(name)
    if not value:
        raise OSError('%s must be set.' % name)
    return value


def _bool(name):
    value = os.getenv(name, '').lower()
    return value == 'true' or value == '1' or value == 't'


config = Config()
