"""Run Python regressions and real firmware storage/web logic using host adapters.

Requires gcc, OpenSSL development headers and libcjson (Linux). Does not validate
ESP-IDF drivers, mbedTLS acceleration, the radio, display, RMT or USB hardware.
"""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import sys
import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--python-only', action='store_true', help='Run portable desktop checks without Linux native dependencies')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root/'tests'))
for name in ('test_protocol', 'test_vault_client', 'test_protocol_extended', 'test_client_integrity'):
    spec = importlib.util.spec_from_file_location(name, root/'tests'/f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tests = [fn for key, fn in vars(module).items() if key.startswith('test_') and callable(fn)]
    for fn in tests:
        fn()
    print(f'{name}: {len(tests)} checks passed', flush=True)
if args.python_only:
    print('All Python checks passed. Native firmware checks were not requested.')
    sys.exit(0)
with tempfile.TemporaryDirectory() as temp:
    target = Path(temp)/'host-test'
    host = root/'tests'/'host'
    main = root/'firmware'/'main'
    subprocess.run(['gcc', '-std=gnu11', '-g', '-fsanitize=address,undefined',
        '-Werror=implicit-function-declaration', '-I'+str(host/'include'), '-I'+str(main),
        '-DVAULT_MOUNT_POINT="'+temp+'"', str(host/'test_web_storage.c'),
        str(host/'support.c'), str(main/'vault_storage.c'), str(main/'vault_config.c'),
        str(main/'vault_runtime.c'), '-lcrypto', '-l:libcjson.so.1', '-o', str(target)], check=True)
    subprocess.run([str(target)], check=True)
print('All host checks passed.')
