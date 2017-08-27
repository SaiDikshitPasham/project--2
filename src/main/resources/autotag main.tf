## Terraform Module. 
# EC2 AutoTag - At a scheduled time a Lambda function creates the tags for all instances within region
# The autoTag.zip files are zipped functions built from here:
# http://git.tpp.tsysecom.com:8080/projects/ENAWS/repos/iac-framework/browse/lambda

## Providers ##

provider "aws" {
	alias 	= "theregion"
	region 	= "${var.region}"
}

## Data sources ##
data "archive_file" "AutoTagZip" {
    type        = "zip"
    source_file  = "../../../lambda/autoTag.py"
    output_path = "AutoTag.zip"
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
      "RunInstances",
      "CreateVolume",
      "CreateSnapshot",
      "CreateImage"
    ]
  }
}
PATTERN
}



resource "aws_lambda_function" "AutoTagBasic" {
	provider = "aws.theregion"
	filename = "AutoTag.zip"
    source_code_hash = "${data.archive_file.AutoTagZip.output_base64sha256}"
    function_name = "AutoTagBasic-${var.region}"
	description = "Automatically add Owner, PrincipalId and NonStop tags"
	runtime = "python3.6"
	timeout = 60
    role = "${var.lambda_role}"
    handler = "autoTag.lambda_handler"
}



resource "aws_cloudwatch_event_target" "autotagwatcher" {
    provider = "aws.theregion"
	rule = "${aws_cloudwatch_event_rule.autotagwatcher.name}"
    arn = "${aws_lambda_function.AutoTagBasic.arn}"
}


resource "aws_lambda_permission" "allow_cloudwatch_to_call_AutoTagBasic" {
    provider = "aws.theregion"
	statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = "${aws_lambda_function.AutoTagBasic.function_name}"
    principal = "events.amazonaws.com"
    source_arn = "${aws_cloudwatch_event_rule.autotagwatcher.arn}"
}
