# cfn-mssql-resource-provider

Although CloudFormation is very good in creating Microsoft MSSQL database servers with  
Amazon RDS, the mundane task of creating databases, logins and users is not supported.  
This custom MSSQL resource provider automates the provisioning of MSSQL databases, 
login's and users.

## How do I create a MSSQL Database?
To create a logical database on a Microsoft SQLServer using Cloudformation, you can use the  
following custom resource:
```yaml
  KongDatabase:
    Type: Custom::MSSQLDatabase
    DeletionPolicy: Retain
    Properties:
      Name: kong
      Server:
        URL: !Sub 'mssql://sa@${Database.Endpoint.Address}:${Database.Endpoint.Port}'
        PasswordParameterName: !GetAtt DBPassword.ParameterName
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-${VPC}'
```
You just specify the name of the database and the server on which it is hosted. The custom provider  
does suport renaming of the  database, but you cannot "move" it another server.


## How do I create a MSSQL User?
Although there are 13 types of users on Microsoft SQLServer, the provider only  
creates a database user for a server authentication login. An example is shown below, using
the [Custom::MSSQLLogin](docs/MSSQLLogin.md) and 
[Custom::MSSQLUser](docs/MSSQLUser.md) resources.

```yaml
  KongLogin:
    Type: Custom::MSSQLLogin
    Properties:
      LoginName: kong
      DefaultDatabase: !GetAtt KongDatabase.Name
      PasswordParameterName: !GetAtt KongPassword.ParameterName
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-${VPC}'
      Server:
        URL: !Sub 'mssql://sa@${Database.Endpoint.Address}:${Database.Endpoint.Port}'
        PasswordParameterName: !Ref DBPassword.ParameterName

  KongUser:
    Type: Custom::MSSQLUser
    Properties:
      UserName: kong
      LoginName: !GetAtt KongLogin.LoginName
      Server:
        URL: !Sub 'mssql://${Database.Endpoint.Address}:${Database.Endpoint.Port}/${KongDatabase.Name}'
        PasswordParameterName: !GetAtt DBPassword.ParameterName
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-${VPC}'
```

The custom provider does suport renaming of the login name and the username. In addition, you
can move the user to another database by changing the database name in the server URL.  
but you cannot them to another server. 

Finally, you use the [Custom::MSSQLDatabaseGrant](docs/MSSQLDatabaseGrant.md) to grant permissions to the user in the database.  
In this case we grant the user `ALL` permissions on the database, so that the development team can manage the database  
schema themselves.

```yaml
  KongDatabaseGrant:
    Type: Custom::MSSQLDatabaseGrant
    Properties:
      Permission: ALL
      UserName: !GetAtt KongUser.UserName
      Database: !GetAtt KongDatabase.Name
      Server:
        URL: !Sub 'mssql://${Database.Endpoint.Address}:${Database.Endpoint.Port}/${KongDatabase.Name}'
        PasswordParameterName: !GetAtt DBPassword.ParameterName
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-${VPC}'
```
That is all there is to it!

## Installation
To install this SQLServer custom resource provider, type:

```sh
read -p "VPC ID:" VPC_ID
read -p "private subnet ids:" SUBNET_IDS
read -p "default security group:" SG_ID
aws cloudformation deploy \
	--capabilities CAPABILITY_IAM \
	--stack-name cfn-mssql-resource-provider \
	--template-file ./cloudformation/cfn-resource-provider.yaml  \
	--parameter-overrides \
	  "VPC=$VPC_ID" "Subnets=$SUBNET_IDS" "SecurityGroup=$SG_ID"
```
As the provider needs to connect to the database server, we connect the Lambda function on private  
subnets of the VPC and provide it with a security group which grants access. Install the custom resource 
provider on each vpc that you want to be able to create databases, logins and users.

This CloudFormation template will use our pre-packaged provider from `463637877380.dkr.ecr.eu-central-1.amazonaws.com/xebia/cfn-mssql-resource-provider:0.0.0`.

## Demo
To install the simple sample of the Custom Resource provider, type:

```sh
## install the secret provider

curl -o /tmp/cfn-secret-provider.yaml \
	-sS https://raw.githubusercontent.com/binxio/cfn-secret-provider/refs/tags/v3.0.1/cloudformation/cfn-resource-provider.yaml

aws cloudformation deploy \
--stack-name cfn-secret-provider \
--capabilities CAPABILITY_IAM \
--template-file /tmp/cfn-secret-provider.yaml

aws cloudformation deploy --stack-name cfn-database-user-provider-demo \
	--template-file ./cloudformation/demo-stack.yaml
```
It will create a Microsoft SQLServer database server too, it will take quiet some time.

## Conclusion
With this solution, you can create Microsoft SQLServer databases and users with Cloudformation.  
You can host multiple teams on the same server by providing them with their own database  
and database users, while you can share the passwords via the AWS Parameter Store.
