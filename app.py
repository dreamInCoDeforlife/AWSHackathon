import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4
from flask_cors import CORS
import requests
from flask import Flask, jsonify, request
import boto3
import ast
import decimal
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from sentiment_analyzer import compare_price
app = Flask(__name__)
CORS(app)
s3 = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('products')
sage_client = boto3.client('sagemaker-runtime', region_name='us-east-1')


@app.route('/')
def index():
    return '''<form method=POST enctype=multipart/form-data action="upload">
		<input type=file name=myfile>
		<input type=submit>
		</form>
	'''


@app.route('/create_new_product', methods=["POST"])
def create_new_product():
    new_uuid = str(uuid4())
    # s3.Bucket('thirdparty-image-bucket').put_object(new_uuid+"/")
    table.put_item(Item={
        'product_description': "Add Product Description",
        'username': 'admin',
        'product_id': new_uuid,
        'product_name': "Add Product Name",
        'product_price': 0,
        'is_used_product': True,
        'barcode': -00000000,
        'stat': "In progress",
        'images': []
    })

    return jsonify({"product_id": new_uuid}), new_uuid


@app.route('/update/<id_>', methods=['POST'])
def update_product(id_):
    product_id = id_
    val = request.get_data()
    dict_str = val.decode("UTF-8")
    values = json.loads(dict_str)
    # values = ast.literal_eval(dict_str)
    required = ['product_name', 'product_price', 'is_used_product',
                'barcode', 'product_description', 'stat']
    if not all(k in values for k in required):
        return 'Missing values', 400

    try:
        retrieve = table.update_item(
            Key={'username': 'admin', 'product_id': product_id},
            UpdateExpression="set product_name = :r, product_price=:p, is_used_product=:a, barcode=:l, product_description=:t, stat=:stat",
            ExpressionAttributeValues={
                ':r': values['product_name'],
                ':p': decimal.Decimal(str(values['product_price'])),
                ':a': values["is_used_product"],
                ':l': values["barcode"],
                ":t": values["product_description"],
                ":stat": values["stat"]
            },
            ReturnValues="UPDATED_NEW"
        )
        return "Done", 200
    except ClientError as e:
        print(e.response['Error']['Message'])
        return "Server error", 500


def removeEmptyString(dic):
    if isinstance(dic, str):
        if dic == "":
            return None
        else:
            return dic

    for e in dic:
        if isinstance(dic[e], dict):
            dic[e] = removeEmptyString(dic[e])
        if (isinstance(dic[e], str) and dic[e] == ""):
            dic[e] = None
        if isinstance(dic[e], list):
            for entry in dic[e]:
                removeEmptyString(entry)
    return dic


