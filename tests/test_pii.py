from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    cccd = "001092001234"
    out = scrub_text(f"CCCD của tôi là {cccd}")
    assert cccd not in out
    assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    cards = ("4532111122223333", "4532-1111-2222-3333", "4532 1111 2222 3333")
    for card in cards:
        out = scrub_text(f"Thẻ: {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_passport() -> None:
    passport = "B1234567"
    out = scrub_text(f"Hộ chiếu: {passport}")
    assert passport not in out
    assert "REDACTED_PASSPORT" in out


def test_scrub_vietnamese_address() -> None:
    address = "12 Ngõ 5 Phố Huế, Hà Nội"
    out = scrub_text(f"Tôi sống tại {address}")
    assert "12 Ngõ" not in out
    assert "REDACTED_ADDRESS_VN" in out


def test_scrub_combined_message() -> None:
    raw = "giao hàng cho johndoe@example.com, SĐT 0901234567, CCCD 001092001234"
    out = scrub_text(raw)
    assert "johndoe@example.com" not in out
    assert "0901234567" not in out
    assert "001092001234" not in out
