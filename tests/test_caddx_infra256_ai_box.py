import math

from caddx_infra256 import CaddxInfra256AIBox


def test_parse_json_packet():
    line = '{"dx":12.4,"dy":-5.1,"squal":82,"height":0.73}'
    packet = CaddxInfra256AIBox._parse_packet_line(line, packet_format='json')
    assert packet is not None
    assert math.isclose(packet['dx'], 12.4)
    assert math.isclose(packet['dy'], -5.1)
    assert packet['squal'] == 82
    assert math.isclose(packet['height'], 0.73)


def test_parse_key_value_packet():
    line = "DX:15,DY:-3,SQUAL:95,HEIGHT:0.6"
    packet = CaddxInfra256AIBox._parse_packet_line(line, packet_format='kv')
    assert packet == {'dx': 15.0, 'dy': -3.0, 'squal': 95, 'height': 0.6}


def test_parse_csv_packet():
    line = "20,-10,77,0.55"
    packet = CaddxInfra256AIBox._parse_packet_line(line, packet_format='csv')
    assert packet == {'dx': 20.0, 'dy': -10.0, 'squal': 77, 'height': 0.55}


def test_parse_invalid_packet_returns_none():
    assert CaddxInfra256AIBox._parse_packet_line("no data", packet_format='kv') is None
