import json
import boto3

dynamo_resource = boto3.resource('dynamodb')

dynamo_visitors_table = dynamo_resource.Table("visitors")
dynamo_passcodes_table = dynamo_resource.Table("passcodes")


def lambda_handler(event, context):
    # TODO implement
    print(event)
    
    visitors_provided_otp = event['message']['otp']     # this will come from the API 
    
    passcodes_response = dynamo_passcodes_table.scan()
    otps = []
    
    otp_faceid_dict = {}
    
    for i in range(len(passcodes_response['Items'])):
        # otps.append(passcodes_response['Items'][i]['otp'])
        otp_faceid_dict[passcodes_response['Items'][i]['otp']] = passcodes_response['Items'][i]['faceId']
    
    
    if visitors_provided_otp in otp_faceid_dict.keys():
        print("Give access to visitor")       # here we give access to user by returning true
        key = {'faceId' : otp_faceid_dict[visitors_provided_otp]}   # here the actual faceId has to be added
        visitors_response = dynamo_visitors_table.get_item(Key=key)
        visitors_name = visitors_response['Item']['name']
        visitors_phone = visitors_response['Item']['phone']
        
        return visitors_name
    else:
        
        return "false"
        # print("Invalid OTP")            # here we deny access to user by returning false
    
    
    print(otp_faceid_dict)
    
    

    # return {
    #     'statusCode': 200,
    #     'body': json.dumps(event)
    # }
