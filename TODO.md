### tool resolutions

- deterministic `node lts`
- updateable

```sql
CREATE TABLE IF NOT EXISTS tool_resolutions (
    tool TEXT NOT NULL,
    version TEXT NOT NULL,
    resolved TEXT NOT NULL,
    PRIMARY KEY (tool, version)
);
```

```console
$ pre-commit tools autoupdate [--only ...]  # update config override versions
$ pre-commit tools resolve [--only ...]  # update resolved versions
```

```yaml
# in .pre-commit-config.yaml
tool_resolution:
    node: {lts: '24.2.0'}
```
