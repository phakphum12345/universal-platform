# Geometry Batch Validation

The repository-root geometry command validates multiple CAD-neutral primitive geometry snapshots in one invocation.

## Install

From the repository root:

\`\`\`sh
python -m pip install -e ".[dev]"
\`\`\`

The package entry point is also installed as \`up-geometry\`.

## Terminal usage

Validate multiple files:

\`\`\`sh
up-geometry validate models/part-a.geometry.json models/part-b.geometry.json
\`\`\`

The same command works without installing the console script:

\`\`\`sh
python -m universal_platform.engineering.geometry_batch validate models/ --recursive
\`\`\`

Directory inputs search one level by default. Add \`--recursive\` to search nested directories. Explicit files and glob patterns are supported. Directory scans omit JSON Schema files and the \`schemas/\` tree; pass a geometry snapshot file explicitly if needed.

Write a machine-readable report:

\`\`\`sh
up-geometry validate models/ --recursive --format json --report build/geometry-report.json
\`\`\`

## Safe repair mode

\`\`\`sh
up-geometry validate models/ --recursive --fix
\`\`\`

Repair mode only canonicalizes JSON serialization for snapshots that already pass semantic geometry validation. It creates a sibling \`.bak\` file before replacing a non-canonical file and refuses to overwrite an existing backup. It does not guess coordinates, close loops, move holes, alter units, or change topology. Semantic geometry errors remain FAIL and require an explicit engineering decision.

## Exit codes and evidence

- \`0\`: every discovered input passed.
- \`1\`: one or more files failed validation or safe repair.
- \`2\`: invalid command usage or no input files discovered.

Every file is processed even when an earlier file fails. The summary reports total, PASS and FAIL counts; an unsupported or invalid geometry snapshot is never silently counted as PASS.

The validator uses \`PrimitiveGeometryModel.from_dict\` and therefore currently validates the repository's CAD-neutral primitive geometry snapshot contract (schema versions 1.0 and 1.1). It is not a general STEP, STL, 3MF, arbitrary B-rep, mesh, or manufacturing-quality validator.
