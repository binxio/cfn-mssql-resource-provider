# Custom::MSSQLUser
The `Custom::MSSQLUser` resource creates a MSSQL database user.

## Syntax
To declare this entity in your AWS CloudFormation template, use the following syntax:

```yaml
Type: Custom::MSSQLUser
Properties:
  Name: String
  LoginName: String
  DefaultSchema: String
  Server:
    URL: mssql://<user>@<host>:<port>/<database>
    Password: String
    PasswordParameterName: String
  ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-vpc-${AppVPC}'
```
This will execute the following SQL statement on create:
```SQL
   CREATE USER [<UserName>]
   FOR LOGIN = '<LoginName>',
   WITH DEFAULT_SCHEMA = [<DefaultSchema>]
```
The Name, LoginName and DefaultSchema can all be updated in place. The Server must continue to 
point to the same logical instance.  



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

# Caveats
- The logical resource is tied to the same logical database instance, changing the Server URL
  will not create a new user on another server once it is created. Changing the database in the
  URL will move it to the other logical database.

## Attributes Returned
`UserName` - of the user
