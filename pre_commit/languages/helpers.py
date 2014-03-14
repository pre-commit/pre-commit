
def run_hook(env, hook, file_args):
    return env.run(
        ' '.join([hook['entry']] + hook.get('args', []) + list(file_args)),
        retcode=None,
    )