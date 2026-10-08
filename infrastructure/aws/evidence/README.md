# QuantSoil evidence storage baseline

This Terraform module creates the production evidence-storage boundary used by
the runtime content-addressed S3 evidence repository.

Controls:

- S3 Versioning enabled.
- S3 Object Lock enabled with configurable default retention.
- Server-side encryption with AES-256.
- All public-access paths blocked.
- Bucket policy denies requests that do not use TLS.
- Bucket name is supplied explicitly so accidental creation of an unexpected
  bucket is avoided.

## Apply

Provide a globally unique bucket name:

    terraform init
    terraform plan -var='bucket_name=YOUR_UNIQUE_BUCKET_NAME'
    terraform apply -var='bucket_name=YOUR_UNIQUE_BUCKET_NAME'

Object Lock is intentionally enabled at bucket creation. Treat the retention
policy as a production data-governance decision; increasing retention can be
irreversible for already locked objects.

This module does not grant runtime access. The runtime workload identity must
receive only the minimum S3 permissions required for evidence writes and
verification. Do not attach broad administrator or s3:* permissions to the
runtime identity.

The configuration should be applied and then verified in the target AWS
account before the production acceptance gate is marked PASS.
