# Custom::SQLServerLogin
The `Custom::SQLServerLogin` resource creates a SQLServer login

## Syntax
To declare this entity in your AWS CloudFormation template, use the following syntax:

```yaml
Type: Custom::SQLServerLogin
Properties:
  LoginName: String
  DefaultDatabase: String
  Password: String
  PasswordParameterName: String
  Server:
    URL: sqlserver://<user>@<host>:<port>/<database>
    Password: String
    PasswordParameterName: String
  ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-sqlserver-resource-provider-vpc-${AppVPC}'
```

## Properties
You can specify the following properties:

- `LoginName` - of the login to create (required)
- `DefaultDatabase` - for the login, default is master (optional)
- `Password` - to identify the user with.  (optional)
- `PasswordParameterName` - name of the parameter in the store containing the password of the user (optional)
- `Server` - server connection
    - `URL` - jdbc url point to the server to connect  (required)
    - `Password` - to identify the user with. (optional)
    - `PasswordParameterName` - name of the parameter in the store containing the password of the user (optional)

`Name` and Either `Password` or `PasswordParameterName` are required.

Changing the Server URL will not create a new user once it is created.

## Attributes Returned
`LoginName` - the name of the database
