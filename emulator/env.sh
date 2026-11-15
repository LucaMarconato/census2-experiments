# Source this: point AWS CLI and obstore at the emulator on :9297.
D=$HOME/.aws/emulator/9297
unset AWS_PROFILE AWS_SESSION_TOKEN
export AWS_ENDPOINT_URL=https://127.0.0.1:9297 AWS_CA_BUNDLE=$D/ca.pem AWS_CONFIG_FILE=$D/config
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_EC2_METADATA_DISABLED=true
export AWS_ALLOW_INVALID_CERTIFICATES=true  # obstore: self-signed cert
export AWS_ACCESS_KEY_ID=$(awk -F' *= *' '/aws_access_key_id/{print $2}' $D/emulator_credentials)
export AWS_SECRET_ACCESS_KEY=$(awk -F' *= *' '/aws_secret_access_key/{print $2}' $D/emulator_credentials)
