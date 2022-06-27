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

- `LoginName` - of the login to create
- `DefaultDatabase` - for the login, default is master
- `Password` - to identify the user with. 
- `PasswordParameterName` - name of the parameter in the store containing the password of the user

`Name` and Either `Password` or `PasswordParameterName` is required.

## Attributes Returned
`LoginName` - the name of the database
