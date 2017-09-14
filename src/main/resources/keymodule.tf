## Providers ##

provider "aws" {
	alias 	= "theregion"
	region 	= "${var.region}"
}

## Data sources ##
data "archive_file" "TagKeyValidatorZip" {
    type        = "zip"
    source_file  = "../../../lambda/tagKeyValidator.py"
    output_path = "TagKeyValidator.zip"
}

## Resources ##

resource "aws_cloudwatch_event_rule" "tagkeywatcher" {
	provider = "aws.theregion"
	name = "TagKeyChangeWatcher"
	description = "Checks for CreateTags API call"
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
      "CreateTags"
    ]
  }
}
PATTERN
}



resource "aws_lambda_function" "TagKeyValidator" {
	provider = "aws.theregion"
	filename = "TagKeyValidator.zip"
    source_code_hash = "${data.archive_file.TagKeyValidatorZip.output_base64sha256}"
    function_name = "TagKeyValidator-${var.region}"
	description = "Automatically check tags for inconsistencies or mistakes"
	runtime = "python3.6"
	timeout = 60
    role = "${var.lambda_role}"
    handler = "tagKeyValidator.lambda_handler"
    environment {
        variables {
            account = "${var.account}",
            bucket_region = "${var.bucketregion}"
            }
}
}



resource "aws_cloudwatch_event_target" "tagkeywatcher" {
    provider = "aws.theregion"
	rule = "${aws_cloudwatch_event_rule.tagkeywatcher.name}"
    arn = "${aws_lambda_function.TagKeyValidator.arn}"
}


resource "aws_lambda_permission" "allow_cloudwatch_to_call_TagKeyValidator" {
    provider = "aws.theregion"
	statement_id = "AllowExecutionFromCloudWatch"
    action = "lambda:InvokeFunction"
    function_name = "${aws_lambda_function.TagKeyValidator.function_name}"
    principal = "events.amazonaws.com"
    source_arn = "${aws_cloudwatch_event_rule.tagkeywatcher.arn}"
}
