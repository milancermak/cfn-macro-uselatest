import json
import os
from string import Template

from botocore.stub import Stubber
import jmespath
import pytest

from uselatest import main


@pytest.fixture(scope='function')
def lambda_client():
    lambda_stubbed = Stubber(main.lambda_client)
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, 'list_layers.json')) as f:
        list_layers_response = json.load(f)
    lambda_stubbed.add_response('list_layers',
                                list_layers_response,
                                expected_params=None)
    lambda_stubbed.activate()
    yield lambda_stubbed
    lambda_stubbed.deactivate()
    main.get_available_layers.cache_clear()


def load_template_fixture_with_layer(layer_name):
    here = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(here, 'template_fixture.json')) as f:
        raw = Template(f.read())
        formatted = raw.substitute(layer_name=layer_name)
        return json.loads(formatted)


@pytest.mark.parametrize('layer_name', [
    # double-quoting because of the string interpolation when building a
    # valid JSON from the template_fixture.json
    '"superlayer"',
    '"arn:aws:lambda:us-east-1:123456789012:layer:superlayer"',
    '"arn:aws:lambda:us-east-1:123456789012:layer:superlayer:5"'
])
def test_transform(layer_name, lambda_client):
    invocation_event = load_template_fixture_with_layer(layer_name)
    request_id = invocation_event['requestId']

    fqarn = 'arn:aws:lambda:us-east-1:123456789012:layer:superlayer:4'
    if layer_name.endswith('5"'):
        fqarn = layer_name.replace('"', '')

    result = main.handler(invocation_event, None)

    lambda_client.assert_no_pending_responses()
    assert result['status'] == 'success'
    assert result['requestId'] == request_id

    keypaths = ['fragment.Globals.Function.Layers[0]',
                'fragment.Resources.LambdaFunction.Properties.Layers[0]',
                'fragment.Resources.ServerlessFunction.Properties.Layers[0]']
    for keypath in keypaths:
        assert jmespath.search(keypath, result) == fqarn

@pytest.mark.parametrize('layer_name', [
    '{\"Ref\": \"Parameter\"}',
    '{\"Fn::Sub\": \"arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:layer:superlayer:1\"}'
])
def test_no_transform_when_intrinsic_function(layer_name, lambda_client):
    invocation_event = load_template_fixture_with_layer(layer_name)
    request_id = invocation_event['requestId']
    expected = json.loads(layer_name)

    result = main.handler(invocation_event, None)

    lambda_client.assert_no_pending_responses()
    assert result['status'] == 'success'
    assert result['requestId'] == request_id

    keypaths = ['fragment.Globals.Function.Layers[0]',
                'fragment.Resources.LambdaFunction.Properties.Layers[0]',
                'fragment.Resources.ServerlessFunction.Properties.Layers[0]']
    for keypath in keypaths:
        assert jmespath.search(keypath, result) == expected
