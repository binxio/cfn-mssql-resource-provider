# cfn-sqlserver-resource--provider

Although CloudFormation is very good in creating Microft SQLServer database servers with Amazon RDS, the mundane task of creating database, logins and users is not supported. 

This custom SQLServer user provider automates the provisioning of SQLServer databases, login's and users.


## How does it work?
It is quite easy: you specify a CloudFormation resource of the [Custom::SQLServerUser](docs/SQLServerUser.md), as follows:

```yaml
  KongUser:
    Type: Custom::SQLServerUser
    DependsOn: KongPassword
    Properties:
      User: kong
      PasswordParameterName: /sqlserver/kong/password
      WithDatabase: true
      WithPublicSchema: false
      DeletionPolicy: Retain 
      Database:                   # the server to create the new user or database in
        Host: sqlserver
        Port: 1433
        DBName: master
        User: sa
        PasswordParameterName: /sqlserver/sa/password                # put your root password is in the parameter store
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxioio-cfn-sqlserver-resource--provider-vpc-${AppVPC}'

   KongPassword:
    Type: Custom::Secret
    Properties:
      Name: /sqlserver/kong/PGPASSWORD
      KeyAlias: alias/aws/ssm
      Alphabet: _`'~-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
      Length: 30
      ServiceToken: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:binxio-cfn-secret-provider'
```

After the deployment, the Postgres user 'kong' has been created together with a matching database 'kong'. The password for the root database user has been obtained by querying the Parameter `/postgres/root/PGPASSWORD`.  If you just want to create a user with which you can login to the SQLServer database server, without a database, specify `WithDatabase` as `false`.  If `WithPublicSchema` is set to false, permission to create in the schema `public` is revoked.

The RetainPolicy by default is `Retain`. This means that the login to the database is disabled. If you specify drop, it will be dropped and your data will be lost.


## Installation
To install this Custom Resource, type:

```sh
export VPC_ID=$(aws ec2  --output text --query 'Vpcs[?IsDefault].VpcId' describe-vpcs)
export SUBNET_ID=$(aws ec2 --output text --query Subnets[0].SubnetId \
			describe-subnets --filters Name=vpc-id,Values=$VPC_ID)
export SG_ID=$(aws ec2 --output text --query "SecurityGroups[*].GroupId" \
			describe-security-groups --group-names default  --filters Name=vpc-id,Values=$VPC_ID)

aws cloudformation create-stack \
	--capabilities CAPABILITY_IAM \
	--stack-name cfn-sqlserver-resource--provider \
	--template-body file://cloudformation/cfn-custom-resource-provider.json  \
	--parameters \
	            ParameterKey=VPC,ParameterValue=$VPC_ID \
	            ParameterKey=Subnet,ParameterValue=$SUBNET_ID \
                ParameterKey=SecurityGroup,ParameterValue=$SG_ID

aws cloudformation wait stack-create-complete  --stack-name cfn-sqlserver-resource--provider 
```
Note that this uses the default VPC, subnet and security group. As the Lambda functions needs to connect to the database. You will need to 
install this custom resource provider for each vpc that you want to be able to create database users.

This CloudFormation template will use our pre-packaged provider from `s3://binxio-public/lambdas/cfn-sqlserver-resource--provider-0.5.9.zip`.

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
	--template-body file://cloudformation/demo-stack.json
aws cloudformation wait stack-create-complete  --stack-name cfn-database-user-provider-demo
```
It will create a postgres database too, so it is quite time consuming...

## Conclusion
With this solution SQLServer users and databases can be provisioned just like a database, while keeping the
passwords safely stored in the AWS Parameter Store.
