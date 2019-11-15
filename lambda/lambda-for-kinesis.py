import boto3
import logging
import base64
import json
import cv2
import os
import random as r
import time
from decimal import Decimal 

s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

smsClient = boto3.client('sns')

dynamo_resource = boto3.resource('dynamodb')

dynamo_visitors_table = dynamo_resource.Table("visitors")
dynamo_passcodes_table = dynamo_resource.Table("passcodes")


def lambda_handler(event, context):
    # TODO implement
    logging.info("API CALLED. EVENT IS:{}".format(event))
    
    print("Data streaming")
    data = event['Records'][0]['kinesis']['data']
    print(base64.b64decode(data))
    json_data = json.loads(base64.b64decode(data).decode('utf-8'))
    stream_name="smart-door-stream"
    print('JSON DATA',json_data)
    
    
    smsClient = boto3.client('sns')
    mobile = "6466230205"
    
    # msg="hi"
    
    #  smsClient.publish(
    #         PhoneNumber = mobile,
    #         Message=msg
                # )
    # response = s3_client.get_object(
        
    #         Bucket='ultimate-bucket',
    #         Key='temp.png'
        
    #     )
        
    # s3.meta.client.download_file('ultimate-bucket', 'temp.png', '/tmp/temp.png')    
    
    # print("hrere is my response")
    # print(response)
    # print(os.path.isfile('/tmp/temp.png'))
    faceId='123'
    face_search_response = json_data['FaceSearchResponse']
    if face_search_response is None:
        return ("No one at the door")
    else:
        matched_face = json_data['FaceSearchResponse'][0]['MatchedFaces']
        print("Matched: ", matched_face)
    
    if face_search_response is not None and ( matched_face is None or len(matched_face)==0):
        fragmentNumber= json_data['InputInformation']['KinesisVideo']['FragmentNumber']
        fileName,faceId=store_image(stream_name,fragmentNumber, None)
        print("Face Id: ",faceId)
    else:
        image_id = json_data['FaceSearchResponse'][0]['MatchedFaces'][0]['Face']['ImageId']
        print('IMAGEID',image_id)
        faceId = json_data['FaceSearchResponse'][0]['MatchedFaces'][0]['Face']['FaceId']
        print('FACEID',faceId)
        fragmentNumber=image_id

    key = {'faceId' : faceId}   # here the actual faceId has to be added
    visitors_response = dynamo_visitors_table.get_item(Key=key)
    
    keys_list = list(visitors_response.keys())
    
    otp=""
    for i in range(4):
        otp+=str(r.randint(1,9))
    
    if('Item' in keys_list):
        
        phone_number_visitor = visitors_response['Item']['phone']
        face_id_visitor = visitors_response['Item']['faceId']
        sendOtpToVisitor(phone_number_visitor, otp)
        
        visitors_name = visitors_response['Item']['name']
        visitors_photo = visitors_response['Item']['photo']
        photo={'objectKey':'updatedKey' , 'bucket' : 'myBucket', 'createdTimestamp' : str(time.ctime(time.time()))}
        visitors_photo.append(photo)
        
        my_visitor_entry = {'faceId' : face_id_visitor , 'name' : visitors_name , 'phone' : phone_number_visitor , 'photo' : visitors_photo}
        dynamo_visitors_table.put_item(Item=my_visitor_entry)
        
        my_string = {'faceId' : face_id_visitor, 'otp': otp, 'expiration' : str(int(time.time() + 300))}
        dynamo_passcodes_table.put_item(Item=my_string)
        time.sleep(60)
    else:
        phone_number_owner = '2016914391' #'6466230205'
        link_visitor_image = 'https://smart-door-trr.s3.amazonaws.com/' + fileName
        
        link_visitor_details_form = 'https://visitor-information.s3.amazonaws.com/WebPage_Visitor_Info_backup.html?fileName='+str(fileName)+'&faceId='+str(faceId)
        print("To Owner: ",link_visitor_details_form)
        sendMessageToOwner(phone_number_owner, link_visitor_image, link_visitor_details_form)
        time.sleep(60)
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

def sendOtpToVisitor(phone_number, otp):
    message_visitor = "Hello, here is your one time password, "
    message_visitor += str(otp)
    smsClient.publish(PhoneNumber="+1"+phone_number,Message=message_visitor)
    
def sendMessageToOwner(phone_number, link_visitor_image, link_visitor_details_form):
    message_owner = "Hello, here is the link for your visitor image, "
    message_owner += str(link_visitor_image)
    message_owner += ", and here is to link to give access to visitor " + str(link_visitor_details_form)
    smsClient.publish(PhoneNumber="+1"+phone_number,Message=message_owner)

