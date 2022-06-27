# Custom::SQLServerDatabase
The `Custom::SQLServerDatabase` resource creates a SQLServer database


## Syntax
To declare this entity in your AWS CloudFormation template, use the following syntax:

```yaml
Type: Custom::SQLServerDatabase
Properties:
  Name: String
  Server:
    URL: sqlserver://<user>@<host>:<port>/master
    Password: password
    PasswordParameterName: name
  ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-sqlserver-resource-provider-vpc-${AppVPC}'
```

## Properties
You can specify the following properties:

- `Name` -  of the database to create (required)
- `Server` - server connection
  - `URL` - jdbc url point to the server to connect  (required)
  - `Password` - to identify the user with. (required or PasswordParameterName)
  - `PasswordParameterName` - name of the parameter in the store containing the password of the user

Changing the Server URL will not create a new database once it is created.

## Attributes Returned
`Name` - the name of the database
