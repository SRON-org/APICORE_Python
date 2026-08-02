# Security Policy

## Security Boundary

APICORE_Python is a parser and validator. The public `load()`, `loads()`,
`parse()`, and `validate()` APIs decode configuration data and return typed
models. They do not make HTTP requests, open browser links, or execute handler
actions.

In particular, an APICORE `run` handler is treated as untrusted data:

- The parser verifies that a `run` handler has a non-empty `script` field.
- The script is exposed as `HandlerRule.script`; it is never passed to a shell,
  interpreter, `eval()`, or `exec()` by this SDK.
- The repository CLI only validates documents.
- The repository GUI displays the script and labels it as high risk, but does
  not execute it.

There is no execution sandbox setting to enable or disable because this SDK
does not include an execution engine. Parsing a document successfully is not
authorization to execute any action in that document.

## Security Controls And Flags

APICORE_Python intentionally provides no `allow_run`, `execute_handlers`, or
`sandbox_mode` option. Handler execution is outside the SDK, so adding an
`allow_run=False` flag would create a misleading security boundary: changing
that flag could not secure code implemented by a host application. The secure
SDK behavior is unconditional:

- `run` execution is always unavailable.
- Network requests and `browser` actions are always unavailable.
- YAML always uses the safe loader configured by the package.
- The repository GUI always masks parameters marked with `text_secret`.

Applications that add an execution layer should define their own controls with
secure defaults, such as `allow_run=False`, `require_run_approval=True`, and an
OS-enforced sandbox policy. These examples are host-application controls, not
APICORE_Python constructor or function arguments. A sandbox flag must fail
closed when isolation cannot be established; it must never silently fall back
to running a command in the main application process.

## Safely Integrating `run`

Applications that implement `run` themselves assume the security boundary and
must treat every script as attacker-controlled, including scripts from local
files. A secure host integration should, at minimum:

1. Disable execution by default and require explicit, informed user approval
   for each script or for a narrowly defined, trusted policy.
2. Prefer a fixed allowlist of structured operations over arbitrary command
   strings. Resolve executable paths before comparing them with the allowlist.
3. Invoke approved programs with an argument array and shell processing
   disabled, such as `subprocess.run(argv, shell=False, ...)`. Do not use
   `os.system()`, `shell=True`, `eval()`, or `exec()` with configuration data.
4. Reject shell control syntax, including command separators, pipelines,
   redirects, command substitution, environment expansion, and embedded line
   breaks. A denylist alone is not a sufficient authorization policy.
5. Block privilege-escalation, system-management, destructive filesystem,
   credential-access, and arbitrary downloader/interpreter operations unless a
   narrowly scoped product requirement explicitly permits one of them.
6. Run approved operations in an OS-enforced sandbox or isolated worker with a
   dedicated low-privilege identity, an empty or allowlisted environment, no
   inherited credentials, a restricted working directory, and read-only
   filesystem access wherever possible.
7. Deny network access by default and allow only required destinations. Apply
   the same SSRF protections to APICORE URLs and browser actions.
8. Enforce time, memory, process, file, and output limits. Terminate the entire
   process tree when a timeout or cancellation occurs.
9. Record the configuration origin, policy decision, executable, arguments,
   exit status, and resource-limit event in an audit log. Redact secrets from
   scripts, arguments, environment variables, and output.

Containers alone are not a complete sandbox. Use the operating system's
isolation controls and keep the sandbox runtime and policy separate from the
application process that holds user data or credentials.

## Untrusted Input And Resource Limits

`load()` reads the complete input file into memory, and the decoders may allocate
additional memory while parsing nested data. The SDK does not currently impose
file-size, nesting-depth, or parse-time limits. Hosts accepting untrusted input
should enforce those limits before calling the SDK and should parse in a
resource-constrained worker when denial of service is a concern.

Configuration validation establishes structural correctness only. It does not
establish the identity, integrity, or trustworthiness of a document. Obtain
remote configurations over authenticated transport and verify a signature or
trusted digest when provenance matters. Do not store credentials directly in
APICORE documents.

## Decoder And Dependency Safety

The package uses `orjson` for JSON, `msgspec` for TOML, and `ruamel.yaml` for
YAML. YAML is instantiated as `YAML(typ="safe")`, which avoids constructing
arbitrary Python objects from YAML tags. Do not replace it with an unsafe or
round-trip loader for untrusted documents.

APICORE_Python does not depend on PyYAML. Applications that separately use
PyYAML for untrusted input must use `yaml.safe_load()` or `SafeLoader`, never
`yaml.load()` with the default or an unsafe loader. Safe object construction
does not prevent resource-exhaustion attacks, so input limits are still
required.

Keep `orjson`, `msgspec`, `ruamel.yaml`, and `ruamel.yaml.clib` current, retain a
reviewed lock file for deployments, and scan resolved dependencies for known
vulnerabilities. Review dependency updates before release rather than relying
only on the minimum versions declared in `pyproject.toml`.

### Dependency Vulnerability Policy

- Security reports for direct and transitive dependencies are evaluated against
  the versions resolved in `uv.lock`, not only the version ranges in
  `pyproject.toml`.
- Affected dependencies should be upgraded to the smallest reviewed,
  non-vulnerable compatible version. The lock file and package metadata must be
  updated together when a direct dependency constraint changes.
- Dependency security updates must pass Ruff, the complete test suite, package
  build checks, and tests for all affected formats and supported Python
  versions before release.
- If no compatible fixed dependency exists, maintainers should remove or
  disable the affected path, apply a narrowly scoped mitigation, or document
  that no safe release is currently available. A vulnerable version must not
  be described as safe merely because the vulnerable feature is uncommon.
- Release notes should identify the affected package and fixed version without
  publishing exploit details before users have had a reasonable opportunity to
  update.

## Reporting A Vulnerability

Report vulnerabilities in parser behavior, repository tools, packaging, or
dependency handling exclusively by email to `admin@sr-studio.cn` with the
subject `[APICORE_Python Security]`. No other submission channel is accepted.

Do not open a public issue or pull request containing an unpatched vulnerability,
proof of concept, sensitive configuration, or Zero-Day details. This includes,
but is not limited to, unsafe deserialization, parser resource exhaustion,
memory-safety defects in native decoding dependencies, SSRF introduced by a
repository tool, command execution, path traversal, secret disclosure, and
authorization bypass.

Include the following when available:

- Affected APICORE_Python, Python, operating system, and dependency versions.
- A minimal reproducer or proof of concept and the required input format.
- Expected and observed behavior, impact, and realistic attack prerequisites.
- Whether exploitation is known to be public or active.
- Suggested mitigations and a safe way for maintainers to contact you.

Maintainers should acknowledge receipt privately, validate severity and affected
versions, prepare tests and a fix, and coordinate a release before disclosure.
Reporters should allow maintainers a reasonable remediation period and avoid
sharing exploit details until a fixed release or mutually agreed disclosure
date is available. After users can update, maintainers may publish a GitHub
Security Advisory and credit the reporter if requested. Never include secrets,
personal data, production credentials, or data copied from systems you do not
own in a report.
