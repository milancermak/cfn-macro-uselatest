from functools import lru_cache

import boto3
import jmespath


lambda_client = boto3.client('lambda')


@lru_cache(maxsize=1)
def get_available_layers():
    return lambda_client.list_layers()['Layers']


def build_layer_arn_from_name(layer_name, available_layers):
    for layer in available_layers:
        if layer_name == layer['LayerName']:
            return layer['LatestMatchingVersion']['LayerVersionArn']

    print(f'No available layer matching the name {layer_name}')
    return layer_name


def ensure_latest_layers(layers, region, account_id):
    available_layers = get_available_layers()
    if available_layers == []:
        print(f'No Lambda Layers available under account {account_id} in region {region}')
        return layers

    latest_layers = []
    for layer in layers:
        if isinstance(layer, dict):
            # happens with intrinsic functions, e.g. !Ref, !Sub
            latest_layers.append(layer)
            continue

        arn_parts = layer.split(':')
        if len(arn_parts) == 8:
            # fully qualified layer version
            latest_layers.append(layer)
        else:
            # layer specified either only by its name
            # or by the full layer arn, without version
            layer_name = arn_parts[-1]
            layer_arn = build_layer_arn_from_name(layer_name,
                                                  available_layers)
            latest_layers.append(layer_arn)

    return latest_layers


def handler(event, context):
    print(event)

    region = event['region']
    account_id = event['accountId']

    global_layers = jmespath.search('fragment.Globals.Function.Layers', event)
    if global_layers:
        latest_global_layers = ensure_latest_layers(global_layers,
                                                    region,
                                                    account_id)
        event['fragment']['Globals']['Function']['Layers'] = latest_global_layers

    resources = jmespath.search('fragment.Resources', event)
    transformable_types = ['AWS::Serverless::Function',
                           'AWS::Lambda::Function']

    for resource in resources.values():
        if resource.get('Type') in transformable_types:
            layers = resource['Properties'].get('Layers')
            if layers:
                latest_layers = ensure_latest_layers(layers, region, account_id)
                resource['Properties']['Layers'] = latest_layers

    result = {
        'fragment': event['fragment'],
        'requestId': event['requestId'],
        'status': 'success'
    }
    print(result)

    return result
