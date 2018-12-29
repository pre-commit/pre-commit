from pre_commit.meta_hooks import identity


def test_identity(cap_out):
    assert not identity.main(('a', 'b', 'c'))
    assert cap_out.get() == 'a\nb\nc\n'
