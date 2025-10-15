import sys, types, os
# Provide a dummy requests module so sub.py doesn't try to send webhooks during import
class DummyResp:
    def __init__(self):
        self.status_code = 204
        self.text = ''
def dummy_post(*a, **k):
    return DummyResp()

sys.modules['requests'] = types.SimpleNamespace(post=dummy_post)

# Now import sub safely
sys.path.insert(0, os.getcwd())
import importlib.util
spec = importlib.util.spec_from_file_location('sub', os.path.join(os.getcwd(), 'sub.py'))
sub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sub)

# Generate HTML export and write to file
html = sub._generate_html_export(sub.df)
out_path = os.path.join(os.getcwd(), 'out_debug_export.html')
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('Wrote', out_path)