def update_from_barcode(dict_values, id_):
    dict_values = removeEmptyString(dict_values)
    product_id = id_
    update_expression = 'SET {}'.format(
        ','.join(f'#{k}=:{k}' for k in dict_values))
    expression_attribute_values = {f':{k}': v for k, v in dict_values.items()}
    expression_attribute_names = {f'#{k}': k for k in dict_values}

    response = table.update_item(
        Key={'username': 'admin', 'product_id': product_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
        ExpressionAttributeNames=expression_attribute_names,
        ReturnValues='UPDATED_NEW',
    )

# todo
@app.route('/delete/<id_>', methods=["POST"])
def delete_item(id_):
    image_list = request.get_data()
    dict_str = image_list.decode("UTF-8")
    values = ast.literal_eval(dict_str)
    required = ['image_list']
    if not all(k in values for k in required):
        return 'Missing values', 400

    for url in values["image_list"]:
        key = url.split("https://thirdparty-image-bucket.s3.amazonaws.com/")[1]
        # s3.Bucket('thirdparty-image-bucket').delete_key(key)
        s3.Object('thirdparty-image-bucket', key).delete()

    return "Done", 200


@app.route("/scan_barcode", methods=["POST"])
def scan_barcode():
    val = []
    send_, id_ = create_new_product()
    # id_ = uuid4()
    for filename, file in request.files.items():

        # print(file.filename)
        response = sage_client.invoke_endpoint(
            EndpointName='barcode-reader-rat',
            Body=file,
            ContentType='image/jpeg',
            Accept='application/json'
        )

        # print(response["Body"].read().decode("utf-8"))
        val = response["Body"].read().decode("utf-8")
        val = ast.literal_eval(val)

    if len(list(val.keys())) == 1:
        barcode = list(val.keys())[0]
        value = {}
        val = requests.get(
            "https://api.barcodelookup.com/v2/products?barcode=" + barcode + "&formatted=y&key=cmsr5t3jnfq14ncd3ws4hcif6cbrwx")
        dict_str = val.content.decode("UTF-8")
        if dict_str != "\n":
            values = ast.literal_eval(dict_str)

            json_body = values["products"][0]
            value = {}
            if "barcode_number" in json_body:
                value["barcode"] = int(json_body["barcode_number"])

            if "product_name" in json_body:
                value["product_name"] = json_body["product_name"]

            if "description" in json_body:
                value['product_description'] = json_body['description']

            if len(json_body["stores"]) > 1:
                expensive = json_body["stores"][-1]["store_price"]
                cheap = json_body["stores"][0]["store_price"]
                value["expensive_version"] = expensive
                value["cheap_version"] = cheap
            elif len(json_body["stores"]) == 1:
                value["version_in_market"] = json_body["stores"][0][
                    "store_price"]

            value["parse_product"] = json_body

            # print(value)
            update_from_barcode(value, id_)
            # return send_, 200

            price = 0

            if "cheap_version" in value:
                price = value["cheap_version"]
            elif "expensive_version" in value:
                price = value["expensive_version"]
            elif "version_in_market" in value:
                price = value["version_in_market"]

            return jsonify({"product_id": id_, "barcode": value["barcode"], "price": price, "product_name": value["parse_product"]["product_name"]}), 200

        else:
            return "Error Reading Barcode Please try again at another time", 400

    else:
        return "Unacceptable Input", 400


@app.route('/retrieve/<id_>', methods=["POST"])
def retrieve(id_):
    folder_id = id_
    my_bucket = s3.Bucket('thirdparty-image-bucket')
    image_list = []
    dynamodb_items = []
    for object_summary in my_bucket.objects.filter(
            Prefix=folder_id + "/"):
        val = "https://thirdparty-image-bucket.s3.amazonaws.com/" + object_summary.key
        image_list.append(val)

    try:
        response = table.get_item(
            Key={'username': 'admin', 'product_id': folder_id},
        )
        dynamodb_items = response
        # print(dynamodb_items)
    except ClientError as e:
        print(e.response['Error']['Message'])
        return "Error Occured", 400
    return jsonify({'image_list': image_list, "item_info": dynamodb_items}), 200


def retrieve_regular(id_):
    folder_id = id_
    my_bucket = s3.Bucket('thirdparty-image-bucket')
    image_list = []
    dynamodb_items = []
    for object_summary in my_bucket.objects.filter(
            Prefix=folder_id + "/"):
        val = "https://thirdparty-image-bucket.s3.amazonaws.com/" + object_summary.key
        image_list.append(val)

    try:
        response = table.get_item(
            Key={'username': 'admin', 'product_id': folder_id},
        )
        dynamodb_items = response
        # print(dynamodb_items)
    except ClientError as e:
        print(e.response['Error']['Message'])
        return "Error Occured", 400
    return {'image_list': image_list, "item_info": dynamodb_items}


@app.route('/send_for_review/<id_>', methods=['POST'])
def send_for_review(id_):
    json_format = retrieve_regular(id_)["item_info"]["Item"]
    val = ""
    if "version_in_market" in json_format:
        actual_price = json_format["version_in_market"]
        third_party_price = json_format["product_price"]
        val = compare_price(decimal.Decimal(actual_price),
                            third_party_price, json_format)
    elif "expensive_version" in json_format:
        actual_price = json_format["expensive_version"]
        third_party_price = json_format["product_price"]
        val = compare_price(decimal.Decimal(actual_price),
                            decimal.Decimal(third_party_price), json_format)

    return jsonify(val), 200


@app.route('/upload/<id_>', methods=['POST'])
def upload(id_):
    for filename, file in request.files.items():

        filePath = id_ + "/" + file.filename
        fileURL = 'https://thirdparty-image-bucket.s3.amazonaws.com/' + filePath
        contentType = file.content_type

        s3.Bucket('thirdparty-image-bucket').put_object(Key=filePath,
                                                        Body=file,
                                                        ContentType=contentType)

        s3Client = boto3.client("s3", region_name="us-east-1")
        object_acl = s3.ObjectAcl(
            "thirdparty-image-bucket", id_+"/"+file.filename)
        response = object_acl.put(ACL='public-read')

        try:
            retrieve = table.update_item(
                Key={'username': 'admin', 'product_id': id_},
                UpdateExpression="set images = list_append(images, :i)",
                ExpressionAttributeValues={
                    ':i': [fileURL],
                },
                ReturnValues="UPDATED_NEW"
            )
            return "Done", 200
        except ClientError as e:
            print(e.response['Error']['Message'])
            return "Server error", 500

        return jsonify({'url': fileURL}), 200


@app.route('/get_item_list', methods=['POST'])
def return_index():
    try:
        response = table.query(
            KeyConditionExpression=Key('username').eq('admin')
        )
        # print(response)
        response = response["Items"]
        array = []
        for i in response:
            # print(response)
            val = {}
            val["product_id"] = i["product_id"]
            val["status"] = i["stat"]
            val["product_name"] = i['product_name']
            val["images"] = i["images"]
            array.append(val)
        # print(array)
        # print(response)
        return jsonify({"list_items": array}), 200
    except ClientError as e:
        print(e.response['Error']['Message'])
        return "Error Occured", 400


if __name__ == '__main__':

    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int,
                        help='port to listen on')
    args = parser.parse_args()
    port = args.port
    app.run(host='0.0.0.0', port=port)
