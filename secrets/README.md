# Secrets

You can add KMS encrypted secrets into here as an alternative to passing secrets as environment variables.

## Usage
The app will load from either the `development` or the `production` directory, depending on the value of the `PROD` env var.

Add secrets into those folders based on the name of the secrets. For example, for `github_app_private_key` in dev, add a file named `development/github_app_private_key.kms` with the KMS encrypted value inside it.
