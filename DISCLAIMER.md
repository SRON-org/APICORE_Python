[English](DISCLAIMER.md) | [中文](DISCLAIMER.zh-CN.md)

# Disclaimer

APICORE_Python is provided for parsing and validating APICORE configuration
documents. The APICORE format includes a `run` action, and this SDK exposes its
script as data, but the SDK does not execute the script, enable a sandbox, or
authorize an application to run it.

Application developers who choose to implement `run` execution are solely
responsible for obtaining appropriate user authorization, validating and
restricting commands, providing effective sandbox isolation, protecting data
and credentials, and complying with applicable laws and platform policies.
Parsing or validation success must not be treated as proof that a configuration
or script is safe or trusted.

To the maximum extent permitted by applicable law, the SDK authors and
contributors are not liable for loss, compromise, service interruption, legal
claims, or other damage resulting from executing untrusted configurations,
scripts, or commands through an application that integrates this SDK. This
notice supplements, and does not replace, the warranty and liability terms in
the project [LICENSE](LICENSE).