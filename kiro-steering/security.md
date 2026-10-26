# Security Guidelines

## API Security Rules
- All API endpoints must be authenticated using Amazon Cognito JWT tokens
- API keys should never be exposed in client-side code
- Rate limiting must be implemented on all public endpoints
- Input validation is required for all user-provided data
- HTTPS must be used for all API communications in production
- CORS policies should be restrictive and specific to allowed origins

## Authentication & Authorization
- JWT tokens must be validated on every request
- Token expiration should be set to 1 hour maximum
- Refresh tokens must be stored securely (httpOnly cookies)
- Role-based access control (RBAC) must be enforced
- Admin endpoints require additional verification

## Data Protection
- Sensitive data must be encrypted at rest in DynamoDB
- PII (Personally Identifiable Information) requires special handling
- Database credentials must use AWS Secrets Manager
- Never log sensitive information (passwords, tokens, API keys)
- Implement data retention policies for user data

## WebSocket Security
- WebSocket connections must be authenticated
- Message validation is required before processing
- Rate limiting applies to WebSocket messages
- Disconnect idle connections after 30 minutes
- Implement message size limits to prevent DoS attacks

## Warning: Critical Security Areas
- Do not modify the JWT authentication hook without thorough testing
- The Cognito user pool configuration is sensitive - changes require approval
- DynamoDB table permissions must follow principle of least privilege
- S3 bucket policies must not allow public access
- API Gateway authorizers must be properly configured

## Recent Security Updates
- Added rate limiting to prevent abuse (last month)
- Updated JWT validation logic (last week)
- Enhanced input sanitization (last week)
- Fixed CORS configuration issue (2 weeks ago)
