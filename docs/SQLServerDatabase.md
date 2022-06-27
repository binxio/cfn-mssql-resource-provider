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

- `Name` - of the database to create
 - `Password` - to identify the user with. 
  - `PasswordParameterName` - name of the parameter in the store containing the password of the user

`Name` and Either `Password` or `PasswordParameterName` is required.

## Attributes Returned
`Name` - the name of the database
