"""Bounded PDF-to-text child process. No network calls or saved originals."""
import io, json, sys
try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (384*1024*1024,384*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU, (5,5))
except ImportError:
    pass  # Windows: the parent still enforces an 8-second wall-clock timeout.
from pypdf import PdfReader
try:
    raw=sys.stdin.buffer.read(2_000_001)
    if len(raw)>2_000_000:raise ValueError('size')
    reader=PdfReader(io.BytesIO(raw), strict=False)
    if reader.is_encrypted:raise ValueError('encrypted')
    if len(reader.pages)>20:raise ValueError('pages')
    text='\n'.join((page.extract_text() or '')[:10000] for page in reader.pages)[:40000]
    print(json.dumps({'text':text}))
except Exception:
    print(json.dumps({'error':'Could not read PDF. Use an unencrypted text-based PDF, up to 20 pages, or paste the text.'}))
