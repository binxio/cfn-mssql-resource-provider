# Custom::MSSQLLogin
The `Custom::MSSQLLogin` resource creates a MSSQL login

## Syntax
To declare this entity in your AWS CloudFormation template, use the following syntax:

```yaml
Type: Custom::MSSQLLogin
Properties:
  LoginName: String
  DefaultDatabase: String
  Password: String
  PasswordParameterName: String
  PasswordHash: String
  Server:
    URL: mssql://<user>@<host>:<port>/master
    Password: String
    PasswordParameterName: String
  ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-vpc-${AppVPC}'
```

This will execute the following SQL statement on create:
```SQL
   CREATE LOGIN [<LoginName>]
   WITH PASSWORD = '<password>',
        DEFAULT_DATABASE = [<database>]
```
The LoginName, Password and Database can all be updated in place.

## Properties
You can specify the following properties:

- `LoginName` - of the login to create (required)
- `DefaultDatabase` - for the login, default is master (optional)
- `Password` - to identify the user with.  (optional)
- `PasswordParameterName` - name of the parameter in the store containing the password of the user (optional)
- `PasswordHash` - hash of the password, to force and update of the password (optional)
- `Server` - server connection
    - `URL` - jdbc url point to the server to connect  (required)
    - `Password` - to identify the user with. (optional)
    - `PasswordParameterName` - name of the parameter in the store containing the password of the user (optional)

`Name` and Either `Password` or `PasswordParameterName` are required.

## Caveats
- The logical resource is tied to the same logical database instance, changing the Server URL
  will not create a new login on another server once it is created.

## Attributes Returned
`LoginName` - the name of the database
