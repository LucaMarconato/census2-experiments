# Test only: point AWS CLI and obstore at the local floci emulator (127.0.0.1:4566); test/test are dummy creds, never real AWS.
# Caveat: sourced in your own shell, it sends that shell's aws commands to localhost until you close it (the scripts use subshells).
unset AWS_PROFILE AWS_SESSION_TOKEN AWS_CA_BUNDLE AWS_CONFIG_FILE
export AWS_ENDPOINT_URL=http://127.0.0.1:4566 AWS_ALLOW_HTTP=true FLOCI_NO_UPDATE_CHECK=1
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_EC2_METADATA_DISABLED=true
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test
