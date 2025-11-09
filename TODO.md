tables
======

```sql
CREATE TABLE IF NOT EXISTS manifests (
    repo TEXT NOT NULL,
    rev TEXT NOT NULL,
    manifest TEXT NOT NULL,
    PRIMARY KEY (repo, rev)
);

-- `clones` -- ephemeral but helpful for pre-commit.ci to pre-seed ?
CREATE TABLE IF NOT EXISTS clones (
    repo TEXT NOT NULL,
    rev TEXT NOT NULL,
    path TEXT NOT NULL,
    PRIMARY KEY (repo, rev)
);

CREATE TABLE IF NOT EXISTS installs (
    repo TEXT NOT NULL,
    rev TEXT NOT NULL,
    language TEXT NOT NULL,
    language_version TEXT NOT NULL,
    additional_dependencies TEXT NOT NULL,
    path TEXT NOT NULL,
    PRIMARY KEY (repo, rev, language, language_version, additional_dependencies)
);
```
