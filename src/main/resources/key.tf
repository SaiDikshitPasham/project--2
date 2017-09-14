## EC2 Key Validation Terraform project. This project uses remote state to store the details of resources terraform has
## created. All state should be stored in a remote backend (s3) to allow collaboration across users
## More details on Terraform state can be found here: https://www.terraform.io/docs/state/index.html
## More details on Terraform remote state here: https://www.terraform.io/docs/state/remote.html


## Data sources ##


## Resources ##
resource "aws_s3_bucket" "GlobalVariablesBucket" {
  bucket = "global-variables-${var.account}-${var.region}"
  acl    = "private"
  logging {
  target_bucket = "s3-logging.${var.account}.${var.region}.tsys"
  target_prefix = "s3/"
  }
}

resource "aws_s3_bucket_object" "keys" {
  depends_on = ["aws_s3_bucket.GlobalVariablesBucket"]
  bucket = "${aws_s3_bucket.GlobalVariablesBucket.id}"
  key    = "tagging-ec2-instance-all-keys.txt"
  source = "Tags/ec2-all-keys.txt"
  server_side_encryption = "AES256"
}

resource "aws_s3_bucket_object" "valuedefaults" {
  depends_on = ["aws_s3_bucket.GlobalVariablesBucket"]
  bucket = "${aws_s3_bucket.GlobalVariablesBucket.id}"
  key    = "tagging-ec2-instance-default-values.txt"
  source = "Tags/ec2-all-values.txt"
  server_side_encryption = "AES256"
}


resource "aws_iam_role" "Lambda_Role_For_TagValidator" {
    name = "lambdaTagValidatorRole"
    assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "Lambda_Policy_For_TagValidator" {
    name = "lambdaTagValidatorPolicy"
    role = "${aws_iam_role.Lambda_Role_For_TagValidator.id}"
    policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cloudtrail:LookupEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateTags",
                "ec2:DeleteTags",
                "ec2:Describe*"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:List*",
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::${aws_s3_bucket.GlobalVariablesBucket.id}/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail"
            ],
            "Resource":"*",
                "Condition": {
                    "StringEquals": {
                        "ses:FromAddress": "AWS-Alerts-NoReply@tsys.com"
                }
            }
         }
    ]
}
EOF
}

module "ec2tagvalidator-virginia" {
	source 				= "git::http://git.tpp.tsysecom.com:8080/scm/enaws/iac-framework-modules.git//tagkeyvalidator"
# Local source location added for local testing before upload of module to repo. 
#	source				= "../../../../iac-framework-modules/tagkeyvalidator"
	region 			 	= "us-east-1"
	lambda_role			= "${aws_iam_role.Lambda_Role_For_TagValidator.arn}"
    account             = "${var.account}"
    bucketregion        = "${var.region}"

}


module "ec2tagvalidator-oregon" {
	source 				= "git::http://git.tpp.tsysecom.com:8080/scm/enaws/iac-framework-modules.git//tagkeyvalidator"
# Local source location added for local testing before upload of module to repo. 
#	source				= "../../../../iac-framework-modules/tagkeyvalidator"
	region 			 	= "us-west-2"
	lambda_role			= "${aws_iam_role.Lambda_Role_For_TagValidator.arn}"
    account             = "${var.account}"
    bucketregion        = "${var.region}"
}

module "ec2tagvalidator-frankfurt" {
	source 				= "git::http://git.tpp.tsysecom.com:8080/scm/enaws/iac-framework-modules.git//tagkeyvalidator"
# Local source location added for local testing before upload of module to repo. 
#	source				= "../../../../iac-framework-modules/tagkeyvalidator"
	region 			 	= "eu-central-1"
	lambda_role			= "${aws_iam_role.Lambda_Role_For_TagValidator.arn}"
    account             = "${var.account}"
    bucketregion        = "${var.region}"
}

module "ec2tagvalidator-mumbai" {
	source 				= "git::http://git.tpp.tsysecom.com:8080/scm/enaws/iac-framework-modules.git//tagkeyvalidator"
# Local source location added for local testing before upload of module to repo. 
#	source				= "../../../../iac-framework-modules/tagkeyvalidator"
	region 			 	= "ap-south-1"
	lambda_role			= "${aws_iam_role.Lambda_Role_For_TagValidator.arn}"
    account             = "${var.account}"
    bucketregion        = "${var.region}"
}
