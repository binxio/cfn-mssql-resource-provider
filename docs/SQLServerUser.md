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

- `UserName` - of the user to create
- `LoginName` - to create the user for
- `DefaultSchema` - for the user, default `dbo`
- `URL` - database URL with username, host port and database
- `Password` - password to connect to the database
- `PasswordParameterName` - name of the parameter in the store containing the password of the user

Either `Password` or `PasswordParameterName` is required.

## Attributes Returned
`UserName` - of the user

