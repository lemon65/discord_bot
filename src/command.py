def head_or(xs, default=None):
    return next(iter(xs), default)

def parse(input, prefix="!"):
    if not input.startswith(prefix):
        return None, None
    cmd, *arg = input.strip(prefix).split(' ', 1)
    return cmd.lower(), head_or(arg, "")
