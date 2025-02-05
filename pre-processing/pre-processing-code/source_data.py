import os
import boto3
import time
import ssl
from multiprocessing.dummy import Pool
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from s3_md5_compare import md5_compare


def data_to_s3(endpoint):
    source_dataset_url = 'https://www.cryptodatadownload.com/cdd/Bitstamp_'
    if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
    getattr(ssl, '_create_unverified_context', None)):
        ssl._create_default_https_context = ssl._create_unverified_context
    response = None
    retries = 5
    for attempt in range(retries):
        try:
            response = urlopen(source_dataset_url + endpoint)
        except HTTPError as e:
            if attempt == retries:
                raise Exception('HTTPError: ', e.code)
            time.sleep(0.2 * attempt)
        except URLError as e:
            if attempt == retries:
                raise Exception('URLError: ', e.reason)
            time.sleep(0.2 * attempt)
        else:
            break

    if response == None:
        raise Exception('There was an issue downloading the dataset')

    data_set_name = os.environ['DATA_SET_NAME']
    filename = data_set_name + endpoint
    file_location = '/tmp/' + filename

    with open(file_location, 'wb') as f:
        f.write(response.read())

    s3_bucket = os.environ['S3_BUCKET']
    new_s3_key = data_set_name + '/dataset/' + filename
    s3 = boto3.client('s3')

    has_changes = md5_compare(s3, s3_bucket, new_s3_key, file_location)
    if has_changes:
        s3.upload_file(file_location, s3_bucket, new_s3_key)
        print('Uploaded: ' + filename)
    else:
        print('No changes in: ' + filename)

    asset_source = {'Bucket': s3_bucket, 'Key': new_s3_key}
    return {'has_changes': has_changes, 'asset_source': asset_source}


def source_dataset():
    data_endpoints = [
        'BTCUSD_d.csv',
        'ETHUSD_d.csv',
        'LTCUSD_d.csv',
        'XRPUSD_d.csv',
        'BTCEUR_d.csv',
        'ETHEUR_d.csv',
        'LTCEUR_d.csv',
        'LTCBTC_d.csv',

        'BTCUSD_1h.csv',
        'ETHUSD_1h.csv',
        'LTCUSD_1h.csv',
        'XRPUSD_1h.csv',
        'BTCEUR_1h.csv',
        'ETHEUR_1h.csv',
        'LTCEUR_1h.csv',
        'LTCBTC_1h.csv'

    ]

    with (Pool(2)) as p:
        s3_uploads = p.map(data_to_s3, data_endpoints)

    count_updated_data = sum(
        upload['has_changes'] == True for upload in s3_uploads)

    if count_updated_data > 0:
        asset_list = list(
            map(lambda upload: upload['asset_source'], s3_uploads))
        if len(asset_list) == 0:
            raise Exception('Something went wrong when uploading files to s3')
        return asset_list

    else:
        return []