## Providers ##

provider "aws" {
	alias 	= "theregion"
	region 	= "${var.region}"
}

## Data sources ##
data "archive_file" "AutoTagEC2Zip" {
    type        = "zip"
    source_file  = "../../../lambda/autoTagEC2.py"
    output_path = "AutoTagEC2.zip"
}

## Resources ##

resource "aws_cloudwatch_event_rule" "autotagwatcher" {
	provider = "aws.theregion"
	name = "AutoTagWatcher"
	description = "Auto create EC2 tags on provision"
	event_pattern = <<PATTERN
{
  "source": [
    "aws.ec2"
  ],
  "detail-type": [
    "AWS API Call via CloudTrail"
  ],
  "detail": {
    "eventSource": [
      "ec2.amazonaws.com"
    ],
    "eventName": [
      "CreateSecurityGroup",
      "CreateSubnet",
      "CreateVpc"
    ]
  }
}
PATTERN
}



resource "aws_lambda_function" "AutoTagEC2" {
	provider = "aws.theregion"
	filename = "AutoTagEC2.zip"
    source_code_hash = "${data.archive_file.AutoTagEC2Zip.output_base64sha256}"
    function_name = "AutoTagEC2-${var.region}"
	description = "Automatically add Owner, PrincipalId and NonStop tags"
	runtime = "python3.6"
	timeout = 60
    role = "${var.lambda_role}"
    handler = "autoTagEC2.lambda_handler"
    environment {
        variables {
            account = "${var.account}",
            bucket_region = "${var.bucketregion}"
            }
}
}



resource "aws_cloudwatch_event_target" "autotagwatcher" {
    provider = "aws.theregion"
	rule = "${aws_cloudwatch_event_rule.autotagwatcher.name}"
    arn = "${aws_lambda_function.AutoTagEC2.arn}"
}


resource "aws_lambda_permission" "allow_cloudwatch_to_call_AutoTagEC2" {
    provider = "aws.theregion"
	statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = "${aws_lambda_function.AutoTagEC2.function_name}"
    principal = "events.amazonaws.com"
    source_arn = "${aws_cloudwatch_event_rule.autotagwatcher.arn}"
}
