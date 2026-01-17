import public_transit.message as m


def test_constants_exist():
    assert hasattr(m, "QUIET")
    assert hasattr(m, "NORMAL")
    assert hasattr(m, "VERBOSE")


def test_message_write_outputs(capsys):
    msg = m.Message(m.NORMAL)
    msg.write("hello")
    out = capsys.readouterr().out
    assert out.strip() == "hello"


def test_message_write_respects_verbosity(capsys):
    msg = m.Message(m.QUIET)
    msg.write("hidden", m.VERBOSE)
    out = capsys.readouterr().out
    assert out == ""
