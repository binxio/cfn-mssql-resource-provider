# test
Before you can test this code, start a local Microsoft SQLServer docker container.

```
docker run --cap-add SYS_PTRACE \
    -e 'ACCEPT_EULA=1' \
    -e 'MSSQL_SA_PASSWORD=P@ssW0rd' \
    -p 1444:1433 \
    -d mcr.microsoft.com/azure-sql-edge
```
