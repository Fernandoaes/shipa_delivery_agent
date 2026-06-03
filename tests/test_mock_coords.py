from app.twin.mock import MockTwinClient


def test_mock_orders_all_have_coordinates():
    for rec in MockTwinClient().fetch_all():
        assert rec.merchant_lat is not None and rec.merchant_lng is not None
        assert rec.delivery_lat is not None and rec.delivery_lng is not None
