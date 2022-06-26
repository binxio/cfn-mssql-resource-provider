from urllib.parse import urlparse, ParseResult, unquote, parse_qs

from botocore.exceptions import ClientError

request_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "oneOf": [
        {"required": [ "URL", "Password"]},
        {"required": [ "URL", "PasswordParameterName"]}
    ],
    "properties": {
        "URL": {
            "type": "string",
            "pattern": "sqlserver://.*",
            "description": "database connection url"
        },
        "Password": {
            "type": "string",
            "description": "the password of the sa"
        },
        "PasswordParameterName": {
            "type": "string",
            "description": "the name of the sa password in the Parameter Store"
        }
    }
}

def from_url(jdbc_url: str, password = None) -> dict:
    """
    create pymssql connection information from `jdbc_url`. if no password was specified and
    `password` will be used.
    default user is `sa`. default port is 1433. default database is `master`.

    >>> from_url("sqlserver://mssql") # default user, port and database
    {'host': 'mssql', 'port': 1433, 'user': 'sa', 'database': 'master'}
    >>> from_url("//mssql") # no scheme
    {'host': 'mssql', 'port': 1433, 'user': 'sa', 'database': 'master'}
    >>> from_url("sqlserver://dbo@mssql") # alternate user
    {'host': 'mssql', 'port': 1433, 'user': 'dbo', 'database': 'master'}
    >>> from_url("sqlserver://dbo@mssql/thisone") # alternate database
    {'host': 'mssql', 'port': 1433, 'user': 'dbo', 'database': 'thisone'}
    >>> from_url("sqlserver://dbo@mssql:1444/thisone") # alternate port
    {'host': 'mssql', 'port': 1444, 'user': 'dbo', 'database': 'thisone'}
    >>> from_url("sqlserver://dbo:p%40ssword@mssql:1444/thisone") # with password
    {'host': 'mssql', 'port': 1444, 'user': 'dbo', 'database': 'thisone', 'password': 'p@ssword'}
    >>> from_url("sqlserver://dbo:p%40ssword@mssql:1444/thisone?charset=utf-8") # with password
    {'host': 'mssql', 'port': 1444, 'user': 'dbo', 'database': 'thisone', 'password': 'p@ssword', 'charset': 'utf-8'}
    >>> from_url("https://mssql") # invalid scheme
    Traceback (most recent call last):
    ...
    ValueError: unsupport scheme in url
    >>> from_url("sqlserver://mssql", "MyPassWord") # default user, port and database
    {'host': 'mssql', 'port': 1433, 'user': 'sa', 'database': 'master', 'password': 'MyPassWord'}pyth

    """
    url: ParseResult = urlparse(jdbc_url)
    query = parse_qs(url.query) if url.query else {}

    if url.scheme and url.scheme != 'sqlserver':
        raise ValueError('unsupport scheme in url')

    connect_info = {
        'host': url.hostname,
        'port': url.port if url.port else 1433,
        'user': unquote(url.username) if url.username else "sa",
        'database': url.path.strip("/") if url.path else "master",
    }

    if url.password:
        connect_info['password'] = unquote(url.password)
    elif password:
        connect_info['password'] = password

    if 'charset' in query:
        connect_info['charset'] = query['charset'][0]

    return connect_info


def get_ssm_password(ssm, name) -> str:
    try:
        response = ssm.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except ClientError as e:
        raise ValueError('Could not obtain password using name {}, {}'.format(name, e))


def _get_password_from_dict(properties: dict, ssm) -> str:
    if 'Password' in properties:
        return properties.get('Password')
    else:
        response = ssm.get_parameter(Name=properties.get('PasswordParameterName'), WithDecryption=True)
        return response['Parameter']['Value']