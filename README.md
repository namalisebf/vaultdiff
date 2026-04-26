# vaultdiff

> CLI tool to compare and audit differences between HashiCorp Vault secret paths across environments

---

## Installation

```bash
pip install vaultdiff
```

Or install from source:

```bash
git clone https://github.com/yourorg/vaultdiff.git && cd vaultdiff && pip install .
```

---

## Usage

Compare secret paths between two Vault environments:

```bash
vaultdiff --src https://vault.staging.example.com \
          --dst https://vault.prod.example.com \
          --path secret/myapp
```

**Example output:**

```
[~] secret/myapp/config    → DB_HOST differs (staging: db-stg-01, prod: db-prod-01)
[+] secret/myapp/feature   → present in staging, missing in prod
[-] secret/myapp/legacy    → present in prod, missing in staging
```

### Options

| Flag | Description |
|------|-------------|
| `--src` | Source Vault address |
| `--dst` | Destination Vault address |
| `--path` | Secret path to compare |
| `--token` | Vault token (or set `VAULT_TOKEN`) |
| `--output` | Output format: `text`, `json`, `csv` |
| `--recursive` | Recursively compare all sub-paths |

---

## Authentication

`vaultdiff` respects standard Vault environment variables:

```bash
export VAULT_TOKEN=<your-token>
export VAULT_ADDR=https://vault.example.com
```

---

## License

[MIT](LICENSE)