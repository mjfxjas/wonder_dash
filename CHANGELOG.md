# Changelog

All notable changes to this project are documented in this file.

## 0.1.4 - 2026-10-06
- Install AWS CRT automatically for `aws login` credential support.
- Require Boto3 1.41+ and verify dependencies in an isolated CI environment.
- Apply and normalize dashboard environment overrides before startup validation.
- Read all CloudWatch metric pages and preserve failures across response pages.
- Add `wonder-dash --version` and document Homebrew installation.

## 0.1.1 - 2026-02-11
- Published `wonder-dash` to PyPI.
- Added and validated GitHub Actions workflows for CI and publishing.
- Improved package verification with build and `twine check`.

## 0.1.0 - 2025-11-21
- Initial public release of WonderDash CLI.
- Added CloudFront dashboard with live metrics and trend visualizations.
- Added S3, EC2, Lambda, and CloudWatch toolkit support.
- Added interactive hub and configuration helpers.
