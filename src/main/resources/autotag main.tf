terraform {
	required_version = ">= 0.9.6"
	backend "s3" {
		bucket = "iac-framework"
		key    = "autotag.tfstate"
		region = "eu-west-1"
		encrypt	= "true"
	}
}

## Providers ##
provider "aws" {
  region = "${var.region}"
}

## Data sources ##


## Resources ##
resource "aws_s3_bucket_object" "mandatory-ec2-keys" {
  depends_on = ["aws_s3_bucket.GlobalVariablesBucket"]
  bucket = "${aws_s3_bucket.GlobalVariablesBucket.id}"
  key    = "tagging-ec2-mandatory-keys.txt"
  source = "Tags/ec2-mandatory-keys.txt"
  server_side_encryption = "AES256"
}

resource "aws_s3_bucket_object" "mandatory-ec2-valuedefaults" {
  depends_on = ["aws_s3_bucket.GlobalVariablesBucket"]
  bucket = "${aws_s3_bucket.GlobalVariablesBucket.id}"
  key    = "tagging-ec2-mandatory-key-values.txt"
  source = "Tags/ec2-mandatory-key-values.txt"
  server_side_encryption = "AES256"
}

resource "aws_iam_role" "lamdba_role" {
    name = "lambdaAutoTagRole"
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

resource "aws_iam_role_policy" "lambda_policy" {
    name = "lambdaAutoTagPolicy"
    role = "${aws_iam_role.lamdba_role.id}"
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
                "ec2:Describe*",
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
        }
    ]
}
EOF
}

module "ec2autotag-virginia" {
	source 				= "git::http://git.tpp.tsysecom.com:8080/scm/enaws/iac-framework-modules.git//autotag"
# Local source location added for local testing before upload of module to repo. 
#	source				= "../../../../iac-framework-modules/autotag"
	region 			 	= "us-east-1"
	lambda_role			= "${aws_iam_role.lamdba_role.arn}"
    account             = "${var.account}"
    bucketregion        = "${var.region}"
}


module "ec2autotag-oregon" {
	source 				= "git::http://git.tpp.tsysecom.com:8080/scm/enaws/iac-framework-modules.git//autotag"
# Local source location added for local testing before upload of module to repo. 
#	source				= "../../../../iac-framework-modules/autotag"
	region 			 	= "us-west-2"
	lambda_role			= "${aws_iam_role.lamdba_role.arn}"
    account             = "${var.account}"
    bucketregion        = "${var.region}"
}

module "ec2autotag-frankfurt" {
	source 				= "git::http://git.tpp.tsysecom.com:8080/scm/enaws/iac-framework-modules.git//autotag"
# Local source location added for local testing before upload of module to repo. 
#	source				= "../../../../iac-framework-modules/autotag"
	region 			 	= "eu-central-1"
	lambda_role			= "${aws_iam_role.lamdba_role.arn}"
    account             = "${var.account}"
    bucketregion        = "${var.region}"
}

module "ec2autotag-mumbai" {
	source 				= "git::http://git.tpp.tsysecom.com:8080/scm/enaws/iac-framework-modules.git//autotag"
# Local source location added for local testing before upload of module to repo. 
#	source				= "../../../../iac-framework-modules/autotag"
	region 			 	= "ap-south-1"
	lambda_role			= "${aws_iam_role.lamdba_role.arn}"
    account             = "${var.account}"
    bucketregion        = "${var.region}"
}