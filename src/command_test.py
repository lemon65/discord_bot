import command

def test_simple_command_parse():
    cmd, arg = command.parse("!randomquote")
    assert cmd == "randomquote"
    assert arg == ""

def test_command_with_args():
    cmd, arg = command.parse("!feed add https://example.com/feed.xml")
    assert cmd == "feed"
    assert arg == "add https://example.com/feed.xml"

def test_command_lower_case():
    cmd, arg = command.parse("!BlackJack")
    assert cmd == "blackjack"
    assert arg == ""

def test_no_prefix():
    cmd, arg = command.parse("add https://example.com/feed.xml", prefix="")
    assert cmd == "add"
    assert arg == "https://example.com/feed.xml"

