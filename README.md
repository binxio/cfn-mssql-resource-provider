# cfn-mssql-resource-provider

Although CloudFormation is very good in creating Microsoft MSSQL database servers with Amazon RDS, the mundane task of creating databases, logins and users is not supported. 
This custom MSSQL resource provider automates the provisioning of MSSQL databases, login's and users.


## How does it work?
It is quite easy: you specify a CloudFormation resource of the [Custom::MSSQLLogin](docs/MSSQLUser.md), as follows:

```yaml
  KongDatabase:
    Type: Custom::MSSQLDatabase
    DeletionPolicy: Retain
    UpdateReplacePolicy: Retain
    Properties:
      Name: kong
      Server:
        URL: !Sub 'mssql://sa@${Database.Endpoint.Address}:${Database.Endpoint.Port}'
        PasswordParameterName: !Sub '/${AWS::StackName}/mssql/sa/password'
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-${VPC}'

  KongLogin:
    Type: Custom::MSSQLLogin
    Properties:
      LoginName: kong
      DefaultDatabase: !GetAtt KongDatabase.Name
      PasswordParameterName: !Sub '/${AWS::StackName}/mssql/kong/password'
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-${VPC}'
      Server:
        URL: !Sub 'mssql://sa@${Database.Endpoint.Address}:${Database.Endpoint.Port}'
        PasswordParameterName: !Sub '/${AWS::StackName}/mssql/sa/password'

  KongUser:
    Type: Custom::MSSQLUser
    Properties:
      UserName: kong
      LoginName: !GetAtt KongLogin.LoginName
      Server:
        URL: !Sub 'mssql://${Database.Endpoint.Address}:${Database.Endpoint.Port}/${KongDatabase.Name}'
        PasswordParameterName: !Sub '/${AWS::StackName}/mssql/sa/password'
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-${VPC}'

  KongDatabaseGrant:
    Type: Custom::MSSQLDatabaseGrant
    Properties:
      Permission: ALL
      UserName: !GetAtt KongUser.UserName
      Database: !GetAtt KongDatabase.Name
      Server:
        URL: !Sub 'mssql://${Database.Endpoint.Address}:${Database.Endpoint.Port}/${KongDatabase.Name}'
        PasswordParameterName: !Sub '/${AWS::StackName}/mssql/sa/password'
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-mssql-resource-provider-${VPC}'

```
Cloudformation creates the database 'kong', the login 'kong' and the user 'kong' in the database.


## Installation
To install this Custom Resource, type:

```sh
export VPC_ID=$(aws ec2  --output text --query 'Vpcs[?IsDefault].VpcId' describe-vpcs)
export SUBNET_IDS=$(aws ec2 describe-route-tables \
                       --filters Name=vpc-id,Values=$VPC_ID \
                       --query 'join(`,`, RouteTables[?Routes[?GatewayId == null]].Associations[].SubnetId)' \
		       --output text)
export SG_ID=$(aws ec2 --output text --query "SecurityGroups[*].GroupId" \
			describe-security-groups --group-names default  --filters Name=vpc-id,Values=$VPC_ID)

aws cloudformation create-stack \
	--capabilities CAPABILITY_IAM \
	--stack-name cfn-mssql-resource-provider \
	--template-body file://cloudformation/cfn-resource-provider.yaml  \
	--parameters \
	            ParameterKey=VPC,ParameterValue=$VPC_ID \
	            ParameterKey=Subnets,ParameterValue=$SUBNET_IDS \
                ParameterKey=SecurityGroup,ParameterValue=$SG_ID

aws cloudformation wait stack-create-complete  --stack-name cfn-mssql-resource-provider 
```
Note that this uses the default VPC, private subnets and security group. As the Lambda functions needs to connect to the database. You will need to 
install this custom resource provider for each vpc that you want to be able to create database users.

This CloudFormation template will use our pre-packaged provider from `s3://binxio-public/lambdas/cfn-mssql-resource-provider-0.2.1.zip`.

If you have not done so, please install the secret provider too.

```
aws cloudformation create-stack \
   --stack-name cfn-secret-provider \
   --capabilities CAPABILITY_IAM \
   --template-url https://binxio-public-eu-central-1.s3.eu-central-1.amazonaws.com/lambdas/cfn-secret-provider-1.4.4.yaml 
aws cloudformation wait stack-create-complete --stack-name cfn-secret-provider
```

## Demo
To install the simple sample of the Custom Resource, type:

```sh
aws cloudformation create-stack --stack-name cfn-database-user-provider-demo \
	--template-body file://cloudformation/demo-stack.yaml
aws cloudformation wait stack-create-complete  --stack-name cfn-database-user-provider-demo
```
It will create a MSSQL database too, so it is quite time consuming...

## Conclusion
With this solution MSSQL users and databases can be provisioned just like a database, while keeping the
passwords safely stored in the AWS Parameter Store.
