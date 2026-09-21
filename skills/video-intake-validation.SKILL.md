---
name: video-intake-validation
---
# Use when validating and sanitizing URLs and handling sensitive data.

## Purpose
This skill captures the workflows related to ensuring URL and input validation in the video intake knowledge system, with a specific emphasis on SSRF protection and prompt injection prevention.

## Workflow
1. **Check URL Format**: Ensure the URL uses the correct scheme (http/https).
2. **Validate Against Blacklisted Hosts**: Reject URLs pointing to localhost or private IPs.
3. **Implement Whitelist Checking**: Verify the URL's hostname against a list of allowed domains if provided.
4. **Return Validation Result**: Structured feedback indicating validity, normalized URL, and any errors detected.

## Pitfalls
- **Improper URL validation**: Always include a domain whitelist to avoid SSRF vulnerabilities; simply checking format is insufficient.
- **Ignoring normalization**: Ensure the final output provides a normalized version of the URL for consistent downstream processing.