# Custom::SQLServerUser
The `Custom::PostgresSQLUser` resource creates a SQLServer database user.


## Syntax
To declare this entity in your AWS CloudFormation template, use the following syntax:

```yaml
Type: Custom::SQLServerUser
Properties:
  Name: String
  LoginName: String
  DefaultSchema: String
  Server:
    URL: sqlserver://<user>@<host>:<port>/<database>
    Password: String
    PasswordParameterName: String
  ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-sqlserver-resource-provider-vpc-${AppVPC}'
```

## Properties
You can specify the following properties:

- `UserName` - of the user to create (required)
- `LoginName` - to create the user for (required)
- `DefaultSchema` - for the user, default `dbo` (optional)
- `Server` - server connection
    - `URL` - jdbc url point to the server to connect  (required)
    - `Password` - to identify the user with. (optional)
    - `PasswordParameterName` - name of the parameter in the store containing the password of the user (optional)

Either `Password` or `PasswordParameterName` is required.

Changing the Server URL will not create a new user.

## Attributes Returned
`UserName` - of the user
