# Custom::MSSQLDatabase
The `Custom::MSSQLDatabase` resource creates a MSSQL database


## Syntax
To declare this entity in your AWS CloudFormation template, use the following syntax:

```yaml
Type: Custom::MSSQLDatabase
Properties:
  Name: String
  Server:
    URL: mssql://<user>@<host>:<port>/master
    Password: password
    PasswordParameterName: name
  ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-vpc-${AppVPC}'
```

This will execute the following SQL statement on create:
```SQL
   CREATE DATABASE [<Name>]
```


## Properties
You can specify the following properties:

- `Name` -  of the database to create (required)
- `Server` - server connection
  - `URL` - jdbc url point to the server to connect  (required)
  - `Password` - to identify the user with. (required or PasswordParameterName)
  - `PasswordParameterName` - name of the parameter in the store containing the password of the user

## Caveats
- The logical resource is tied to the same logical database instance, changing the Server URL 
  will not create a new database on another server once it is created.

## Attributes Returned
`Name` - the name of the database