# def store_image():
#     kvs_client = boto3.client('kinesisvideo')
#     kvs_data_pt = kvs_client.get_data_endpoint(
#         StreamARN='', # kinesis stream arn
#         APIName='GET_MEDIA'
#     )
#     print(kvs_data_pt)
#     end_pt = kvs_data_pt['DataEndpoint']
#     kvs_video_client = boto3.client('kinesis-video-media', endpoint_url=end_pt, region_name='us-east-1') # provide your region
#     kvs_stream = kvs_video_client.get_media(
#         StreamARN='', # kinesis stream arn
#         StartSelector={'StartSelectorType': 'NOW'} # to keep getting latest available chunk on the stream
#     )
#     print(kvs_stream)

#     with open('/tmp/stream.mkv', 'wb') as f:
#         streamBody = kvs_stream['Payload'].read(1024*16384) # reads min(16MB of payload, payload size) - can tweak this
#         f.write(streamBody)
#         # use openCV to get a frame
#         cap = cv2.VideoCapture('/tmp/stream.mkv')

#         # use some logic to ensure the frame being read has the person, something like bounding box or median'th frame of the video etc
#         ret, frame = cap.read() 
#         cv2.imwrite('/tmp/frame.jpg', frame)
#         s3_client = boto3.client('s3')
#         s3_client.upload_file(
#             '/tmp/frame.jpg',
#             '', # replace with your bucket name
#             'frame.jpg'
#         )
#         cap.release()
#         print('Image uploaded')
def store_image(stream_name, fragmentNumber,faceId):
    # kvs_client = boto3.client('kinesis-video-archived-media')
    s3_client = boto3.client('s3')
    rekClient=boto3.client('rekognition')
    
    # kvs = boto3.client("kinesisvideo")
    # # Grab the endpoint from GetDataEndpoint
    # endpoint = kvs.get_data_endpoint(
    #     APIName="GET_MEDIA_FOR_FRAGMENT_LIST",
    #     StreamName=stream_name
    # )['DataEndpoint']
    # print("Kinesis Data endpoint: ",endpoint)
    # kvs_client = boto3.client("kinesis-video-archived-media", endpoint_url=endpoint, region_name='us-east-1')
    
    # kvs_stream = kvs_client.get_media_for_fragment_list(
    # StreamName=stream_name,
    # Fragments=[
    #     fragmentNumber,
    # ])
    
    
    
    kvs_client = boto3.client('kinesisvideo')
    kvs_data_pt = kvs_client.get_data_endpoint(
        StreamARN='arn:aws:kinesisvideo:us-east-1:463589813520:stream/smart-door-stream/1572993757435',
        APIName='GET_MEDIA'
    )
    print(kvs_data_pt)
    end_pt = kvs_data_pt['DataEndpoint']
    kvs_video_client = boto3.client('kinesis-video-media', endpoint_url=end_pt, region_name='us-east-1') # provide your region
    kvs_stream = kvs_video_client.get_media(
        StreamARN='arn:aws:kinesisvideo:us-east-1:463589813520:stream/smart-door-stream/1572993757435', # kinesis stream arn
        StartSelector={'StartSelectorType': 'NOW'}
    )
    print(kvs_stream)
    
    collectionId="smart-door"
    print("KVS Stream: ",kvs_stream)
    
    with open('/tmp/stream.mkv', 'wb') as f:
        print("Processing stream...")
        streamBody = kvs_stream['Payload'].read(1024*16384) # reads min(16MB of payload, payload size) - can tweak this
        f.write(streamBody)
        
        s3_client.upload_file(
            '/tmp/stream.mkv',
            'smart-door-trr', # replace with your bucket name
            'stream.mkv'
        )
        # use openCV to get a frame
        cap = cv2.VideoCapture('/tmp/stream.mkv')
        
        # total=int(count_frames_manual(cap)/2)
        # cap.set(2,total)
        ret, frame = cap.read() 
        # print("Image: ",frame)
        print("Ret ", ret)
        cv2.imwrite('/tmp/frame.jpg', frame)
        
        if(faceId is None):
            faceId=index_image(frame, collectionId,fragmentNumber)
        print(faceId,fragmentNumber)
        fileName= faceId+'-'+fragmentNumber+'.jpg'
        s3_client.upload_file(
            '/tmp/frame.jpg',
            'smart-door-trr', # replace with your bucket name
            fileName
        )
        cap.release()
        print('Image uploaded')
        return fileName, faceId

def index_image(frame, collectionId, fragmentNumber):
    rekClient=boto3.client('rekognition')
    retval, buffer = cv2.imencode('.jpg', frame)
    response=rekClient.index_faces(CollectionId=collectionId,
    Image={
    'Bytes': buffer.tobytes(),
    },
    ExternalImageId=fragmentNumber,
    DetectionAttributes=['ALL'])
    
    print('New Response',response)
    faceId=''
    for faceRecord in response['FaceRecords']:
        faceId = faceRecord['Face']['FaceId']
    return faceId

def count_frames_manual(video):
	total = 0
	while True:
		(grabbed, frame) = video.read()
		if not grabbed:
			break
		total += 1
	return total