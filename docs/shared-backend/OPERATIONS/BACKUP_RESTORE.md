# Backup and Restore

## Scope
Back up each domain's database independently and include only the artifacts/configuration required to restore service. Keep secrets outside ordinary backups unless encrypted and explicitly required.

## Procedure
1. Identify the data owner and stop or quiesce writes safely.
2. Create a timestamped backup.
3. Verify file integrity and metadata.
4. Restore to an isolated test location.
5. Apply/check migrations as documented.
6. Start the service and run health and domain smoke tests.
7. Record the tested backup date, source SHA, restore result, and duration.

A backup is not accepted as reliable until a restore test succeeds. Define retention and recovery objectives with the data owner.
