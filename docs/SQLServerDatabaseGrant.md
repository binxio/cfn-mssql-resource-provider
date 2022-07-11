# Custom::MSSQLDatabaseGrant
The `Custom::MSSQLDatabaseGrant` resource grants a database permission to a user.

## Syntax
To declare this entity in your AWS CloudFormation template, use the following syntax:

```yaml
Type: Custom::MSSQLDatabaseGrant
Properties:
  Permission: String
  Database: String
  UserName: String
  Server:
    URL: mssql://<user>@<host>:<port>/master
    Password: String
    PasswordParameterName: String
  ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-vpc-${AppVPC}'
```
This will execute the following SQL statement on create or update:

```SQL
GRANT <Permission> ON DATABASE::[<database>] TO [<username>]
```

## Properties
You can specify the following properties:

- `Permission` - to grant on the database (required)
- `Database` - on which the permission is granted (optional)
- `UserName` - to grant the permission to (required)
- `Server` - server connection
    - `URL` - jdbc url point to the server to connect  (required)
    - `Password` - to identify the user with. (optional)
    - `PasswordParameterName` - name of the parameter in the store containing the password of the user (optional)

Either `Password` or `PasswordParameterName` is required. 

# Caveats
- The logical resource is tied to the same logical database instance, changing the Server URL
  will not create a new grant on another server once it is created. 

